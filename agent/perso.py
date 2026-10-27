"""Compte Instagram de Stéphane : Reels « conseils et astuces psychologiques » de 60 secondes et plus, sans visage filmé.

Chaque jour de publication (config perso.jours), au premier passage après perso.heure : le sujet suivant du catalogue
(perso_sujets.py, adapté du skill marketing-psychology) devient un Reel. Gemini (gratuit) écrit trois accroches fortes,
garde la meilleure, puis le script rythmé (scènes courtes, émoji, mots clés, listes, comparaisons) et la légende, à
partir de la fiche du sujet seulement : aucune étude, aucun chercheur, aucun chiffre qui n'y figure pas (contrôlé).
Fonds réalistes : vidéos et photos libres Pixabay (medias_libres.py, facultatif). Voix Google (voix.py), rendu Remotion
(composition PersoReel), mise en ligne GitHub Pages, publication par la connexion Instagram directe.
"""
from __future__ import annotations

import json
import os
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
PAROLE_MIN = 1050  # caractères dits ≈ 60 secondes de vidéo avec la voix Schedar (884 caractères = 53 s le 27/10)
TYPES = ["accroche", "texte", "liste", "comparaison", "citation"]
_TXT = {"type": "string"}
_TXT_NUL = {"anyOf": [{"type": "string"}, {"type": "null"}]}
_NB_NUL = {"anyOf": [{"type": "number"}, {"type": "null"}]}

SCHEMA = {
    "type": "object",
    "properties": {
        "accroches": {"type": "array", "items": {"type": "object", "properties": {"formule": _TXT, "texte": _TXT},
                                                 "required": ["formule", "texte"], "additionalProperties": False}},
        "titre": _TXT,
        "scenes": {"type": "array", "items": {
            "type": "object",
            "properties": {
                "type": {"type": "string", "enum": TYPES},
                "emoji": _TXT,
                "ecran": _TXT,
                "dit": _TXT,
                "recherche": _TXT_NUL,
                "a": _TXT_NUL, "b": _TXT_NUL, "valeur_a": _NB_NUL, "valeur_b": _NB_NUL,
            },
            "required": ["type", "emoji", "ecran", "dit", "recherche", "a", "b", "valeur_a", "valeur_b"],
            "additionalProperties": False,
        }},
        "question": _TXT,
        "legende": _TXT,
        "hashtags": {"type": "array", "items": _TXT},
    },
    "required": ["accroches", "titre", "scenes", "question", "legende", "hashtags"],
    "additionalProperties": False,
}

FORMULES = """\
- Liste : « 3 choses que tu fais sans t'en rendre compte quand… », « 4 signes que ton cerveau te piège… »
- Pourquoi + nom : « Pourquoi tu gardes des choses inutiles ? Ça porte un nom. »
- Pas ta faute : « Si tu n'arrives pas à…, ce n'est pas ta faute. C'est ton cerveau. »
- Ordre : « Arrête de… tant que tu n'as pas vu ça. »
- Démasquer : « Les vendeurs utilisent ça sur toi tous les jours. »
- Contre-pied : « Tu crois que… ? C'est l'inverse. »
- Révélation : « Ce petit réflexe te coûte plus cher que tu ne crois. »
- Défi : « Personne ne m'a jamais expliqué ça, et ça a tout changé. »"""

SYSTEME = """Tu écris le script d'un Reel Instagram de 60 à 90 secondes pour le compte de Stéphane Nzesseu : des conseils \
et astuces de psychologie pour la vie de tous les jours et le travail. Public : francophones d'Afrique et d'Europe, \
entrepreneurs, salariés, étudiants, curieux, sans formation en psychologie. Ils regardent en faisant défiler : tu as \
2 secondes pour les arrêter, puis il faut une relance toutes les 10 secondes.

1. L'ACCROCHE décide de tout. Écris trois accroches de formules différentes (champ « accroches »), parmi celles-ci :
""" + FORMULES + """
Une accroche : 12 mots au plus, concrète, elle vise le spectateur (« tu »), crée une tension ou une curiosité, et ne \
donne pas encore la réponse. Garde la plus forte : elle devient la première scène (type « accroche »).

2. Le déroulé, une idée par scène, entre 13 et 18 scènes courtes :
- accroche ; puis une relance qui promet la suite (« Et le pire, c'est la troisième. »)
- le nom du mécanisme, dit simplement (« Ça s'appelle l'aversion à la perte. »)
- des situations où le spectateur se reconnaît (marché, famille, bureau, téléphone, boutique, argent)
- pourquoi le cerveau fait ça, en une phrase, sans jargon
- si l'accroche annonce une liste, chaque point a sa scène, numérotée à l'oral (« Un. », « Deux. »)
- l'astuce, en 2 ou 3 étapes concrètes (une scène « liste »)
- comment s'en protéger quand les autres s'en servent, si c'est pertinent
- la phrase à retenir (une scène « citation »)
Ne pose pas la question finale dans les scènes et ne parle pas de commentaire : la question va seulement dans le \
champ « question », elle sera ajoutée à la fin.

Exactitude (impératif) :
- Ta seule source est la fiche du sujet. N'invente aucune étude, expérience, chercheur, pourcentage ni statistique. \
Les seuls chiffres permis sont ceux de la fiche et de petits nombres d'exemple (« 3 options »).
- Ne dis pas « les études montrent », « les scientifiques ont prouvé ».
- Exemples ordinaires et plausibles, sans nom de personne, de marque ou d'entreprise réelle.
- Reste éthique : on explique pour aider, jamais pour manipuler.

Ton : celui de Stéphane, direct, chaleureux, un peu malicieux. Il tutoie. Français oral, simple et correct, phrases \
courtes et rythmées. Pas de ton publicitaire, pas de tiret long (—).

Chaque scène :
- « dit » : la voix, entre 50 et 120 caractères (3 à 7 secondes). En tout, au moins 1 150 caractères dits.
- « emoji » : UN émoji qui illustre la scène (😱 🧠 💸 🛒 📱 ⏳ 🔥 ✅ ❌ 🤔 💡 🎯 …), varié d'une scène à l'autre.
- « ecran » : le texte affiché en grand, 6 mots au plus, avec le ou les mots clés entre astérisques (« Tu *détestes* perdre »).
  - « accroche » : l'accroche choisie, 12 mots au plus.
  - « liste » : « Titre : étape 1 | étape 2 | étape 3 », 90 caractères au plus.
  - « comparaison » : deux barres ; « a » et « b » = leurs noms (2 mots), « valeur_a » et « valeur_b » = leurs tailles \
relatives, tirées de la fiche (perte 2, gain 1) ou évidentes (1 et 3) ; « ecran » = le titre. Seulement si le sujet s'y \
prête, au plus une fois.
  - « citation » : la phrase à retenir, 110 caractères au plus, « dit » = la même phrase.
- « recherche » : pour environ une scène sur deux, et toujours pour l'accroche, 2 à 4 mots EN ANGLAIS pour trouver une \
vidéo réaliste de fond dans une banque d'images (« woman shopping market », « man stressed phone ») ; sinon null.
- « a », « b », « valeur_a », « valeur_b » : null sauf pour « comparaison ».

« titre » : le nom du mécanisme, 45 caractères au plus.
« question » : une question courte qui donne envie de répondre (expérience personnelle, choix entre deux).
« legende » : la légende Instagram. Première ligne : l'accroche, 125 caractères au plus. Puis 2 à 4 courts paragraphes \
séparés par une ligne vide, qui résument l'astuce sans recopier la vidéo. Termine par la question. Pas de lien, pas de \
hashtag dans le texte, 2 ou 3 émojis au plus.
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


# --------------------------------------------------------------------------- script

def fiche(sujet: tuple) -> str:
    ident, cat, nom, idee, astuce = sujet
    return f"Catégorie : {CATEGORIES[cat]}\nMécanisme : {nom}\nL'idée : {idee}\nL'astuce : {astuce}"


def _nombres(texte: str) -> set[str]:
    t = re.sub(r"(?<=\d)[   .](?=\d{3}\b)", "", texte)
    return {n.replace(",", ".") for n in re.findall(r"\d+(?:,\d+)?", t)}


def controler(script: dict, source: str) -> list[str]:
    """Problèmes qui interdisent d'utiliser le script (vide = bon)."""
    problemes = []
    scenes = script.get("scenes") or []
    if not 12 <= len(scenes) <= 20:
        problemes.append(f"{len(scenes)} scènes (13 à 18 attendues)")
    if not scenes or scenes[0].get("type") != "accroche":
        problemes.append("la première scène doit être l'accroche (type « accroche »)")
    elif len(re.sub(r"\*", "", scenes[0].get("ecran", "")).split()) > 13:
        problemes.append("accroche trop longue (12 mots au plus)")
    if len(script.get("accroches") or []) < 3:
        problemes.append("il faut trois accroches de formules différentes")
    parole = sum(len(sc.get("dit", "")) for sc in scenes) + len(script.get("question", ""))
    if parole < PAROLE_MIN:
        problemes.append(f"trop court : {parole} caractères dits, au moins 1 150 pour tenir 60 secondes")
    textes = [script.get("titre", ""), script.get("question", ""), script.get("legende", "")]
    for k, sc in enumerate(scenes):
        textes += [sc.get("dit", ""), sc.get("ecran", ""), str(sc.get("a") or ""), str(sc.get("b") or "")]
        if len(sc.get("dit", "")) > 150:
            problemes.append(f"scène {k + 1} : voix trop longue ({len(sc['dit'])} caractères)")
        limite = {"citation": 120, "liste": 100, "accroche": 90}.get(sc.get("type"), 48)
        if len(sc.get("ecran", "")) > limite:
            problemes.append(f"scène {k + 1} : texte écran trop long ({len(sc['ecran'])} caractères)")
        if sc.get("type") == "liste" and len([x for x in sc.get("ecran", "").split(":")[-1].split("|") if x.strip()]) < 2:
            problemes.append(f"scène {k + 1} : liste sans ses étapes (« Titre : étape 1 | étape 2 »)")
        if sc.get("type") == "comparaison" and not (sc.get("valeur_a") and sc.get("valeur_b") and sc.get("a") and sc.get("b")):
            problemes.append(f"scène {k + 1} : comparaison sans ses deux barres (a, b, valeur_a, valeur_b)")
        if re.search(r"\bcommentaires?\b", sc.get("dit", "") + sc.get("ecran", ""), re.I):
            problemes.append(f"scène {k + 1} : ne parle pas de commentaire dans les scènes (la question est ajoutée à la fin)")
    tout = " ".join(textes)
    inventes = sorted(_nombres(tout) - _nombres(source) - {str(n) for n in range(0, 11)})
    if inventes:
        problemes.append("chiffres absents de la fiche : " + ", ".join(inventes))
    if re.search(r"\b(études?|chercheurs?|scientifiques?|université|expérience menée|selon une)\b", tout, re.I):
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
        for pause in (0, 30):
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


def ecrire_script(cfg: dict, sujet: tuple, journal=print) -> dict:
    if not os.environ.get("GEMINI_API_KEY"):
        raise RuntimeError("clé GEMINI_API_KEY absente")
    source = fiche(sujet)
    parties = [{"text": f"<fiche>\n{source}\n</fiche>"}]
    remarques: list[str] = []
    for essai in range(3):
        script = _demander(cfg, parties, remarques)
        remarques = controler(script, source)
        if not remarques:
            return script
        journal(f"    ↺ script refusé ({essai + 1}/3) : " + " ; ".join(remarques)[:300])
    raise RuntimeError("script refusé au contrôle : " + " ; ".join(remarques)[:400])


def legende_finale(script: dict) -> str:
    texte = script["legende"].replace("—", ",").replace("–", "-").strip()
    tags = " ".join("#" + re.sub(r"\W", "", h.lstrip("#")) for h in script.get("hashtags", [])[:5] if re.sub(r"\W", "", h))
    return (texte + ("\n\n" + tags if tags else ""))[:2200]


# --------------------------------------------------------------------------- vidéo

def rendre(cfg: dict, script: dict, sujet: tuple, sortie: Path, journal=print, essai: bool = False) -> Path:
    from .medias_libres import chercher, disponible
    from .voix import Voix

    p = cfg.get("perso") or {}
    if not (MOTION / "node_modules").exists():  # machine neuve (GitHub : à chaque passage), comme scenario.rendre_video
        subprocess.run(["npm.cmd" if shutil.which("npm.cmd") else "npm", "ci", "--no-audit", "--no-fund"],
                       cwd=MOTION, check=True, capture_output=True, timeout=900)
    dossier = MOTION / "public" / "_perso"
    shutil.rmtree(dossier, ignore_errors=True)
    dossier.mkdir(parents=True)
    scenes, dits, pris = [], [], set()
    if not disponible():
        journal("ℹ️ aucune clé Pixabay (PIXABAY_API_KEY) : fonds animés seulement, sans vidéos réalistes")
    for k, sc in enumerate(script["scenes"]):
        s = {"type": sc["type"], "emoji": sc.get("emoji") or None, "ecran": sc.get("ecran") or None, "soustitre": sc["dit"]}
        if sc["type"] == "comparaison":
            s.update(a=sc.get("a"), b=sc.get("b"), valeur_a=sc.get("valeur_a"), valeur_b=sc.get("valeur_b"))
        if sc.get("recherche") and sc["type"] in ("accroche", "texte"):
            trouve = chercher(sc["recherche"], dossier, f"fond{k}", pris)
            if trouve:
                s["media"] = {"src": f"_perso/{trouve[0].name}", "video": trouve[1]}
        scenes.append(s)
        dits.append(sc["dit"])
    question = script["question"].strip()
    scenes.append({"type": "question", "emoji": "💬", "ecran": question, "soustitre": question})
    dits.append(question)  # dite une seule fois ; l'invitation au commentaire est écrite à l'écran
    scenes.append({"type": "signature", "duree": 3.0})
    dits.append("")
    journal(f"    🎬 {sum('media' in s for s in scenes)} fond(s) réaliste(s)")
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
            sc["duree"] = max(2.5, len(sc.get("soustitre") or "") / 15)  # sans voix : le temps de lire
    props = {"rubrique": CATEGORIES[sujet[1]], "titre": script["titre"], "nom": p.get("nom", "Stéphane Nzesseu"),
             "compte": p.get("compte", "@stephane_nzesseu"), "scenes": scenes, "musique": "melodie.wav", "volume_musique": 0.12}
    with tempfile.TemporaryDirectory() as d:
        fichier = Path(d) / "props.json"
        fichier.write_text(json.dumps(props, ensure_ascii=False), encoding="utf-8")
        r = subprocess.run(["npx.cmd" if shutil.which("npx.cmd") else "npx", "remotion", "render", "src/index.ts", "PersoReel",
                            str(sortie.resolve()), f"--props={fichier}", "--codec=h264", "--crf=20", "--log=warn"],
                           cwd=MOTION, capture_output=True, text=True, timeout=2400)
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
            script = ecrire_script(cfg, sujet, log)
            log(f"    📝 accroche « {script['scenes'][0]['ecran']} », {len(script['scenes'])} scènes, "
                f"{sum(len(s['dit']) for s in script['scenes'])} caractères dits")
            nom = f"reel-perso-{jour.isoformat()}.mp4"
            if essai:
                sortie_essai.mkdir(parents=True, exist_ok=True)
                video = rendre(cfg, script, sujet, sortie_essai / nom, log, essai=True)
                (sortie_essai / "legende.txt").write_text(legende_finale(script), encoding="utf-8")
                (sortie_essai / "script.json").write_text(json.dumps(script, ensure_ascii=False, indent=1), encoding="utf-8")
                log(f"✅ Reel d'essai fabriqué : {video.name} (+ legende.txt, script.json), rien n'est publié")
                return True
            video = rendre(cfg, script, sujet, dossier / nom, log)
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
