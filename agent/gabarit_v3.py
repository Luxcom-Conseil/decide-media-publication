"""Gabarit V3 des Shorts (composition Remotion DecideShortV3), en production depuis le 27/10/2026 (config video.gabarit).

Mode information depuis le 02/11/2026 (demande de Stéphane) : un hook qui donne le fait, puis les faits, lus d'un seul
tenant comme un flash, en 30 secondes environ. Plus de parties, d'étiquettes, d'exemple, de leçon, de conseil, de
personnages ni de question finale. Images : banque_photos pour ce que l'article nomme (ville, bâtiment, institution), logo
officiel sur Wikimedia Commons, crédit affiché, sinon le visuel du lot. Plus de Pixabay : à l'essai du 02/11, « permis
moto » a donné un moteur de bateau, et la règle est aucune image hors contexte.
Le script est écrit par Gemini (gratuit) et contrôlé par controler_v3. Refusé ou indisponible : script_secours lit les
phrases de l'article, sans IA.
"""
from __future__ import annotations

import copy
import json
import os
import re
import shutil
import subprocess
import tempfile
from datetime import date
from pathlib import Path

from .gabarit_v2 import _insecables
from .scenario import MOTION, _date_fr
from .script_video import ILLUSTRATIONS, SCHEMA as SCHEMA_V2, _demander_gemini, _nombres, nombres_permis
from .voix import Voix

SCRIPTS_V3 = MOTION.parent / "etat" / "scripts_v3"
_TXT_NUL = {"anyOf":[{"type": "string"}, {"type": "null"}]}
DESSINS = ("photo", "carte", "pourcent", "pile", "frais", "calendrier")  # le visuel du lot, ou un fait : lieu, chiffre, somme, date
_ILLUSTRATION = copy.deepcopy(SCHEMA_V2["properties"]["scenes"]["items"]["properties"]["illustration"])
_ILLUSTRATION["anyOf"][1]["properties"]["type"]["enum"] = list(DESSINS)
VOIX_MAX = 560  # caractères
# Un Short dure 30 s au moins (demande du 12/11/2026 : « une information a besoin de respirer »). Les lots du 11 et du
# 12/11 lisaient 270 à 486 caractères pour des vidéos de 18 à 29 s : le script vise donc 450 caractères au moins, et
# etirer() garde l'image un peu plus longtemps après chaque phrase si la voix reste courte.
VOIX_MIN = 450
DUREE_MIN = 30.0  # secondes, générique compris
TENUE_MAX = 1.5   # secondes d'image ajoutées au plus après une phrase
PHRASE_MAX = 110
INTERDIT = re.compile(r"\b(prenons un exemple|voici|voilà|ce que ça change|la leçon|il faut|en clair|autrement dit|"
                      r"(cela|ça) (signifie|veut dire)|attention|pourquoi|imagine|à retenir|concrètement)\b", re.I)
ADRESSE = re.compile(r"\b(tu|te|ton|ta|tes|toi|vous|vos|votre)\b", re.I)
# phrases de méthode, et phrases qui ne se comprennent pas seules (lecture sans IA)
HORS_FAIT = re.compile(r"cet article|n'a pas été vérifi|^(ils?|elles?|ce|cela|ces|cette|et|mais)\b", re.I)
MOTS_BANNIS = re.compile(r"\b(assur(?!anc)\w*|transform(?!ation|ateur)\w*|parcours)\b", re.I)

SCHEMA = {
    "type": "object",
    "properties": {
        "accroches": {"type": "array", "items": {"type": "string"}},
        "titre": {"type": "string"},
        "scenes": {"type": "array", "items": {
            "type": "object",
            "properties": {
                "type": {"type": "string", "enum": ["accroche", "media", "explication"]},
                "illustration": _ILLUSTRATION,
                "fond": {"anyOf": [{"type": "null"}, {
                    "type": "object",
                    "properties": {"source": {"type": "string", "enum": ["commons"]}, "recherche": {"type": "string"},
                                   "logo": {"type": "boolean"}, "secours": _TXT_NUL},
                    "required": ["source", "recherche", "logo", "secours"], "additionalProperties": False}]},
                "ecran": {"type": "string"},
                "dit": {"type": "string"},
            },
            "required": ["type", "illustration", "fond", "ecran", "dit"],
            "additionalProperties": False,
        }},
    },
    "required": ["accroches", "titre", "scenes"],
    "additionalProperties": False,
}

SYSTEME = f"""Tu écris le script d'un flash d'information en vidéo verticale (Short) de DECIDE média. La voix lit l'information \
comme au journal, d'un seul tenant, sans parties ni rubriques. Les gens regardent en faisant défiler : la première phrase \
doit les arrêter, et elle doit déjà donner l'information : les 3 premières secondes portent l'information la plus forte.

1. LE HOOK. Écris trois accroches (champ « accroches ») : le chiffre le plus fort de l'article, l'information clé, le fait \
le plus inattendu. Chacune énonce le fait, en phrase affirmative de 12 mots au plus : \
« 7 ménages sur 10 n'ont pas de compteur. » Pas de question, pas de promesse de la suite, pas de chiffre sans intérêt \
(« 1 budget rejeté »). Le plus fort est ce qui touche le porte-monnaie ou la vie du spectateur : quand l'article donne \
une somme par personne, par ménage ou par mois, c'est elle (« 275 000 FCFA par jeune »). Garde la plus forte : elle \
devient la première scène (type « accroche »), écran = dit = l'accroche.

2. LES FAITS. Entre 4 et 6 scènes de plus, une phrase par scène, du plus important au moins important : qui, quoi, combien, \
où, quand, ce qui est prévu ensuite. Chaque phrase apporte un fait nouveau et suit la précédente comme dans une dépêche. \
La dernière scène donne un détail concret de l'article : une date, un lieu, une démarche, un délai, un montant par \
personne. Si l'article n'en donne aucun, le dernier fait le plus utile. La vidéo s'arrête là : pas de conclusion.

Donne juste l'information. Sont interdits : analyse, avis, explication de mot, exemple, personnage, conséquence supposée, \
leçon, conseil, question, annonce de la suite (« voici », « voilà »), appel au spectateur. Ne t'adresse jamais au spectateur : \
ni « tu » ni « vous ».

3. Les images. Aucune image hors contexte : une image montre ce que l'article nomme, sinon le visuel de l'article.
- « accroche » : la première scène, avec un « fond », ou fond null si l'article ne nomme aucun lieu ni institution.
- « media » : une vraie photo vérifiée (champ « fond »), illustration null, seulement pour une chose que l'ARTICLE NOMME : une ville, un bâtiment, une université, une institution. « source » = « commons ». « recherche » = son nom exact (« Université de Yaoundé I », « Douala », « port de Douala »), jamais une région ou un secteur administratif. « logo » = true pour le logo officiel d'une institution ou d'une entreprise nommée (« recherche » = son sigle ou son nom). « secours » = null. Une même recherche une seule fois par vidéo. Jamais de personnes nommées, de chaînes de télévision ou de médias.
- « explication » : toutes les autres scènes, fond null, avec le dessin qui montre le fait (champ « illustration ») ; aucun dessin ne convient : « photo », le visuel de l'article. Le chiffre d'un dessin est celui de la phrase lue dans la même scène. « pourcent » seulement pour une évolution dont l'article donne l'avant et l'après, jamais pour une part d'un total.

Langue : français simple et correct, phrases courtes, mots de tous les jours, écrites pour être lues à voix haute. Un fait \
ancien au passé, avec sa date. Pas de ton publicitaire, pas de tiret long (—). N'emploie jamais « assurer », « transformer », \
« parcours ».

Exactitude (impératif) :
- N'ajoute aucun fait et ne durcis aucune phrase de l'article. Ce que l'article attribue à quelqu'un reste attribué \
(« selon Ecomatin »), une fois. Ce que l'article dit inconnu ou incertain n'est pas écrit comme un fait.
- Chaque chiffre écrit doit figurer dans l'article, recopié à l'identique (« 10,99 % », « 90 000 FCFA »).
- Ne nomme aucune personne qui n'est pas nommée dans l'article.

Format de chaque scène :
- « dit » : la voix, {PHRASE_MAX} caractères au plus ; le total des « dit » fait entre {VOIX_MIN} et {VOIX_MAX} caractères (30 à 35 secondes) : une information \
complète, lue sans se presser.
- « ecran » : le texte affiché en grand, 6 mots au plus (sauf l'accroche), avec le mot clé entre astérisques \
(« Le crédit *coûte* plus cher »). Les chiffres s'affichent en orange d'eux-mêmes.
- « illustration » (scènes « explication » seulement, sinon null) : remplis seulement les paramètres utiles, les autres à null.
« titre » : le titre affiché en haut pendant toute la vidéo, 45 caractères au plus.

Dessins disponibles :
""" + "\n".join(f"- {k} : {ILLUSTRATIONS[k]}" for k in DESSINS)


_LIEUX = json.loads((MOTION / "src" / "lieux.json").read_text(encoding="utf-8"))


def lieu_connu(nom: str) -> bool:
    """Même clé que Carte.tsx : sans accents, en minuscules, apostrophe droite."""
    import unicodedata
    cle = unicodedata.normalize("NFKD", nom.replace("’", "'")).encode("ascii", "ignore").decode().lower().strip()
    return cle in _LIEUX and cle != "_"


def _sans_etoiles(t: str) -> str:
    return (t or "").replace("*", "")


def _reparer(script: dict) -> dict:
    """Une carte sur des lieux absents du fond de carte (un quartier, par exemple) passe sur le visuel du lot : à l'essai
    du 02/11, ce seul défaut a fait refuser trois scripts de suite. Un dessin dont le chiffre n'est pas dans la phrase lue
    y passe aussi : à l'essai du 03/11, des barres en hausse sur une part de 44 % et une pile de 2,27 milliards sur
    « 492 dossiers » disaient autre chose que la voix."""
    for sc in script.get("scenes") or []:
        il = sc.get("illustration") or {}
        lu = _nombres(f"{_sans_etoiles(sc.get('ecran'))} {sc.get('dit', '')}")
        if il.get("type") == "carte" and not all(lieu_connu(n) for n in str(il.get("texte") or "").split("|")):
            sc["illustration"] = {"type": "photo"}
        elif il.get("type") == "pourcent" and not (il.get("sens") and il.get("avant") and il.get("apres")
                                                   and _nombres(f"{il['avant']} {il['apres']}") <= lu):
            sc["illustration"] = {"type": "photo"}
        elif il.get("type") in ("pile", "frais") and not (il.get("montant") and _nombres(str(il["montant"])) & lu):
            sc["illustration"] = {"type": "photo"}
    return script


def question_du_public(article: dict) -> str | None:
    """La question à laquelle répond l'article (protocole 2.2), sinon None."""
    if article.get("editorial_type") != "reponse":
        return None
    return str((article.get("reponse") or {}).get("question") or "").strip() or None


def consignes_reponse(article: dict) -> str:
    """Une réponse ouvre sur la question du public, telle quelle, puis donne la réponse tout de suite (12/11/2026)."""
    q = question_du_public(article)
    if not q:
        return ""
    appui = (article.get("reponse") or {}).get("reponse") or ""
    return (f"\n\nCETTE VIDÉO RÉPOND À UNE QUESTION DU PUBLIC : « {q} ». Ici seulement, la première scène (type « accroche ») "
            f"est cette question, mot pour mot : « ecran » = « dit » = la question, avec son point d'interrogation. Les "
            f"accroches du champ « accroches » sont trois fois cette question. La deuxième scène donne la réponse tout de "
            f"suite, en reprenant cette phrase de l'article : « {appui} ». Puis les faits qui l'appuient. Les autres règles "
            f"restent : aucune autre question, pas de « tu » ni de « vous » hors de la question.")


def controler_v3(script: dict, article: dict) -> list[str]:
    scenes = script.get("scenes") or []
    question = question_du_public(article)
    source = " ".join(str(article.get(k) or "") for k in ("title", "body", "post_text")) + " " + (question or "")
    problemes = []
    if question and scenes and _sans_etoiles(scenes[0].get("dit")).strip() != question:
        problemes.append(f"la première scène doit être la question du public, mot pour mot : « {question} »")
    if not 4 <= len(scenes) <= 7:
        problemes.append(f"{len(scenes)} scènes (4 à 7 attendues : le hook, puis 3 à 6 faits)")
    if not scenes or scenes[0].get("type") != "accroche":
        problemes.append("la première scène doit être le hook (type « accroche »)")
    elif not question and len(_sans_etoiles(scenes[0].get("ecran")).split()) > 13:
        problemes.append("hook trop long (12 mots au plus)")
    if len(script.get("accroches") or []) < 3:
        problemes.append("il faut trois accroches de formes différentes")
    voix = sum(len(sc.get("dit", "")) for sc in scenes)
    if voix > VOIX_MAX + 50:  # tolérance : 565 caractères ne valent pas un refus
        problemes.append(f"voix trop longue ({voix} caractères, {VOIX_MAX} au plus)")
    # trop court : refusé seulement si l'article a de quoi dire plus ; sinon etirer() tient les 30 s
    if voix < VOIX_MIN - 50 and len(article.get("body") or "") >= 2 * VOIX_MIN:
        problemes.append(f"voix trop courte ({voix} caractères, {VOIX_MIN} au moins) : ajoute un fait de l'article, "
                         "par exemple une date, un lieu, une démarche ou un montant par personne")
    textes = [script.get("titre", "")]
    for k, sc in enumerate(scenes):
        if question and k == 0:  # la question du public : seule phrase permise avec « ? » ou « vous »
            continue
        ecran, dit = _sans_etoiles(sc.get("ecran")), sc.get("dit", "")
        il = (sc.get("illustration") or {}) if sc.get("type") == "explication" else {}
        textes += [ecran, dit] + [str(v) for c, v in il.items() if c != "type" and v]
        if len(dit) > PHRASE_MAX + 20:
            problemes.append(f"scène {k + 1} : voix trop longue ({len(dit)} caractères)")
        if sc.get("type") != "accroche" and len(ecran.split()) > 8:
            problemes.append(f"scène {k + 1} : texte écran trop long (6 mots)")
        if sc.get("type") == "media" and not (sc.get("fond") or {}).get("recherche"):
            problemes.append(f"scène {k + 1} : scène « media » sans fond")
        if sc.get("type") == "explication" and il.get("type") not in DESSINS:
            problemes.append(f"scène {k + 1} : dessin à choisir parmi {', '.join(DESSINS)}")
        if il.get("type") == "carte":
            inconnus = [n.strip() for n in str(il.get("texte") or "").split("|") if n.strip() and not lieu_connu(n)]
            if inconnus or not str(il.get("texte") or "").strip():
                problemes.append(f"scène {k + 1} : carte avec des lieux inconnus ({', '.join(inconnus) or 'aucun lieu'}) : "
                                 "prends une photo")
    tout = " ".join(textes)
    if "?" in tout:
        problemes.append("pas de question : énonce le fait")
    for motif, message in ((INTERDIT, "formule d'analyse ou d'annonce interdite"), (ADRESSE, "ne t'adresse pas au spectateur"),
                           (MOTS_BANNIS, "mot interdit")):
        trouve = motif.search(tout)
        if trouve:
            problemes.append(f"{message} : « {trouve.group(0)} »")
    inventes = sorted(_nombres(tout) - nombres_permis(source))
    if inventes:
        problemes.append("chiffres absents de l'article : " + ", ".join(inventes))
    return problemes


def script_secours(article: dict) -> dict | None:
    """Sans IA : les phrases de l'article, mot pour mot, sur le visuel du lot. None si aucune ne peut être lue."""
    phrases = [p.strip() for p in re.split(r"(?<=[.!])\s+", article.get("body") or "")]
    gardees: list[str] = []
    for p in phrases:
        lisible = 20 <= len(p) <= PHRASE_MAX + 20 and "?" not in p and not (INTERDIT.search(p) or ADRESSE.search(p) or HORS_FAIT.search(p))
        if lisible and len(gardees) < 5 and sum(map(len, gardees)) + len(p) <= VOIX_MAX:
            gardees.append(p)
    if not gardees:
        return None
    hook = (article.get("etiquette_chiffre") or {}).get("texte") or article.get("title", "")
    question = question_du_public(article)
    if question:  # une réponse : la question, puis les phrases de l'article
        scenes = [{"type": "accroche", "fond": None, "ecran": question, "dit": question}]
        scenes += [{"type": "explication", "illustration": {"type": "photo"}, "fond": None, "ecran": "", "dit": p}
                   for p in gardees[:4]]
        return {"titre": article.get("title", ""), "scenes": scenes}
    scenes = [{"type": "accroche", "fond": None, "ecran": hook, "dit": gardees[0]}]
    scenes += [{"type": "explication", "illustration": {"type": "photo"}, "fond": None, "ecran": "", "dit": p} for p in gardees[1:]]
    return {"titre": article.get("title", ""), "scenes": scenes}


def script_v3(article: dict, cfg: dict, journal=print, cache: Path | None = None) -> dict | None:
    fichier = cache / f"{article.get('id', 'article')}.json" if cache else None
    if fichier and fichier.exists():
        garde = json.loads(fichier.read_text(encoding="utf-8"))
        if "question" not in garde:  # un script de l'ancien modèle se réécrit
            return garde
    import agent.script_video as sv
    if not os.environ.get("GEMINI_API_KEY") or sv._IA_HORS_SERVICE:  # Gemini saturé plus tôt dans ce passage : pas d'attente
        return None
    systeme, schema = sv.SYSTEME, sv.SCHEMA
    # même appel Gemini (modèles de secours, pauses), autres consignes ; la date du jour pour ne pas écrire au présent un fait ancien
    sv.SYSTEME = SYSTEME + f"\n\nDate du jour : {date.today().isoformat()}. Un fait daté de plus de 7 jours s'écrit au passé, hook compris." + consignes_reponse(article)
    sv.SCHEMA = SCHEMA
    remarques: list[str] = []
    try:
        for essai in range(3):
            ecrit = _reparer(_demander_gemini(article, cfg, remarques))
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


def duree_scene(sc: dict) -> float:
    """Même calcul que longueur() dans GabaritV3.tsx (3 + 5 images autour de la voix)."""
    base = (sc["voix"]["duree"] + 8 / 30) if sc.get("voix") else float(sc.get("duree") or 3)
    return base + float(sc.get("tenue") or 0)


def etirer(scenes: list[dict], minimum: float = DUREE_MIN) -> float:
    """Porte le Short à `minimum` secondes : l'image reste un peu après chaque phrase (TENUE_MAX au plus), le reste va
    au générique. Rien ne change si la vidéo est déjà assez longue. Rend la durée finale."""
    manque = minimum - sum(map(duree_scene, scenes))
    faits = [sc for sc in scenes if sc.get("type") != "outro"]
    if manque > 0 and faits:
        tenue = round(min(TENUE_MAX, manque / len(faits)), 2)
        for sc in faits:
            sc["tenue"] = tenue
        manque -= tenue * len(faits)
    if manque > 0 and scenes:
        scenes[-1]["tenue"] = round(float(scenes[-1].get("tenue") or 0) + manque + 0.05, 2)
    return sum(map(duree_scene, scenes))


def _fond(fond: dict, dossier: Path, nom: str, pris: set[str], journal) -> dict | None:
    from . import medias_commons
    if fond.get("logo"):
        trouve = medias_commons.chercher(fond["recherche"], dossier, nom, pris, logo=True)
        credit = "Logo : " + trouve[1] if trouve else None
    else:
        trouve = medias_commons.dans_banque(fond["recherche"], dossier, nom, pris)
        credit = trouve[1] if trouve else None
    if trouve:
        journal(f"      🖼 « {fond['recherche']} » : {credit}")
        return {"src": f"_v3/{trouve[0].name}", "video": False, "credit": credit, "logo": bool(fond.get("logo"))}
    journal(f"      · « {fond['recherche']} » : rien de vérifié, visuel du lot")
    return None


# Thèmes de la banque où une photo illustre le sujet sans montrer un lieu ou un bâtiment précis : un pylône pour
# l'électricité, un étal pour les prix. Hors liste (institutions, ville_habitat, port_aeroport, education, sante) : la
# photo d'un bâtiment ou d'une ville nommés ferait croire qu'il s'agit de celui de l'article.
THEMES_GENERIQUES = {"electricite", "solaire", "carburant", "marche", "transport", "agriculture", "elevage", "eau",
                     "travail", "bois_foret", "peche"}
PHOTOS_PAR_SHORT = 4
COUVERTURE_MS = 500  # instant de la couverture : texte du hook complet, secousse finie (Buffer → TikTok : thumbnailOffset)


def photos_du_sujet(article: dict, dossier: Path, pris: set[str], recentes: dict | None = None) -> list[dict]:
    """La photo vérifiée de l'article (banque_photos), puis jusqu'à 3 autres du même thème générique, sans visage
    reconnaissable ni marque, et pas déjà sorties ces 7 derniers jours. Liste vide si la photo de l'article n'est pas
    dans la banque : pas d'image devinée."""
    from .lots import cle_photo
    from .medias_commons import BANQUE
    page = cle_photo((article.get("image_provenance") or {}).get("page"))
    if not page:
        return []
    index = json.loads((BANQUE / "index.json").read_text(encoding="utf-8"))
    sienne = next((e for e in index if cle_photo(e.get("page")) == page), None)
    if not sienne:
        return []
    if recentes is None:
        f = MOTION.parent / "etat" / "photos_utilisees.json"
        recentes = json.loads(f.read_text(encoding="utf-8")) if f.exists() else {}
    jour = str(article.get("_lot") or date.today().isoformat())

    def recente(e):
        vu = recentes.get(cle_photo(e.get("page")))
        try:
            return vu is not None and 0 <= (date.fromisoformat(jour) - date.fromisoformat(vu)).days <= 7
        except ValueError:
            return False

    choisies = [sienne]
    if sienne["theme"] in THEMES_GENERIQUES:
        choisies += [e for e in index if e is not sienne and e["theme"] == sienne["theme"] and e["fichier"] not in pris
                     and e["personnes"] in ("aucune", "loin") and not e["marque"] and not recente(e)
                     and "panneau de" not in e["montre"]][:PHOTOS_PAR_SHORT - 1]
    sortie = []
    for k, e in enumerate(choisies):
        cible = dossier / f"theme{k}.jpg"
        shutil.copy(BANQUE / e["fichier"], cible)
        pris.add(e["fichier"])
        sortie.append({"src": f"_v3/{cible.name}", "video": False, "credit": e["credit"]})
    return sortie


def rendre_production(article: dict, image: Path, sortie: Path, journal=print, essai: bool = False) -> Path:
    """Short V3 ; si Gemini ne fournit pas de script utilisable, les phrases de l'article sont lues telles quelles (la
    publication continue). Le script est gardé dans etat/scripts_v3/<id>.json : même vidéo pour tous les réseaux et tous
    les passages."""
    from .config import charger_config
    from .gabarit_v2 import rendre_v2
    ecrit = None
    try:
        ecrit = script_v3(article, charger_config(MOTION.parent / "config.yaml"), journal, cache=SCRIPTS_V3)
    except Exception as e:  # l'IA ne bloque jamais la publication
        journal(f"⚠️ Script V3 indisponible ({type(e).__name__} : {str(e)[:200]})")
    if not ecrit:
        ecrit = script_secours(article)
        journal("    ↪ Script lu dans l'article, sans IA")
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
        s = {"type": sc["type"], "ecran": _insecables(sc.get("ecran") or "") or None, "soustitre": _insecables(sc["dit"])}
        if sc["type"] == "explication":
            s["illustration"] = {c: v for c, v in (sc.get("illustration") or {}).items() if v is not None} or {"type": "photo"}
        elif sc.get("fond"):
            media = _fond(sc["fond"], dossier, f"fond{k}", pris, journal)
            if media:
                s["media"] = media
            elif sc["type"] == "media":  # pas d'image libre : la scène passe sur le visuel du lot
                s.update(type="explication", illustration={"type": "photo"})
        scenes.append(s)
        dits.append({"cle": f"s{k}", "texte": sc["dit"]})
    # plus d'images (demande du 05/11) : la photo de l'article et celles de son thème, à tour de rôle ; une scène
    # « photo » (le visuel du lot en carte) passe en plein écran, un dessin garde son fond photo très assombri
    photos = photos_du_sujet(article, dossier, pris)
    tour = 0
    for s in scenes:
        if not photos or s.get("media"):
            continue
        photo = dict(photos[tour % len(photos)])
        tour += 1
        if s["type"] == "accroche":
            s["media"] = photo
        elif s["type"] == "explication" and (s.get("illustration") or {}).get("type") == "photo":
            s.pop("illustration")
            s.update(type="media", media=photo)
        elif s["type"] == "explication":
            s["media"] = {**photo, "voile": True}
    if photos:
        journal(f"      🖼 {len(photos)} photo(s) du thème, {tour} scène(s) illustrée(s)")
    scenes.append({"type": "outro", "duree": 3.5})
    dits.append({"cle": f"s{len(scenes) - 1}", "texte": "Décide média. Abonne-toi."})
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
    avant = sum(map(duree_scene, scenes))
    if avant < DUREE_MIN:
        journal(f"      ⏱ {avant:.1f} s → {etirer(scenes):.1f} s (30 s au moins)")
    editeurs = list(dict.fromkeys((s or {}).get("publisher") for s in article.get("sources") or [] if (s or {}).get("publisher")))
    props = {"rubrique": "VOUS AVEZ DEMANDÉ" if question_du_public(article) else "INFO",
             "lieu": article.get("country"), "date": _date_fr(article.get("event_date")), "titre": ecrit.get("titre") or article.get("title", ""),
             "image": f"_v3/{nom_image}", "source": ("Source : " + ", ".join(editeurs[:3])) if editeurs else None,
             "scenes": scenes, "musique": "melodie.wav", "volume_musique": 0.10}
    from . import sons
    from .config import charger_config
    cfg = charger_config(MOTION.parent / "config.yaml")
    try:  # charte sonore « flash info » : un son manquant n'empêche jamais le Short
        props.update(sons.habiller(cfg, "video", scenes, cle=str(article.get("id") or props["titre"]), journal=journal,
                                   duree_scene=duree_scene))
        props.pop("credit_musique", None)
    except Exception as e:
        journal(f"    ⚠️ charte sonore non appliquée : {e}")
    try:
        with tempfile.TemporaryDirectory() as d:
            fichier = Path(d) / "props.json"
            fichier.write_text(json.dumps(props, ensure_ascii=False), encoding="utf-8")
            npx = "npx.cmd" if shutil.which("npx.cmd") else "npx"
            r = subprocess.run([npx, "remotion", "render", "src/index.ts", "DecideShortV3",
                                str(sortie.resolve()), f"--props={fichier}", "--codec=h264", "--crf=22", "--log=warn"],
                               cwd=MOTION, capture_output=True, text=True, timeout=2400)
            if r.returncode == 0:
                # couverture JPEG (YouTube) : l'image de la vidéo à COUVERTURE_MS, la même que TikTok affiche
                c = subprocess.run([npx, "remotion", "still", "src/index.ts", "DecideShortV3", str(couverture(sortie).resolve()),
                                    f"--props={fichier}", f"--frame={COUVERTURE_MS * 30 // 1000}", "--image-format=jpeg",
                                    "--jpeg-quality=90", "--log=warn"], cwd=MOTION, capture_output=True, text=True, timeout=600)
                if c.returncode != 0:
                    journal(f"⚠️ couverture non fabriquée : {(c.stderr + c.stdout)[-300:]}")
    finally:
        shutil.rmtree(dossier, ignore_errors=True)
    if r.returncode != 0 or not sortie.exists():
        raise RuntimeError(f"rendu Remotion impossible (code {r.returncode}) : {(r.stderr + r.stdout)[-1500:]}")
    sons.niveler(cfg, "video", sortie, journal)
    return sortie


def couverture(short: Path) -> Path:
    """Couverture JPEG d'un Short V3, à côté du MP4 (absente si le rendu de l'image fixe a échoué)."""
    return short.with_name(short.stem + "_couverture.jpg")
