"""Compte Instagram personnel de Stéphane, par la connexion Instagram directe (« Instagram API with Instagram Login ») :
pas de Page Facebook. Hôte graph.instagram.com, jeton d'utilisateur Instagram longue durée (60 jours).

- INSTAGRAM_PERSO_TOKEN : le jeton généré dans le tableau de bord de l'application Meta (scripts/jeton_instagram_perso.ps1).
- INSTAGRAM_PERSO_CLE : clé de chiffrement (Fernet). Le jeton est renouvelé chaque semaine et le nouveau est rangé
  chiffré dans etat/instagram_perso.jeton (le dépôt est public : il n'y est jamais en clair).
- Les Reels se publient depuis une adresse web publique (video_url) : l'envoi direct du fichier est réservé à la
  connexion Facebook. La vidéo est donc d'abord mise en ligne sur GitHub Pages (hebergement.py).
"""
from __future__ import annotations

import json
import os
from datetime import datetime, timedelta, timezone
from pathlib import Path

import requests

from .base import TIMEOUT, ErreurPublication, Resultat, attendre, controler

RACINE = Path(__file__).resolve().parent.parent.parent
COFFRE = RACINE / "etat" / "instagram_perso.jeton"
RENOUVELER_APRES = timedelta(days=7)


class InstagramPerso:
    nom = "instagram_perso"
    variables = ("INSTAGRAM_PERSO_TOKEN",)

    def __init__(self, cfg: dict, journal=print):
        self.version = cfg.get("meta", {}).get("version_api", "v25.0")
        self.graph = f"https://graph.instagram.com/{self.version}"
        self.journal = journal
        self.jeton, self._obtenu = self._charger()
        self._ig = ""

    @classmethod
    def est_configure(cls) -> bool:
        return bool(os.environ.get("INSTAGRAM_PERSO_TOKEN") or COFFRE.exists())

    # ---- jeton : coffre chiffré, sinon le secret d'origine
    @staticmethod
    def _fernet():
        cle = os.environ.get("INSTAGRAM_PERSO_CLE", "")
        if not cle:
            return None
        from cryptography.fernet import Fernet
        return Fernet(cle.encode())

    def _charger(self) -> tuple[str, datetime | None]:
        f = self._fernet()
        if f and COFFRE.exists():
            try:
                d = json.loads(COFFRE.read_text(encoding="utf-8"))
                jeton = f.decrypt(d["jeton"].encode()).decode()
                # un nouveau jeton collé par Stéphane (après expiration) remplace celui du coffre
                if d.get("empreinte_secret") == _empreinte(os.environ.get("INSTAGRAM_PERSO_TOKEN", "")):
                    return jeton, datetime.fromisoformat(d["obtenu_le"])
            except Exception as e:
                self.journal(f"⚠️ Coffre du jeton Instagram illisible ({type(e).__name__}) : jeton d'origine utilisé")
        return os.environ.get("INSTAGRAM_PERSO_TOKEN", ""), None

    def renouveler(self) -> None:
        """Prolonge le jeton de 60 jours (au plus une fois par semaine) et le range chiffré dans le coffre."""
        f = self._fernet()
        if not f:
            self.journal("⚠️ INSTAGRAM_PERSO_CLE absente : le jeton Instagram n'est pas renouvelé (il expirera au bout de 60 jours)")
            return
        if self._obtenu and datetime.now(timezone.utc) - self._obtenu < RENOUVELER_APRES:
            return
        r = requests.get("https://graph.instagram.com/refresh_access_token", timeout=TIMEOUT,
                         params={"grant_type": "ig_refresh_token", "access_token": self.jeton})
        if r.status_code != 200:  # jeton de moins de 24 h : Instagram refuse, on réessaiera au passage suivant
            self.journal(f"ℹ️ Jeton Instagram non renouvelé cette fois (HTTP {r.status_code})")
            return
        self.jeton = r.json()["access_token"]
        self._obtenu = datetime.now(timezone.utc)
        COFFRE.parent.mkdir(parents=True, exist_ok=True)
        COFFRE.write_text(json.dumps({
            "jeton": f.encrypt(self.jeton.encode()).decode(),
            "obtenu_le": self._obtenu.isoformat(timespec="seconds"),
            "empreinte_secret": _empreinte(os.environ.get("INSTAGRAM_PERSO_TOKEN", "")),
        }, indent=2), encoding="utf-8")
        self.journal("🔑 Jeton Instagram renouvelé pour 60 jours")

    # ---- appels
    def _get(self, chemin: str, **params) -> dict:
        r = requests.get(f"{self.graph}/{chemin}", params={**params, "access_token": self.jeton}, timeout=TIMEOUT)
        return controler(r, f"instagram GET {chemin.split('/')[-1]}").json()

    def _post(self, chemin: str, contexte: str, **donnees) -> dict:
        r = requests.post(f"{self.graph}/{chemin}", data={**donnees, "access_token": self.jeton}, timeout=TIMEOUT)
        return controler(r, contexte).json()

    @property
    def ig(self) -> str:
        if not self._ig:
            self._ig = str(self._get("me", fields="user_id")["user_id"])
        return self._ig

    def verifier(self) -> str:
        return "@" + self._get("me", fields="username")["username"]

    def publier_reel(self, video_url: str, legende: str) -> Resultat:
        cid = self._post(f"{self.ig}/media", "création conteneur Reel", media_type="REELS", video_url=video_url,
                         caption=legende, share_to_feed="true")["id"]

        def pret():
            s = self._get(cid, fields="status_code,status")
            if s.get("status_code") in ("ERROR", "EXPIRED"):
                raise ErreurPublication(f"Instagram a rejeté la vidéo : {s.get('status')}")
            return s.get("status_code") == "FINISHED"
        attendre(pret, delai_max=900, pas=20, contexte="Instagram traitement du Reel")
        media_id = self._post(f"{self.ig}/media_publish", "publication du Reel", creation_id=cid)["id"]
        lien = self._get(media_id, fields="permalink").get("permalink", "")
        return Resultat(lien or f"instagram media {media_id}", media_id)


def _empreinte(jeton: str) -> str:
    import hashlib
    return hashlib.sha256(jeton.encode()).hexdigest()[:16] if jeton else ""
