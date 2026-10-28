"""Gabarit V3 des Shorts (composition Remotion DecideShortV3), en production depuis le 27/10/2026 (config video.gabarit).

Le rythme des Reels perso (accroche choisie parmi trois, une idée courte par scène, texte cinétique, karaoké) avec
la pédagogie DECIDE (« Prenons un exemple », dessins, personnages) et des fonds réalistes libres :
- Wikimedia Commons pour ce que l'article nomme (institution, ville, bâtiment, logo officiel), crédit affiché ;
- Pixabay pour un décor générique (marché, route, banque), qui illustre le cadre et jamais l'événement lui-même.
Le script est écrit par Gemini (gratuit) et contrôlé par script_video.controler (chiffres, tutoiement, « fictif »).
"""
from __future__ import annotations

import json
import os
import re
import shutil
import subprocess
import tempfile
from pathlib import Path

from .gabarit_v2 import _insecables
from .scenario import MOTION, RUBRIQUES, _date_fr
from .script_video import ILLUSTRATIONS, SCHEMA as SCHEMA_V2, _demander_gemini, _nombres, controler
from .voix import Voix

SCRIPTS_V3 = MOTION.parent / "etat" / "scripts_v3"
_TXT_NUL = {"anyOf":[{"type": "string"}, {"type": "null"}]}
_SCENE_V2 = SCHEMA_V2["properties"]["scenes"]["items"]

SCHEMA = {
    "type": "object",
    "properties": {
        "accroches": {"type": "array", "items": {"type": "string"}},
        "titre": {"type": "string"},
        "scenes": {"type": "array", "items": {
            "type": "object",
            "properties": {
                "type": {"type": "string", "enum": ["accroche", "media", "explication"]},
                "etiquette": {"type": "string"},
                "illustration": _SCENE_V2["properties"]["illustration"],
                "fond": {"anyOf": [{"type": "null"}, {
                    "type": "object",
                    "properties": {"source": {"type": "string", "enum": ["commons", "pixabay"]}, "recherche": {"type": "string"},
                                   "logo": {"type": "boolean"}, "secours": _TXT_NUL},
                    "required": ["source", "recherche", "logo", "secours"], "additionalProperties": False}]},
                "ecran": {"type": "string"},
                "dit": {"type": "string"},
            },
            "required": ["type", "etiquette", "illustration", "fond", "ecran", "dit"],
            "additionalProperties": False,
        }},
        "question": {"type": "string"},
    },
    "required": ["accroches", "titre", "scenes", "question"],
    "additionalProperties": False,
}

SYSTEME = """Tu écris le script d'une courte vidéo verticale (Short) de DECIDE média, qui explique l'actualité économique \
à des gens ordinaires d'Afrique centrale et de l'Ouest : commerçants, artisans, parents, étudiants, sans culture financière. \
Ils regardent en faisant défiler : tu as 2 secondes pour les arrêter, puis il faut une relance toutes les 10 secondes.

1. L'ACCROCHE. Écris trois accroches de formes différentes (champ « accroches ») : une question qui touche le spectateur \
(« Ton crédit va-t-il coûter plus cher ? »), un chiffre frappant de l'article, une conséquence concrète pour lui \
(« Ce changement touche ton porte-monnaie. »). 12 mots au plus, tutoiement, sans donner encore la réponse. Garde la plus \
forte : elle devient la première scène (type « accroche »), écran = dit = l'accroche.

2. Le déroulé, une idée par scène, entre 10 et 15 scènes :
- tout de suite une relance qui promet la suite (« Et voici ce que ça change pour toi. »)
- le mot clé expliqué comme à un ami (« Un crédit, c'est de l'argent que la banque te prête. »)
- le fait, avec les chiffres de l'article
- un cas concret : reprends l'exemple de l'article s'il y en a un, étape par étape ; sinon, montre ce que le fait change \
pour une personne ordinaire, sans ajouter de chiffre. Introduis-le simplement par « Prenons un exemple. »
- la leçon en une phrase, puis ce qu'il faut faire concrètement
Puis une question au spectateur (champ « question »), sur son avis ou son expérience ; elle sera ajoutée à la fin : ne \
parle pas de commentaire dans les scènes.

3. Les images. Trois sortes de scènes :
- « accroche » : la première, avec un « fond ».
- « media » : une photo ou une vidéo réaliste plein écran derrière le texte (champ « fond »), illustration null. Au moins \
trois par vidéo, pour les lieux, les institutions, les décors de la vie quotidienne.
- « explication » : un dessin animé DECIDE (champ « illustration »), fond null. Au moins trois par vidéo, pour les \
chiffres, les mécanismes, l'exemple ; dont au moins deux avec un personnage, et, dans les quatre premières scènes, une \
« carte » qui montre où ça se passe (le pays ou les villes d'Afrique nommés dans l'article).
Le « fond » :
- source « commons » : une vraie photo libre de Wikimedia Commons d'une chose que l'ARTICLE NOMME : une ville, un \
bâtiment, une université, une institution. « recherche » = son nom exact, tel qu'on le trouve sur Wikipédia \
(« Université de Yaoundé I », « Lomé », « Banque des États de l'Afrique centrale »). « logo » = true pour le logo officiel \
d'une institution ou d'une entreprise nommée (« recherche » = son sigle ou son nom : « BEAC », « Banque africaine de \
développement »). « secours » = 2 à 4 mots EN ANGLAIS pour un décor générique si la photo n'existe pas, sinon null.
- source « pixabay » : un décor générique, « recherche » = 2 à 4 mots EN ANGLAIS (« african market », « road construction \
africa », « bank counter », « students campus africa »). Il illustre le cadre, jamais l'événement : ne présente jamais \
des personnes filmées comme les gens dont parle l'article. « logo » = false, « secours » = null.
- Ne cherche jamais de personnes nommées, de chaînes de télévision ou de médias.

Langue : français simple et correct, phrases courtes, tutoiement, mots de tous les jours. Pas de jargon ; un sigle utile \
(CEMAC, BEAC) est expliqué une fois. Pas de ton publicitaire, pas de tiret long (—).

Exactitude (impératif) :
- N'invente aucun fait. Chaque chiffre écrit doit figurer dans l'article, recopié à l'identique (« 10,99 % », \
« 90 000 FCFA »). Seul « 12 mois » peut s'écrire en chiffres si l'article dit « douze ».
- N'écris jamais qu'un exemple est « fictif » ou « inventé ».
- Ne nomme aucune personne qui n'est pas nommée dans l'article ; pas de prénom au personnage de l'exemple.
- Ne donne pas de conseil que l'article ne donne pas.

Format de chaque scène :
- « dit » : la voix, 100 caractères au plus (environ 5 secondes).
- « ecran » : le texte affiché en grand, 6 mots au plus (sauf l'accroche), avec le mot clé entre astérisques \
(« Le crédit *coûte* plus cher »). Les chiffres s'affichent en orange d'eux-mêmes.
- « etiquette » : 1 à 3 mots en majuscules (C'EST QUOI ?, LE FAIT, EXEMPLE, RÉSULTAT, LA LEÇON, À FAIRE…), vide pour \
l'accroche.
- « illustration » (scènes « explication » seulement, sinon null) : le dessin qui montre l'idée, choisi dans la liste ; \
il doit correspondre au sens de la scène. Remplis seulement les paramètres utiles, les autres à null. Personnages : \
commercante = une femme (commerçante, vendeuse, mère), artisan = un homme (artisan, ouvrier, agriculteur), salarie = un \
homme en veste (salarié, fonctionnaire, chef d'entreprise), etudiante = une jeune femme (étudiante, élève). Garde le même \
personnage pour toute l'histoire d'un exemple ; l'expression et le geste suivent le sens de la phrase.
« titre » : le titre affiché en haut pendant toute la vidéo, 45 caractères au plus.

Dessins disponibles :
""" + "\n".join(f"- {k} : {v}" for k, v in ILLUSTRATIONS.items() if k != "photo")


_LIEUX = json.loads((MOTION / "src" / "lieux.json").read_text(encoding="utf-8"))


def lieu_connu(nom: str) -> bool:
    """Même clé que Carte.tsx : sans accents, en minuscules, apostrophe droite."""
    import unicodedata
    cle = unicodedata.normalize("NFKD", nom.replace("’", "'")).encode("ascii", "ignore").decode().lower().strip()
    return cle in _LIEUX and cle != "_"


def _sans_etoiles(t: str) -> str:
    return (t or "").replace("*", "")


def controler_v3(script: dict, article: dict) -> list[str]:
    scenes = script.get("scenes") or []
    copie = {**script, "scenes": [{**sc, "ecran": _sans_etoiles(sc.get("ecran")) if sc.get("type") != "accroche" else "",
                                   "illustration": sc.get("illustration") if sc.get("type") == "explication" else None}
                                  for sc in scenes]}
    problemes = controler(copie, article)
    if not scenes or scenes[0].get("type") != "accroche":
        problemes.append("la première scène doit être l'accroche (type « accroche »)")
    else:
        acc = _sans_etoiles(scenes[0].get("ecran"))
        if len(acc.split()) > 13:
            problemes.append("accroche trop longue (12 mots au plus)")
        source = " ".join(str(article.get(k) or "") for k in ("title", "body", "post_text"))
        if _nombres(acc) - _nombres(source) - {str(n) for n in range(0, 13)}:
            problemes.append("l'accroche contient un chiffre absent de l'article")
    if len(script.get("accroches") or []) < 3:
        problemes.append("il faut trois accroches de formes différentes")
    for k, sc in enumerate(scenes):
        if sc.get("type") != "accroche" and len(_sans_etoiles(sc.get("ecran")).split()) > 8:
            problemes.append(f"scène {k + 1} : texte écran trop long (6 mots)")
        if sc.get("type") == "media" and not (sc.get("fond") or {}).get("recherche"):
            problemes.append(f"scène {k + 1} : scène « media » sans fond")
        if re.search(r"\bcommentaires?\b", sc.get("dit", "") + sc.get("ecran", ""), re.I):
            problemes.append(f"scène {k + 1} : ne parle pas de commentaire dans les scènes")
        il = sc.get("illustration") or {}
        if sc.get("type") == "explication" and il.get("type") == "carte":
            inconnus = [n.strip() for n in str(il.get("texte") or "").split("|") if n.strip() and not lieu_connu(n)]
            if inconnus or not str(il.get("texte") or "").strip():
                problemes.append(f"scène {k + 1} : carte avec des lieux inconnus ({', '.join(inconnus) or 'aucun lieu'}) : "
                                 "prends une ville ou un pays d'Afrique nommé dans l'article, sinon un autre dessin")
    cartes = [sc for sc in scenes if (sc.get("illustration") or {}).get("type") == "carte" and sc.get("type") == "explication"]
    if not cartes and lieu_connu(str(article.get("country") or "").split("/")[-1]):
        problemes.append(f"montre où ça se passe : une scène « explication » avec le dessin « carte » "
                         f"(texte = « {str(article.get('country')).split('/')[-1].strip()} » ou une ville nommée dans l'article), "
                         "parmi les quatre premières scènes")
    # l'accroche a aussi un fond réaliste : elle compte (28/10, 4 replis V2 sur 10, surtout pour 2 scènes « media » au lieu de 3)
    if sum(sc.get("type") in ("accroche", "media") for sc in scenes) < 3:
        problemes.append("au moins trois scènes « media » (fonds réalistes)")
    if sum(sc.get("type") == "explication" for sc in scenes) < 3:
        problemes.append("au moins trois scènes « explication » (dessins)")
    return problemes


def script_v3(article: dict, cfg: dict, journal=print, cache: Path | None = None) -> dict | None:
    fichier = cache / f"{article.get('id', 'article')}.json" if cache else None
    if fichier and fichier.exists():
        return json.loads(fichier.read_text(encoding="utf-8"))
    import agent.script_video as sv
    if not os.environ.get("GEMINI_API_KEY") or sv._IA_HORS_SERVICE:  # Gemini saturé plus tôt dans ce passage : pas d'attente
        return None
    systeme, schema = sv.SYSTEME, sv.SCHEMA
    sv.SYSTEME, sv.SCHEMA = SYSTEME, SCHEMA  # même appel Gemini (modèles de secours, pauses), autres consignes
    remarques: list[str] = []
    try:
        for essai in range(3):
            ecrit = _demander_gemini(article, cfg, remarques)
            remarques = controler_v3(ecrit, article)
            if not remarques:
                if fichier:
                    fichier.parent.mkdir(parents=True, exist_ok=True)
                    fichier.write_text(json.dumps(ecrit, ensure_ascii=False, indent=2), encoding="utf-8")
                return ecrit
            journal(f"    ↺ script V3 refusé ({essai + 1}/3) : " + " ; ".join(remarques)[:300])
    finally:
        sv.SYSTEME, sv.SCHEMA = systeme, schema
    return None


def _fond(fond: dict, dossier: Path, nom: str, pris: set[str], journal) -> dict | None:
    from . import medias_commons, medias_libres
    if fond.get("source") == "commons":
        trouve = medias_commons.chercher(fond["recherche"], dossier, nom, pris, logo=bool(fond.get("logo")))
        if trouve:
            journal(f"      🖼 Commons « {fond['recherche']} » : {trouve[1]}")
            return {"src": f"_v3/{trouve[0].name}", "video": False, "credit": ("Logo : " if fond.get("logo") else "Photo : ") + trouve[1],
                    "logo": bool(fond.get("logo"))}
        journal(f"      · Commons « {fond['recherche']} » : rien de libre et de pertinent")
        requete = fond.get("secours")
    else:
        requete = fond.get("recherche")
    if requete and medias_libres.disponible():
        trouve = medias_libres.chercher(requete, dossier, nom, pris, pertinent=True)
        if trouve:
            journal(f"      🎞 Pixabay « {requete} » ({'vidéo' if trouve[1] else 'photo'})")
            return {"src": f"_v3/{trouve[0].name}", "video": trouve[1], "credit": ("Vidéo" if trouve[1] else "Photo") + " d'illustration : Pixabay"}
    return None


def rendre_production(article: dict, image: Path, sortie: Path, journal=print, essai: bool = False) -> Path:
    """Short V3 ; si Gemini ne fournit pas de script V3 utilisable, le Short sort au gabarit V2 (la publication continue).
    Le script est gardé dans etat/scripts_v3/<id>.json : même vidéo pour tous les réseaux et tous les passages."""
    from .config import charger_config
    from .gabarit_v2 import rendre_v2
    ecrit = None
    try:
        ecrit = script_v3(article, charger_config(MOTION.parent / "config.yaml"), journal, cache=SCRIPTS_V3)
    except Exception as e:  # l'IA ne bloque jamais la publication
        journal(f"⚠️ Script V3 indisponible ({type(e).__name__} : {str(e)[:200]})")
    if not ecrit:
        journal("    ↪ Short au gabarit V2")
        return rendre_v2(article, image, sortie, journal, essai=essai)
    return rendre_v3(article, image, sortie, journal, ecrit=ecrit, essai=essai)


def rendre_v3(article: dict, image: Path, sortie: Path, journal=print, ecrit: dict | None = None, essai: bool = False) -> Path:
    dossier = MOTION / "public" / "_v3"
    shutil.rmtree(dossier, ignore_errors=True)
    dossier.mkdir(parents=True)
    nom_image = f"visuel{image.suffix.lower()}"
    shutil.copy(image, dossier / nom_image)
    scenes, dits, pris = [], [], set()
    for k, sc in enumerate(ecrit["scenes"]):
        s = {"type": sc["type"], "etiquette": sc.get("etiquette") or None, "ecran": _insecables(sc.get("ecran") or "") or None,
             "soustitre": _insecables(sc["dit"])}
        if sc["type"] == "explication":
            s["illustration"] = {c: v for c, v in (sc.get("illustration") or {}).items() if v is not None} or {"type": "photo"}
        elif sc.get("fond"):
            media = _fond(sc["fond"], dossier, f"fond{k}", pris, journal)
            if media:
                s["media"] = media
            elif sc["type"] == "media":  # pas d'image libre : la scène devient une explication sur le visuel du lot
                s.update(type="explication", illustration={"type": "photo"})
        scenes.append(s)
        dits.append({"cle": f"s{k}", "texte": sc["dit"]})
    q = ecrit["question"].strip()
    scenes += [{"type": "question", "ecran": q, "soustitre": q}, {"type": "outro", "duree": 3.5}]
    dits += [{"cle": f"s{len(scenes) - 2}", "texte": f"{q} Dis-le en commentaire."}, {"cle": f"s{len(scenes) - 1}", "texte": "Décide média. Abonne-toi."}]
    try:
        pistes = {p["cle"]: p for p in Voix(journal).narration(dits, dossier, "voix", forcer=essai) or []}
    except Exception as e:  # la voix ne bloque jamais la vidéo
        journal(f"⚠️ Voix off indisponible, Short sans voix : {e}")
        pistes = {}
    for k, sc in enumerate(scenes):
        if f"s{k}" in pistes:
            sc["voix"] = {"src": pistes[f"s{k}"]["src"], "duree": pistes[f"s{k}"]["duree"]}
            sc.pop("duree", None)
        elif "duree" not in sc:
            sc["duree"] = max(2.5, len(sc.get("soustitre") or "") / 15)
    editeurs = list(dict.fromkeys((s or {}).get("publisher") for s in article.get("sources") or [] if (s or {}).get("publisher")))
    props = {"rubrique": RUBRIQUES.get(article.get("editorial_type") or article.get("content_type"), "ACTUALITÉ"),
             "lieu": article.get("country"), "date": _date_fr(article.get("event_date")), "titre": ecrit.get("titre") or article.get("title", ""),
             "image": f"_v3/{nom_image}", "source": ("Source : " + ", ".join(editeurs[:3])) if editeurs else None,
             "scenes": scenes, "musique": "melodie.wav", "volume_musique": 0.10}
    try:
        with tempfile.TemporaryDirectory() as d:
            fichier = Path(d) / "props.json"
            fichier.write_text(json.dumps(props, ensure_ascii=False), encoding="utf-8")
            r = subprocess.run(["npx.cmd" if shutil.which("npx.cmd") else "npx", "remotion", "render", "src/index.ts", "DecideShortV3",
                                str(sortie.resolve()), f"--props={fichier}", "--codec=h264", "--crf=22", "--log=warn"],
                               cwd=MOTION, capture_output=True, text=True, timeout=2400)
    finally:
        shutil.rmtree(dossier, ignore_errors=True)
    if r.returncode != 0 or not sortie.exists():
        raise RuntimeError(f"rendu Remotion impossible (code {r.returncode}) : {(r.stderr + r.stdout)[-1500:]}")
    return sortie
