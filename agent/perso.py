"""Compte Instagram personnel de Stéphane : de la matière qu'il dépose dans Drive au Reel publié.

Dossier Drive « Instagram perso » (config perso.dossier_drive), partagé en Éditeur avec le compte de service :
    📁 Instagram perso/
        📁 Mon premier livre/        une idée = un sous-dossier : notes (Google Doc, .txt), photos (.jpg/.png),
            notes.txt, photo.jpg      message vocal (.m4a, .mp3, .ogg, .wav). Le nom est libre.
        souvenir.txt                  un fichier seul à la racine (note ou vocal) = une idée aussi
        📁 _photos/                   portraits de Stéphane, utilisés quand une idée n'a pas de photo

Les jours de publication (config perso.jours), au premier passage après perso.heure : l'idée la plus ancienne non
traitée devient un Reel. Gemini (gratuit) en tire le script : rubrique, scènes, légende. Il ne met en forme que ce que
Stéphane a écrit ou dit : aucun fait inventé (contrôle des chiffres). Voix Google (voix.py), rendu Remotion
(composition PersoReel), mise en ligne GitHub Pages, publication par la connexion Instagram directe.

Le dossier traité est renommé « [PUBLIÉ] … » et sa description reçoit la légende et le lien. Rien de personnel n'est
écrit dans le dépôt (public) : etat/perso.json ne garde que des identifiants, des rubriques, des dates et des liens.
"""
from __future__ import annotations

import base64
import json
import os
import re
import shutil
import subprocess
import tempfile
from datetime import date, datetime, timezone
from pathlib import Path
from zoneinfo import ZoneInfo

RACINE = Path(__file__).resolve().parent.parent
MOTION = RACINE / "motion"
ETAT = RACINE / "etat" / "perso.json"

RUBRIQUES = {
    "carnet": ("Carnet d'écrivain", "une pensée, une phrase, un court extrait de ses textes"),
    "histoires": ("Histoires vraies", "un récit de vie qu'il a recueilli ou vécu, comme un biographe le raconte"),
    "coulisses": ("Coulisses de scène", "un souvenir d'événement qu'il a animé ou présenté"),
    "parcours": ("Leçons de parcours", "ses valeurs, ce que la vie lui a appris, entre l'Afrique et l'Europe"),
    "regard": ("Mon regard", "son avis sur un sujet d'actualité"),
}
JOURS = ["lundi", "mardi", "mercredi", "jeudi", "vendredi", "samedi", "dimanche"]
TEXTES = {".txt", ".md"}
IMAGES = {".jpg", ".jpeg", ".png", ".webp"}
AUDIOS = {".m4a": "audio/mp4", ".mp3": "audio/mpeg", ".ogg": "audio/ogg", ".opus": "audio/ogg", ".wav": "audio/wav",
          ".aac": "audio/aac"}
GDOC = "application/vnd.google-apps.document"
GFOLDER = "application/vnd.google-apps.folder"
AUDIO_MAX = 15 * 1024 * 1024  # Gemini : 20 Mo par requête en tout

SCHEMA = {
    "type": "object",
    "properties": {
        "rubrique": {"type": "string", "enum": list(RUBRIQUES)},
        "transcription": {"type": "string"},
        "titre": {"type": "string"},
        "scenes": {"type": "array", "items": {
            "type": "object",
            "properties": {
                "type": {"type": "string", "enum": ["photo", "citation", "texte"]},
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
    "required": ["rubrique", "transcription", "titre", "scenes", "question", "legende", "hashtags"],
    "additionalProperties": False,
}

SYSTEME = """Tu écris le script d'un Reel Instagram (vidéo verticale de 30 à 50 secondes) pour le compte personnel de \
Stéphane Nzesseu : écrivain, biographe, présentateur d'événements, entre l'Afrique et l'Europe. Son Instagram est son \
espace personnel : il y parle de tout ce qu'il est et fait, à la première personne.

Tu reçois sa matière brute : notes écrites, messages vocaux, photos. Ton travail est de la mettre en forme, pas d'en \
ajouter.

Exactitude (impératif) :
- N'invente rien : aucun fait, lieu, date, chiffre, nom, anecdote ou émotion qui ne soit pas dans sa matière.
- Chaque chiffre que tu écris doit figurer dans la matière (notes ou transcription), recopié à l'identique.
- Ne nomme personne qui n'est pas nommé dans la matière. Pour un récit de vie recueilli, garde l'anonymat \
(« une dame de 80 ans ») sauf si la note dit explicitement que la personne est d'accord pour être nommée.
- Si la matière est trop mince pour un Reel, fais court (5 scènes) plutôt que d'inventer.

« transcription » : la transcription fidèle des messages vocaux, mot pour mot (vide s'il n'y en a pas).

« rubrique », la plus proche de la matière :
""" + "\n".join(f"- {k} : {nom}, {desc}" for k, (nom, desc) in RUBRIQUES.items()) + """

Ton : la voix de Stéphane, à la première personne (« je »), chaleureuse, posée, sincère. Français simple et correct, \
phrases courtes. Tutoie le spectateur quand tu t'adresses à lui. Pas de ton publicitaire, pas de formule toute faite \
(« dans un monde où », « plus que jamais »), pas de tiret long (—).

Scènes, entre 5 et 10 (une idée par scène) :
- La première scène accroche : une phrase concrète qui donne envie de rester.
- « photo » : une de ses photos, par son numéro (0 = la première reçue) ; « ecran » = l'idée clé, 34 caractères au plus. \
N'utilise que les numéros reçus, varie les photos, et mets photo à null pour les autres types.
- « citation » : une phrase forte de sa matière, affichée en grand en italique ; « ecran » = la phrase, 110 caractères \
au plus, et « dit » = la même phrase.
- « texte » : une idée clé en grand ; « ecran » = 40 caractères au plus.
- « dit » : ce que dit la voix, 140 caractères au plus (environ 7 secondes).
Avec des photos reçues, au moins la moitié des scènes sont des scènes « photo » (la première scène aussi). \
Sans photo reçue, n'utilise que « citation » et « texte ».

« question » : une question au spectateur, courte, qui invite à partager son expérience.
« titre » : 45 caractères au plus (usage interne).
« legende » : la légende Instagram. Première ligne : une accroche de 125 caractères au plus. Puis 2 à 4 courts \
paragraphes séparés par une ligne vide, qui prolongent la vidéo sans la répéter. Termine par la question. Pas de lien, \
pas de hashtag dans le texte, 1 ou 2 émojis au plus.
« hashtags » : 3 à 5 hashtags précis, sans le #."""


# --------------------------------------------------------------------------- état (aucune donnée personnelle)

class EtatPerso:
    def __init__(self, chemin: Path = ETAT):
        self.chemin = chemin
        self.d = json.loads(chemin.read_text(encoding="utf-8")) if chemin.exists() else {}
        self.d.setdefault("idees", {})
        self.d.setdefault("publications", [])

    def idee(self, ident: str) -> dict:
        return self.d["idees"].setdefault(ident, {"statut": "nouveau", "tentatives": 0})

    def publie_le(self, jour: date) -> bool:
        return any(p.get("jour") == jour.isoformat() for p in self.d["publications"])

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


# --------------------------------------------------------------------------- Drive

class DrivePerso:
    """Lecture du dossier « Instagram perso » avec le compte de service déjà utilisé pour les lots."""

    def __init__(self, dossier_id: str):
        from .sources import SourceDrive
        os.environ["DRIVE_FOLDER_ID"] = dossier_id
        self.src = SourceDrive.depuis_env()
        self.svc = self.src.svc
        self.racine = dossier_id

    def _enfants(self, parent: str) -> list[dict]:
        out, token = [], None
        while True:
            r = self.svc.files().list(q=f"'{parent}' in parents and trashed = false", pageSize=1000, pageToken=token,
                                      fields="nextPageToken, files(id, name, mimeType, createdTime, size)",
                                      supportsAllDrives=True, includeItemsFromAllDrives=True).execute()
            out += r.get("files", [])
            token = r.get("nextPageToken")
            if not token:
                return out

    def idees(self) -> list[dict]:
        """Idées dans l'ordre de dépôt : sous-dossiers et fichiers seuls (note ou vocal), hors « [ » et « _ »."""
        out = []
        for f in self._enfants(self.racine):
            if f["name"].startswith(("[", "_", ".")):
                continue
            ext = Path(f["name"]).suffix.lower()
            if f["mimeType"] == GFOLDER or f["mimeType"] == GDOC or ext in TEXTES or ext in AUDIOS:
                out.append(f)
        return sorted(out, key=lambda f: f["createdTime"])

    def fichiers(self, idee: dict) -> list[dict]:
        return self._enfants(idee["id"]) if idee["mimeType"] == GFOLDER else [idee]

    def portraits(self) -> list[dict]:
        dossier = next((f for f in self._enfants(self.racine) if f["mimeType"] == GFOLDER and f["name"].lower() == "_photos"), None)
        return [f for f in self._enfants(dossier["id"]) if Path(f["name"]).suffix.lower() in IMAGES] if dossier else []

    def lire_texte(self, f: dict) -> str:
        from .sources import Fichier
        return self.src.lire_texte(Fichier(f["id"], f["name"], f["mimeType"]))

    def telecharger(self, f: dict, dossier: Path) -> Path:
        from .sources import Fichier
        return self.src.telecharger(Fichier(f["id"], _nom_sur(f["name"]), f["mimeType"]), dossier)

    def marquer(self, idee: dict, prefixe: str, rapport: str) -> None:
        from .sources import Dossier
        self.src.marquer(Dossier(idee["id"], idee["name"]), prefixe, rapport)


def _nom_sur(nom: str) -> str:
    return re.sub(r"[^\w.\-]+", "_", nom)


# --------------------------------------------------------------------------- matière → script

def rassembler(drive: DrivePerso, idee: dict, dossier: Path, journal=print) -> dict:
    """Notes (texte), photos (fichiers locaux) et vocaux (fichiers locaux) d'une idée."""
    notes, photos, vocaux = [], [], []
    for f in sorted(drive.fichiers(idee), key=lambda f: f["name"].lower()):
        ext = Path(f["name"]).suffix.lower()
        try:
            if f["mimeType"] == GDOC or ext in TEXTES:
                notes.append(drive.lire_texte(f).strip())
            elif ext in IMAGES:
                photos.append(drive.telecharger(f, dossier))
            elif ext in AUDIOS:
                if int(f.get("size") or 0) > AUDIO_MAX:
                    journal(f"⚠️ vocal trop long ignoré ({int(f['size']) // 1_000_000} Mo, 15 Mo au plus) : {f['name']}")
                    continue
                vocaux.append(drive.telecharger(f, dossier))
            elif ext in (".heic", ".heif"):
                journal(f"⚠️ photo HEIC ignorée (iPhone : choisir « Le plus compatible » ou envoyer en JPEG) : {f['name']}")
        except Exception as e:
            journal(f"⚠️ fichier illisible ignoré ({type(e).__name__}) : {f['name']}")
    return {"notes": [n for n in notes if n], "photos": photos, "vocaux": vocaux}


def _image_reduite(chemin: Path, cote: int = 1280) -> tuple[bytes, Path]:
    """JPEG d'au plus `cote` px : envoyé à Gemini et utilisé dans la vidéo (orientation EXIF appliquée)."""
    from PIL import Image, ImageOps
    im = ImageOps.exif_transpose(Image.open(chemin)).convert("RGB")
    im.thumbnail((cote, cote))
    sortie = chemin.with_name(chemin.stem + "_r.jpg")
    im.save(sortie, "JPEG", quality=88)
    return sortie.read_bytes(), sortie


def _nombres(texte: str) -> set[str]:
    t = re.sub(r"(?<=\d)[   .](?=\d{3}\b)", "", texte)
    return {n.replace(",", ".") for n in re.findall(r"\d+(?:,\d+)?", t)}


def controler(script: dict, matiere_texte: str, nb_photos: int) -> list[str]:
    """Problèmes qui interdisent d'utiliser le script (vide = bon)."""
    problemes = []
    scenes = script.get("scenes") or []
    if not 4 <= len(scenes) <= 12:
        problemes.append(f"{len(scenes)} scènes (5 à 10 attendues)")
    textes = [script.get("question", ""), script.get("legende", "")]
    for k, sc in enumerate(scenes):
        textes += [sc.get("dit", ""), sc.get("ecran", "")]
        if len(sc.get("dit", "")) > 160:
            problemes.append(f"scène {k + 1} : voix trop longue ({len(sc['dit'])} caractères)")
        limite = 120 if sc.get("type") == "citation" else 48
        if len(sc.get("ecran", "")) > limite:
            problemes.append(f"scène {k + 1} : texte écran trop long ({len(sc['ecran'])} caractères)")
        if sc.get("type") == "photo" and not (isinstance(sc.get("photo"), int) and 0 <= sc["photo"] < nb_photos):
            problemes.append(f"scène {k + 1} : photo n°{sc.get('photo')} inexistante ({nb_photos} reçue(s))")
    if nb_photos and sum(sc.get("type") == "photo" for sc in scenes) < min(2, len(scenes)):
        problemes.append("photos reçues mais pas utilisées : au moins la moitié des scènes doivent être des scènes « photo »")
    permis = _nombres(matiere_texte + " " + script.get("transcription", "")) | {str(n) for n in range(0, 11)}
    inventes = sorted(_nombres(" ".join(textes)) - permis)
    if inventes:
        problemes.append("chiffres absents de la matière : " + ", ".join(inventes))
    if len(script.get("legende", "")) > 2000:
        problemes.append("légende trop longue")
    return problemes


def _demander(cfg: dict, parties: list[dict], remarques: list[str]) -> dict:
    """Gemini (offre gratuite), avec bascule sur les modèles suivants si surchargé (comme script_video)."""
    import time

    import requests

    modeles = (cfg.get("video") or {}).get("modeles_gemini") or ["gemini-3.5-flash", "gemini-flash-latest"]
    consigne = "Écris le script du Reel à partir de cette matière."
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


def ecrire_script(cfg: dict, matiere: dict, journal=print) -> dict:
    if not os.environ.get("GEMINI_API_KEY"):
        raise RuntimeError("clé GEMINI_API_KEY absente")
    if not (matiere["notes"] or matiere["vocaux"]):
        raise ValueError("ni note ni message vocal : il faut au moins quelques lignes ou un vocal pour faire un Reel")
    parties: list[dict] = []
    texte = "\n\n".join(matiere["notes"])
    if texte:
        parties.append({"text": f"<notes>\n{texte}\n</notes>"})
    for k, chemin in enumerate(matiere["photos"]):
        donnees, reduite = _image_reduite(chemin)
        matiere["photos"][k] = reduite
        parties += [{"text": f"Photo n°{k} :"}, {"inlineData": {"mimeType": "image/jpeg", "data": base64.b64encode(donnees).decode()}}]
    for chemin in matiere["vocaux"]:
        parties += [{"text": "Message vocal de Stéphane :"},
                    {"inlineData": {"mimeType": AUDIOS[chemin.suffix.lower()], "data": base64.b64encode(chemin.read_bytes()).decode()}}]
    remarques: list[str] = []
    for _ in range(2):
        script = _demander(cfg, parties, remarques)
        remarques = controler(script, texte, len(matiere["photos"]))
        if not remarques:
            return script
    raise ValueError("script refusé au contrôle : " + " ; ".join(remarques)[:400])


def legende_finale(script: dict) -> str:
    texte = script["legende"].replace("—", ",").replace("–", "-").strip()
    tags = " ".join("#" + re.sub(r"\W", "", h.lstrip("#")) for h in script.get("hashtags", [])[:5] if re.sub(r"\W", "", h))
    return (texte + ("\n\n" + tags if tags else ""))[:2200]


# --------------------------------------------------------------------------- vidéo

def rendre(cfg: dict, script: dict, photos: list[Path], sortie: Path, journal=print, essai: bool = False) -> Path:
    from .voix import Voix

    p = cfg.get("perso") or {}
    dossier = MOTION / "public" / "_perso"
    shutil.rmtree(dossier, ignore_errors=True)
    dossier.mkdir(parents=True)
    noms = []
    for k, ph in enumerate(photos):
        nom = f"photo{k}.jpg"
        shutil.copy(ph, dossier / nom)
        noms.append(f"_perso/{nom}")
    scenes, dits = [], []
    for sc in script["scenes"]:
        s = {"type": sc["type"], "ecran": sc.get("ecran") or None, "soustitre": sc["dit"]}
        if sc["type"] == "photo" and isinstance(sc.get("photo"), int) and sc["photo"] < len(noms):
            s["photo"] = noms[sc["photo"]]
        scenes.append(s)
        dits.append(sc["dit"])
    scenes.append({"type": "question", "ecran": script["question"], "soustitre": script["question"]})
    dits.append(script["question"])
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
    props = {"rubrique": RUBRIQUES[script["rubrique"]][0], "titre": script["titre"], "nom": p.get("nom", "Stéphane Nzesseu"),
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

def traiter_perso(cfg: dict, log, *, simulation: bool = False, essai: bool = False,
                  maintenant: datetime | None = None, sortie_essai: Path = RACINE / "sortie") -> bool:
    """Un passage. essai = fabrique le Reel de la prochaine idée dans sortie/, sans publier ni rien marquer."""
    from .publieurs.instagram_perso import InstagramPerso

    p = cfg.get("perso") or {}
    if not p.get("dossier_drive"):
        log("Instagram perso : dossier Drive pas encore configuré (config.yaml perso.dossier_drive)")
        return True
    maintenant = maintenant or datetime.now(timezone.utc)
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

    drive = DrivePerso(p["dossier_drive"])
    idees = [i for i in drive.idees() if etat.idee(i["id"])["statut"] in ("nouveau", "echec")
             and etat.idee(i["id"])["tentatives"] < int(cfg["tentatives_max"])]
    log(f"Instagram perso : {len(idees)} idée(s) en attente dans le Drive" + ("  [SIMULATION]" if simulation else ""))
    if not idees:
        log("⚠️ Instagram perso : plus aucune idée à publier — déposer de la matière dans le dossier Drive")
        return True
    idee = idees[0]
    if simulation:
        log("    [simulation] prochain Reel : l'idée la plus ancienne du dossier")
        return True

    ok = True
    with tempfile.TemporaryDirectory() as d:
        dossier = Path(d)
        e = etat.idee(idee["id"])
        try:
            matiere = rassembler(drive, idee, dossier, log)
            if not matiere["photos"]:  # pas de photo dans l'idée : deux portraits du dossier _photos
                import random
                portraits = drive.portraits()
                for f in random.Random(idee["id"]).sample(portraits, min(2, len(portraits))):
                    matiere["photos"].append(drive.telecharger(f, dossier))
            script = ecrire_script(cfg, matiere, log)
            log(f"    📝 rubrique « {RUBRIQUES[script['rubrique']][0]} », {len(script['scenes'])} scènes")
            nom = f"reel-perso-{maintenant.astimezone(ZoneInfo(cfg['fuseau_horaire'])).date().isoformat()}.mp4"
            if essai:
                sortie_essai.mkdir(parents=True, exist_ok=True)
                video = rendre(cfg, script, matiere["photos"], sortie_essai / nom, log, essai=True)
                (sortie_essai / "legende.txt").write_text(legende_finale(script), encoding="utf-8")
                log(f"✅ Reel d'essai fabriqué : {video.name} (+ legende.txt), rien n'est publié")
                return True
            video = rendre(cfg, script, matiere["photos"], dossier / nom, log)
            from .hebergement import mettre_en_ligne
            jour = maintenant.astimezone(ZoneInfo(cfg["fuseau_horaire"])).date()
            url = mettre_en_ligne([video], jour)[video.name]
            pub = InstagramPerso(cfg, log)
            legende = legende_finale(script)
            res = pub.publier_reel(url, legende)
            e.update(statut="publie", rubrique=script["rubrique"], url=res.url, media_id=res.id,
                     date=datetime.now(timezone.utc).isoformat(timespec="seconds"))
            etat.d["publications"].append({"jour": jour.isoformat(), "idee": idee["id"], "url": res.url, "rubrique": script["rubrique"]})
            drive.marquer(idee, "[PUBLIÉ]", f"Publié le {jour.strftime('%d/%m/%Y')} : {res.url}\n\n{legende}")
            log(f"✅ Instagram perso — Reel publié : {res.url}")
            try:
                pub.renouveler()
            except Exception as ex:
                log(f"⚠️ Renouvellement du jeton Instagram : {ex}")
        except ValueError as ex:  # matière inutilisable : on le dit dans le Drive et on passe à l'idée suivante
            e.update(statut="ecarte", erreur=str(ex)[:300])
            if not essai:
                drive.marquer(idee, "[À COMPLÉTER]", f"Pas de Reel tiré de cette idée : {ex}")
            log(f"⚠️ Instagram perso — idée écartée : {ex}")
        except Exception as ex:
            ok = False
            e["tentatives"] = e.get("tentatives", 0) + 1
            e.update(statut="echec", erreur=str(ex)[:500])
            log(f"❌ Instagram perso (essai {e['tentatives']}) : {ex}")
        if not essai:
            etat.sauver()
    return ok


__all__ = ["traiter_perso", "est_le_moment", "controler", "EtatPerso", "RUBRIQUES"]
