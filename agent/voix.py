"""Voix off des Shorts : Google Cloud Text-to-Speech, voix Chirp 3 HD « Schedar » (choisie par Stéphane, oct. 2026).

- Accès : le compte de service Google déjà utilisé pour le Drive (secret GOOGLE_SERVICE_ACCOUNT_JSON), dans son projet
  Google Cloud, où l'API Text-to-Speech doit être activée.
- Gratuit jusqu'à 1 million de caractères par mois pour les voix Chirp 3 HD. Le compteur etat/voix.json (recommité par
  le workflow) arrête la voix au plafond de config.yaml : au-delà, le Short sort sans voix, comme avant.
- lexique.csv (mot;prononciation) corrige la prononciation des noms propres.
"""
from __future__ import annotations

import base64
import json
import os
import re
import wave
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

import requests

RACINE = Path(__file__).resolve().parent.parent
COMPTEUR = RACINE / "etat" / "voix.json"
LEXIQUE = RACINE / "lexique.csv"
DEFAUTS = {"active": False, "nom": "fr-FR-Chirp3-HD-Schedar", "vitesse": 1.0, "plafond_mensuel": 900000}


class VoixIndisponible(RuntimeError):
    pass


def _reglages() -> dict:
    from .config import charger_config
    return {**DEFAUTS, **(charger_config(RACINE / "config.yaml").get("voix") or {})}


def _identifiants() -> dict:
    brut = os.environ.get("GOOGLE_SERVICE_ACCOUNT_JSON", "")
    if not brut:
        from .sources import SourceDrive
        fichier = os.environ.get("GOOGLE_SERVICE_ACCOUNT_FILE", "") or SourceDrive._trouver_cle()
        if fichier and os.path.exists(fichier):
            brut = Path(fichier).read_text(encoding="utf-8")
    if not brut:
        raise VoixIndisponible("clé du compte de service Google introuvable")
    return json.loads(brut)


def _lexique() -> list[tuple[str, str]]:
    if not LEXIQUE.exists():
        return []
    paires = []
    for ligne in LEXIQUE.read_text(encoding="utf-8-sig").splitlines()[1:]:
        mot, _, prononciation = ligne.partition(";")
        if mot.strip() and prononciation.strip():
            paires.append((mot.strip(), prononciation.strip()))
    return sorted(paires, key=lambda p: -len(p[0]))  # les expressions longues d'abord


def preparer(texte: str, lexique: list[tuple[str, str]] | None = None) -> str:
    """Texte prononcé : sans liens, hashtags, émojis ni points de suspension de coupe, lexique appliqué."""
    t = re.sub(r"https?://\S+|#\w+", "", texte)
    t = re.sub(r"[\U0001F300-\U0001FAFF☀-➿]", "", t)
    t = t.replace("…", ".").replace("—", ",").replace("–", ",").replace("«", "").replace("»", "")
    for mot, prononciation in (lexique if lexique is not None else _lexique()):
        t = t.replace(mot, prononciation)
    return re.sub(r"\s+", " ", t).strip()


def duree_wav(chemin: Path) -> float:
    with wave.open(str(chemin), "rb") as w:
        return w.getnframes() / float(w.getframerate())


class Voix:
    def __init__(self, journal=print):
        self.cfg = _reglages()
        self.journal = journal
        self._jeton = None
        self._ids = None

    # ---- compteur mensuel (anti-dépense)
    def _mois(self) -> str:
        return datetime.now(ZoneInfo("Europe/Paris")).strftime("%Y-%m")

    def _compteur(self) -> dict:
        try:
            return json.loads(COMPTEUR.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            return {}

    def consommes(self) -> int:
        return int(self._compteur().get(self._mois(), 0))

    def _ajouter(self, n: int) -> None:
        c = self._compteur()
        c[self._mois()] = int(c.get(self._mois(), 0)) + n
        COMPTEUR.parent.mkdir(parents=True, exist_ok=True)
        COMPTEUR.write_text(json.dumps(c, indent=2, sort_keys=True), encoding="utf-8")

    def reste(self) -> int:
        return int(self.cfg["plafond_mensuel"]) - self.consommes()

    # ---- appel Google
    def _entetes(self) -> dict:
        if self._jeton is None or not self._jeton.valid:
            from google.auth.transport.requests import Request
            from google.oauth2 import service_account
            self._ids = self._ids or _identifiants()
            self._jeton = service_account.Credentials.from_service_account_info(
                self._ids, scopes=["https://www.googleapis.com/auth/cloud-platform"])
            self._jeton.refresh(Request())
        return {"Authorization": f"Bearer {self._jeton.token}", "x-goog-user-project": self._ids["project_id"]}

    def dire(self, texte: str, sortie: Path) -> float:
        """Écrit le WAV de `texte` et renvoie sa durée en secondes."""
        r = requests.post("https://texttospeech.googleapis.com/v1/text:synthesize", headers=self._entetes(), timeout=120,
                          json={"input": {"text": texte},
                                "voice": {"languageCode": "fr-FR", "name": self.cfg["nom"]},
                                "audioConfig": {"audioEncoding": "LINEAR16", "sampleRateHertz": 24000,
                                                "speakingRate": float(self.cfg["vitesse"])}})
        if r.status_code != 200:
            raise VoixIndisponible(f"Google Text-to-Speech {r.status_code} : {r.text[:300]}")
        self._ajouter(len(texte))  # Google facture au caractère envoyé
        sortie.write_bytes(base64.b64decode(r.json()["audioContent"]))
        return duree_wav(sortie)

    def narration(self, dits: list[dict], dossier: Path, prefixe: str, forcer: bool = False) -> list[dict] | None:
        """Une piste par scène : [{"cle", "src", "duree"}], src relatif à public/. None si la voix est coupée.
        `forcer` : Short d'essai, avec voix même si elle n'est pas encore activée pour la production."""
        if not (self.cfg.get("active") or forcer):
            return None
        lexique = _lexique()
        textes = [(d["cle"], preparer(d["texte"], lexique)) for d in dits if d.get("texte")]
        textes = [(c, t) for c, t in textes if t]
        total = sum(len(t) for _, t in textes)
        if total > self.reste():
            self.journal(f"⚠️ Voix off coupée : plafond mensuel atteint ({self.consommes()} caractères ce mois-ci)")
            return None
        pistes = []
        for cle, t in textes:
            nom = f"{prefixe}-{cle}.wav"
            pistes.append({"cle": cle, "src": f"{dossier.name}/{nom}", "duree": round(self.dire(t, dossier / nom), 3)})
        return pistes
