"""Compte Instagram de Stéphane : Reels « conseils et astuces psychologiques » de 60 secondes et plus, sans visage filmé.

Chaque jour de publication (config perso.jours), au premier passage après perso.heure : le sujet suivant du catalogue
(perso_sujets.py, adapté du skill marketing-psychology) devient un Reel. Gemini (gratuit) écrit le script et la légende à
partir de la fiche du sujet seulement : aucune étude, aucun chercheur, aucun chiffre qui n'y figure pas (contrôlé).
Voix Google (voix.py), rendu Remotion (composition PersoReel), mise en ligne GitHub Pages, publication par la connexion
Instagram directe (publieurs/instagram_perso.py).

Facultatif : un dossier Drive (perso.dossier_drive) avec un sous-dossier « _photos » de portraits de Stéphane ; s'il
existe, deux portraits illustrent chaque Reel. Sans lui, le Reel n'est fait que de texte animé.
"""
from __future__ import annotations

import base64
import json
import os
import random
import re
import shutil
import subprocess
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from zoneinfo import ZoneInfo

from .perso_sujets import CATEGORIES, PAR_ID, prochain

RACINE = Path(__file__).resolve().parent.parent
MOTION = RACINE / "motion"
ETAT = RACINE / "etat" / "perso.json"
JOURS = ["lundi", "mardi", "mercredi", "jeudi", "vendredi", "samedi", "dimanche"]
IMAGES = {".jpg", ".jpeg", ".png", ".webp"}
GFOLDER = "application/vnd.google-apps.folder"
PAROLE_MIN = 1050  # caractères dits ≈ 60 secondes de vidéo avec la voix Schedar (884 caractères = 53 s le 27/10)

SCHEMA = {
    "type": "object",
    "properties": {
        "titre": {"type": "string"},
        "scenes": {"type": "array", "items": {
            "type": "object",
            "properties": {
                "type": {"type": "string", "enum": ["texte", "citation", "liste", "photo"]},
                "photo": {"anyOf": [{"type": "integer"}, {"type": "null"}]},
                "ecran": {"type": "string"},
                "dit": {"type": "string"},
            },
            "required": ["type", "photo", "ecran", "dit"],
            "additionalProperties": False,
        }},
        "question": {"type": "string"},
        "legende": {"type": "string"},
        "hashtags": {"type": "array", "items": {"type": "string"}},
    },
    "required": ["titre", "scenes", "question", "legende", "hashtags"],
    "additionalProperties": False,
}

SYSTEME = """Tu écris le script d'un Reel Instagram de 60 à 90 secondes pour le compte de Stéphane Nzesseu, qui partage \
des conseils et astuces de psychologie pour la vie de tous les jours et le travail. Son public : des francophones \
d'Afrique et d'Europe, entrepreneurs, salariés, étudiants, curieux. Ils n'ont pas de formation en psychologie.

But : qu'en une minute, le spectateur comprenne un mécanisme de son propre esprit, se reconnaisse dans un exemple, et \
reparte avec une astuce qu'il peut appliquer le jour même.

Déroulé (une idée par scène), entre 12 et 16 scènes :
1. Une accroche qui fait se reconnaître le spectateur (une situation vécue, une question qui pique).
2. Le nom du mécanisme et ce qu'il est, en mots simples.
3. Deux exemples concrets de la vie quotidienne ou du travail (marché, famille, bureau, téléphone, boutique…).
4. Pourquoi le cerveau fait ça, en une phrase, sans jargon.
5. L'astuce : comment s'en servir, en 2 ou 3 étapes concrètes.
6. Comment s'en protéger quand les autres s'en servent (quand c'est pertinent).
7. La phrase à retenir.
Puis une question au spectateur (champ « question »).

Exactitude (impératif) :
- Ta seule source est la fiche du sujet. N'invente aucune étude, aucune expérience, aucun chercheur, aucun pourcentage, \
aucune statistique. Les seuls chiffres permis sont ceux de la fiche, et les petits nombres d'un exemple (« 3 options »).
- N'attribue l'idée à personne et ne dis pas « les études montrent », « les scientifiques ont prouvé ».
- Les exemples sont des situations ordinaires et plausibles, sans nom de personne, de marque ou d'entreprise réelle.
- Reste éthique : on explique pour aider, jamais pour manipuler.

Ton : celui de Stéphane, posé, chaleureux, un peu malicieux. Il tutoie le spectateur. Français simple et correct, \
phrases courtes. Pas de ton publicitaire, pas de formule toute faite (« dans un monde où »), pas de tiret long (—).

Format de chaque scène :
- « dit » : ce que dit la voix, entre 80 et 150 caractères (5 à 8 secondes). En tout, au moins 1 150 caractères dits.
- « texte » : une idée clé en grand ; « ecran » = 40 caractères au plus.
- « citation » : la phrase à retenir (une seule par Reel) ; « ecran » = la phrase, 110 caractères au plus, et « dit » = \
la même phrase.
- « liste » : 2 ou 3 étapes ; « ecran » = « Titre : étape 1 | étape 2 | étape 3 », 90 caractères au plus.
- « photo » : un portrait de Stéphane en fond, par son numéro (0 = le premier reçu) ; « ecran » = 34 caractères au \
plus. Seulement si des portraits sont fournis, et au plus 2 scènes. Mets photo à null pour les autres types.

« titre » : le nom du mécanisme, 45 caractères au plus (affiché en haut de la vidéo).
« legende » : la légende Instagram. Première ligne : une accroche de 125 caractères au plus. Puis 2 à 4 courts \
paragraphes séparés par une ligne vide, qui résument l'astuce sans recopier la vidéo. Termine par la question. Pas de \
lien, pas de hashtag dans le texte, 1 ou 2 émojis au plus.
« hashtags » : 3 à 5 hashtags précis en français, sans le #."""


# --------------------------------------------------------------------------- état (public : aucune donnée personnelle)

class EtatPerso:
    def __init__(self, chemin: Path = ETAT):
        self.chemin = chemin
        self.d = json.loads(chemin.read_text(encoding="utf-8")) if chemin.exists() else {}
        self.d.setdefault("publications", [])
        self.d.setdefault("echecs", {})

    def publie_le(self, jour) -> bool:
        return any(p.get("jour") == jour.isoformat() for p in self.d["publications"])

    def sujets_publies(self) -> list[str]:
        return [p["sujet"] for p in self.d["publications"] if p.get("sujet")]

    def sauver(self) -> None:
        self.chemin.parent.mkdir(parents=True, exist_ok=True)
        tmp = self.chemin.with_suffix(".tmp")
        tmp.write_text(json.dumps(self.d, ensure_ascii=False, indent=2, sort_keys=True), encoding="utf-8")
        tmp.replace(self.chemin)


def est_le_moment(cfg: dict, maintenant: datetime, etat: EtatPerso) -> tuple[bool, str]:
    p = cfg.get("perso") or {}
    local = maintenant.astimezone(ZoneInfo(cfg["fuseau_horaire"]))
    if JOURS[local.weekday()] not in [j.lower() for j in p.get("jours", [])]:
        return False, f"pas de Reel le {JOURS[local.weekday()]}"
    h, m = map(int, str(p.get("heure", "12:00")).split(":"))
    if (local.hour, local.minute) < (h, m):
        return False, f"publication du jour prévue après {h:02d}:{m:02d}"
    if etat.publie_le(local.date()):
        return False, "Reel du jour déjà publié"
    return True, ""


# --------------------------------------------------------------------------- portraits (facultatif)

def portraits(cfg: dict, dossier: Path, graine: str, nb: int = 2, journal=print) -> list[Path]:
    ident = (cfg.get("perso") or {}).get("dossier_drive")
    if not ident:
        return []
    try:
        from .sources import Fichier, SourceDrive
        os.environ["DRIVE_FOLDER_ID"] = ident
        src = SourceDrive.depuis_env()
        sous = next((f for f in src._enfants(ident) if f["mimeType"] == GFOLDER and f["name"].lower() == "_photos"), None)
        photos = [f for f in src._enfants(sous["id"]) if Path(f["name"]).suffix.lower() in IMAGES] if sous else []
        choisies = random.Random(graine).sample(photos, min(nb, len(photos)))
        return [_reduite(src.telecharger(Fichier(f["id"], f"portrait{k}{Path(f['name']).suffix.lower()}", ""), dossier))
                for k, f in enumerate(choisies)]
    except Exception as e:  # les portraits ne bloquent jamais le Reel
        journal(f"⚠️ Portraits indisponibles, Reel en texte seul : {type(e).__name__} {str(e)[:150]}")
        return []


def _reduite(chemin: Path, cote: int = 1280) -> Path:
    from PIL import Image, ImageOps
    im = ImageOps.exif_transpose(Image.open(chemin)).convert("RGB")
    im.thumbnail((cote, cote))
    sortie = chemin.with_name(chemin.stem + "_r.jpg")
    im.save(sortie, "JPEG", quality=88)
    return sortie


# --------------------------------------------------------------------------- script

def fiche(sujet: tuple) -> str:
    ident, cat, nom, idee, astuce = sujet
    return f"Catégorie : {CATEGORIES[cat]}\nMécanisme : {nom}\nL'idée : {idee}\nL'astuce : {astuce}"


def _nombres(texte: str) -> set[str]:
    t = re.sub(r"(?<=\d)[   .](?=\d{3}\b)", "", texte)
    return {n.replace(",", ".") for n in re.findall(r"\d+(?:,\d+)?", t)}


def controler(script: dict, source: str, nb_photos: int) -> list[str]:
    """Problèmes qui interdisent d'utiliser le script (vide = bon)."""
    problemes = []
    scenes = script.get("scenes") or []
    if not 11 <= len(scenes) <= 18:
        problemes.append(f"{len(scenes)} scènes (12 à 16 attendues)")
    parole = sum(len(sc.get("dit", "")) for sc in scenes) + len(script.get("question", ""))
    if parole < PAROLE_MIN:
        problemes.append(f"trop court : {parole} caractères dits, au moins 1 150 pour tenir 60 secondes")
    textes = [script.get("titre", ""), script.get("question", ""), script.get("legende", "")]
    for k, sc in enumerate(scenes):
        textes += [sc.get("dit", ""), sc.get("ecran", "")]
        if len(sc.get("dit", "")) > 160:
            problemes.append(f"scène {k + 1} : voix trop longue ({len(sc['dit'])} caractères)")
        limite = {"citation": 120, "liste": 100}.get(sc.get("type"), 48)
        if len(sc.get("ecran", "")) > limite:
            problemes.append(f"scène {k + 1} : texte écran trop long ({len(sc['ecran'])} caractères)")
        if sc.get("type") == "liste" and len([x for x in sc.get("ecran", "").split(":")[-1].split("|") if x.strip()]) < 2:
            problemes.append(f"scène {k + 1} : liste sans ses étapes (« Titre : étape 1 | étape 2 »)")
        if sc.get("type") == "photo" and not (isinstance(sc.get("photo"), int) and 0 <= sc["photo"] < nb_photos):
            problemes.append(f"scène {k + 1} : portrait n°{sc.get('photo')} inexistant ({nb_photos} reçu(s))")
    tout = " ".join(textes)
    inventes = sorted(_nombres(tout) - _nombres(source) - {str(n) for n in range(0, 11)})
    if inventes:
        problemes.append("chiffres absents de la fiche : " + ", ".join(inventes))
    if re.search(r"\b(études?|étude|chercheurs?|scientifiques?|université|expérience menée|selon une)\b", tout, re.I):
        problemes.append("référence à une étude ou à des chercheurs : interdit, la fiche est la seule source")
    if len(script.get("legende", "")) > 2000:
        problemes.append("légende trop longue")
    return problemes


def _demander(cfg: dict, parties: list[dict], remarques: list[str]) -> dict:
    """Gemini (offre gratuite), avec bascule sur les modèles suivants si surchargé (comme script_video)."""
    import time

    import requests

    modeles = (cfg.get("video") or {}).get("modeles_gemini") or ["gemini-3.5-flash", "gemini-flash-latest"]
    consigne = "Écris le script du Reel sur ce sujet."
    if remarques:
        consigne += "\n\nTa version précédente a été refusée pour ces raisons, corrige-les :\n- " + "\n- ".join(remarques)
    erreur = ""
    for modele in modeles:
        for pause in (0, 20):
            time.sleep(pause)
            try:
                r = requests.post(f"https://generativelanguage.googleapis.com/v1beta/models/{modele}:generateContent",
                                  timeout=300, headers={"x-goog-api-key": os.environ["GEMINI_API_KEY"]},
                                  json={"systemInstruction": {"parts": [{"text": SYSTEME}]},
                                        "contents": [{"role": "user", "parts": parties + [{"text": consigne}]}],
                                        "generationConfig": {"responseMimeType": "application/json", "responseJsonSchema": SCHEMA,
                                                             "thinkingConfig": {"thinkingLevel": "low"}}})
            except requests.RequestException as e:
                erreur = f"{modele} : {type(e).__name__}"
                continue
            if r.status_code == 200:
                candidat = (r.json().get("candidates") or [{}])[0]
                if candidat.get("finishReason") not in (None, "STOP"):
                    raise RuntimeError(f"réponse Gemini inutilisable (finishReason={candidat.get('finishReason')})")
                return json.loads("".join(p.get("text", "") for p in candidat["content"]["parts"]))
            erreur = f"{modele} : HTTP {r.status_code} {r.text[:200]}"
            if r.status_code not in (429, 500, 503):
                break
    raise RuntimeError(f"Gemini indisponible ({erreur})")


def ecrire_script(cfg: dict, sujet: tuple, photos: list[Path], journal=print) -> dict:
    if not os.environ.get("GEMINI_API_KEY"):
        raise RuntimeError("clé GEMINI_API_KEY absente")
    source = fiche(sujet)
    parties: list[dict] = [{"text": f"<fiche>\n{source}\n</fiche>"}]
    if photos:
        parties.append({"text": f"{len(photos)} portrait(s) de Stéphane fourni(s), numéros 0 à {len(photos) - 1}."})
        for k, ph in enumerate(photos):
            parties += [{"text": f"Portrait n°{k} :"},
                        {"inlineData": {"mimeType": "image/jpeg", "data": base64.b64encode(ph.read_bytes()).decode()}}]
    else:
        parties.append({"text": "Aucun portrait fourni : pas de scène « photo »."})
    remarques: list[str] = []
    for essai in range(3):
        script = _demander(cfg, parties, remarques)
        remarques = controler(script, source, len(photos))
        if not remarques:
            return script
        journal(f"    ↺ script refusé ({essai + 1}/3) : " + " ; ".join(remarques)[:300])
    raise RuntimeError("script refusé au contrôle : " + " ; ".join(remarques)[:400])


def legende_finale(script: dict) -> str:
    texte = script["legende"].replace("—", ",").replace("–", "-").strip()
    tags = " ".join("#" + re.sub(r"\W", "", h.lstrip("#")) for h in script.get("hashtags", [])[:5] if re.sub(r"\W", "", h))
    return (texte + ("\n\n" + tags if tags else ""))[:2200]


# --------------------------------------------------------------------------- vidéo

def rendre(cfg: dict, script: dict, sujet: tuple, photos: list[Path], sortie: Path, journal=print, essai: bool = False) -> Path:
    from .voix import Voix

    p = cfg.get("perso") or {}
    dossier = MOTION / "public" / "_perso"
    shutil.rmtree(dossier, ignore_errors=True)
    dossier.mkdir(parents=True)
    noms = []
    for k, ph in enumerate(photos):
        shutil.copy(ph, dossier / f"photo{k}.jpg")
        noms.append(f"_perso/photo{k}.jpg")
    scenes, dits = [], []
    for sc in script["scenes"]:
        s = {"type": sc["type"], "ecran": sc.get("ecran") or None, "soustitre": sc["dit"]}
        if sc["type"] == "photo":
            if isinstance(sc.get("photo"), int) and sc["photo"] < len(noms):
                s["photo"] = noms[sc["photo"]]
            else:
                s["type"] = "texte"
        scenes.append(s)
        dits.append(sc["dit"])
    scenes.append({"type": "question", "ecran": script["question"], "soustitre": script["question"]})
    dits.append(script["question"] + " Dis-le moi en commentaire.")
    scenes.append({"type": "signature", "duree": 3.5})
    dits.append("")
    try:
        pistes = {x["cle"]: x for x in Voix(journal).narration(
            [{"cle": f"s{k}", "texte": t} for k, t in enumerate(dits)], dossier, "voix", forcer=essai) or []}
    except Exception as e:  # la voix ne bloque jamais la vidéo
        journal(f"⚠️ Voix off indisponible, Reel sans voix : {e}")
        pistes = {}
    for k, sc in enumerate(scenes):
        if f"s{k}" in pistes:
            sc["voix"] = {"src": pistes[f"s{k}"]["src"], "duree": pistes[f"s{k}"]["duree"]}
        elif sc["type"] != "signature":
            sc["duree"] = max(3.0, len(sc.get("soustitre") or "") / 15)  # sans voix : le temps de lire
    props = {"rubrique": CATEGORIES[sujet[1]], "titre": script["titre"], "nom": p.get("nom", "Stéphane Nzesseu"),
             "compte": p.get("compte", "@stephane_nzesseu"), "scenes": scenes, "musique": "melodie.wav", "volume_musique": 0.10}
    with tempfile.TemporaryDirectory() as d:
        fichier = Path(d) / "props.json"
        fichier.write_text(json.dumps(props, ensure_ascii=False), encoding="utf-8")
        r = subprocess.run(["npx.cmd" if shutil.which("npx.cmd") else "npx", "remotion", "render", "src/index.ts", "PersoReel",
                            str(sortie.resolve()), f"--props={fichier}", "--codec=h264", "--crf=20", "--log=warn"],
                           cwd=MOTION, capture_output=True, text=True, timeout=1800)
    shutil.rmtree(dossier, ignore_errors=True)
    if r.returncode != 0 or not sortie.exists():
        raise RuntimeError(f"rendu Remotion impossible (code {r.returncode}) : {(r.stderr + r.stdout)[-1500:]}")
    return sortie


# --------------------------------------------------------------------------- passage

def traiter_perso(cfg: dict, log, *, simulation: bool = False, essai: bool = False, sujet_id: str | None = None,
                  maintenant: datetime | None = None, sortie_essai: Path = RACINE / "sortie") -> bool:
    """Un passage. essai = fabrique le Reel du prochain sujet dans sortie/, sans publier ni rien enregistrer."""
    from .publieurs.instagram_perso import InstagramPerso

    p = cfg.get("perso") or {}
    maintenant = maintenant or datetime.now(timezone.utc)
    jour = maintenant.astimezone(ZoneInfo(cfg["fuseau_horaire"])).date()
    etat = EtatPerso()
    if not essai:
        if not p.get("publication"):
            log("Instagram perso : publication pas encore validée (config.yaml perso.publication) — rien n'est publié")
            return True
        pret, raison = est_le_moment(cfg, maintenant, etat)
        if not pret:
            log(f"Instagram perso : {raison}")
            return True
        if not InstagramPerso.est_configure():
            log("❌ Instagram perso : jeton absent (INSTAGRAM_PERSO_TOKEN)")
            return False

    sujet = PAR_ID[sujet_id] if sujet_id else prochain(etat.sujets_publies())
    log(f"Instagram perso : sujet « {sujet[2]} » ({CATEGORIES[sujet[1]]})" + ("  [SIMULATION]" if simulation else ""))
    if simulation:
        return True

    with tempfile.TemporaryDirectory() as d:
        dossier = Path(d)
        try:
            photos = portraits(cfg, dossier, f"{sujet[0]}-{jour}", journal=log)
            script = ecrire_script(cfg, sujet, photos, log)
            log(f"    📝 {len(script['scenes'])} scènes, {sum(len(s['dit']) for s in script['scenes'])} caractères dits")
            nom = f"reel-perso-{jour.isoformat()}.mp4"
            if essai:
                sortie_essai.mkdir(parents=True, exist_ok=True)
                video = rendre(cfg, script, sujet, photos, sortie_essai / nom, log, essai=True)
                (sortie_essai / "legende.txt").write_text(legende_finale(script), encoding="utf-8")
                log(f"✅ Reel d'essai fabriqué : {video.name} (+ legende.txt), rien n'est publié")
                return True
            video = rendre(cfg, script, sujet, photos, dossier / nom, log)
            from .hebergement import mettre_en_ligne
            url = mettre_en_ligne([video], jour)[video.name]
            pub = InstagramPerso(cfg, log)
            res = pub.publier_reel(url, legende_finale(script))
            etat.d["publications"].append({"jour": jour.isoformat(), "sujet": sujet[0], "url": res.url, "media_id": res.id})
            etat.d["echecs"].pop(sujet[0], None)
            log(f"✅ Instagram perso — Reel publié : {res.url}")
            try:
                pub.renouveler()
            except Exception as ex:
                log(f"⚠️ Renouvellement du jeton Instagram : {ex}")
            return True
        except Exception as ex:
            if essai:
                log(f"❌ Reel d'essai impossible : {ex}")
                return False
            n = etat.d["echecs"].get(sujet[0], 0) + 1
            etat.d["echecs"][sujet[0]] = n
            if n >= int(cfg["tentatives_max"]):  # sujet qui échoue toujours : on le saute pour ne pas bloquer la suite
                etat.d["publications"].append({"jour": None, "sujet": sujet[0], "saute": str(ex)[:200]})
            log(f"❌ Instagram perso (essai {n}) : {ex}")
            return False
        finally:
            if not essai:
                etat.sauver()


__all__ = ["traiter_perso", "est_le_moment", "controler", "EtatPerso", "fiche"]
