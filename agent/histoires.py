"""Compte « Histoires vraies d'argent » (TikTok + YouTube, public France) : vidéos d'essai, rien n'est publié.

Projet du 06/11/2026 (C:/Users/nzess/Projets/argent-travail/founder/projet.md). Une affaire d'argent réelle par vidéo :
- source unique = l'article Wikipédia en français (texte lu en direct par l'API, licence CC BY-SA, crédité) ;
- images = celles des articles français et anglais qui sont sur Wikimedia Commons sous licence libre, avec leur crédit ;
- Gemini (offre gratuite) écrit le récit ; contrôle : aucun chiffre absent de l'article ;
- voix Schedar (Gemini) en conteur, relais sur la voix Chirp ; montage Remotion (composition RecitReel).
Deux formats : « serie » (partie 1, de 75 à 110 s, finit sur un suspense) et « chiffre » (25 à 40 s, un fait et sa leçon).
"""
from __future__ import annotations

import json
import os
import re
import shutil
import time
from pathlib import Path

import requests

from .medias_commons import LICENCES, MIMES, _texte, credit
from .perso import MOTION, RACINE, _nombres, _remotion

ENTETES = {"User-Agent": "HistoiresVraiesArgent/0.1 (https://github.com/Luxcom-Conseil/decide-media-publication)"}
COMMONS = "https://commons.wikimedia.org/w/api.php"
NOM_SERIE = "Histoires vraies d'argent"
COMPTE = "@histoires.vraies.argents"  # identifiant réel, le même sur TikTok et YouTube (06/11/2026)

# Les 9 essais du 06/11/2026 : 6 parties 1 de série, 3 « chiffre fou » ; 3 formules d'accroche en alternance.
SUJETS = [
    {"id": "humbert", "article": "Thérèse Humbert", "en": "Thérèse Humbert", "format": "serie", "formule": "Énigme"},
    {"id": "lustig", "article": "Victor Lustig", "en": "Victor Lustig", "format": "serie", "formule": "Chiffre"},
    {"id": "law", "article": "Système de Law", "en": "Mississippi Company", "format": "serie", "formule": "Contre-pied"},
    {"id": "stavisky", "article": "Affaire Stavisky", "en": "Stavisky affair", "format": "serie", "formule": "Chiffre"},
    {"id": "spaggiari", "article": "Albert Spaggiari", "en": "Albert Spaggiari", "format": "serie", "formule": "Énigme"},
    {"id": "meegeren", "article": "Han van Meegeren", "en": "Han van Meegeren", "format": "serie", "formule": "Contre-pied"},
    {"id": "tulipes", "article": "Tulipomanie", "en": "Tulip mania", "format": "chiffre", "formule": "Chiffre"},
    {"id": "ponzi", "article": "Charles Ponzi", "en": "Charles Ponzi", "format": "chiffre", "formule": "Énigme"},
    {"id": "panama", "article": "Scandale de Panama", "en": "Panama scandals", "format": "chiffre", "formule": "Contre-pied"},
]
from .histoires_sujets import CATALOGUE  # noqa: E402

PAR_ID = {s["id"]: s for s in CATALOGUE}

FORMULES = {
    "Énigme": "une situation impossible, sans donner la réponse (« Le jour où l'on a ouvert son coffre-fort, Paris a découvert l'impensable. »)",
    "Chiffre": "un fait ou un chiffre réel de l'article qui choque (« Cet homme a vendu la tour Eiffel. Deux fois. »)",
    "Contre-pied": "ce que tout le monde croit, puis l'inverse (« Le faussaire qui a trompé les nazis a été sauvé par ses faux. »)",
}
FORMATS = {
    # (scènes min, max), (caractères dits min, max) : Schedar en conteur lit environ 15 caractères par seconde
    "serie": ((13, 24), (1150, 1700)),
    "serie2": ((12, 24), (1100, 1700)),
    "chiffre": ((6, 11), (380, 600)),
}
TYPES = ["accroche", "recit", "date", "chiffre", "suite", "lecon"]
_TXT = {"type": "string"}
_TXT_NUL = {"anyOf": [{"type": "string"}, {"type": "null"}]}

SCHEMA = {
    "type": "object",
    "properties": {
        "titre": _TXT,
        "scenes": {"type": "array", "items": {
            "type": "object",
            "properties": {"type": {"type": "string", "enum": TYPES}, "ecran": _TXT, "grand": _TXT_NUL, "dit": _TXT,
                           "image": {"type": "integer"}, "recherche": _TXT_NUL},
            "required": ["type", "ecran", "grand", "dit", "image", "recherche"], "additionalProperties": False}},
        "question": _TXT,
        "legende": _TXT,
        "hashtags": {"type": "array", "items": _TXT},
    },
    "required": ["titre", "scenes", "question", "legende", "hashtags"],
    "additionalProperties": False,
}

SYSTEME = """Tu écris le script d'une vidéo TikTok verticale pour le compte « Histoires vraies d'argent » : de grandes \
affaires d'argent réelles (arnaques, fortunes, faillites, casses), racontées comme un bon documentaire. Public : adultes \
de France, de Belgique et de Suisse, qui font défiler leur fil : tu as 2 secondes pour les arrêter, puis chaque scène \
doit relancer l'envie de voir la suivante (une révélation, un chiffre, une question, un retournement).

EXACTITUDE (impératif) :
- Ta seule source est l'article fourni. N'invente aucun fait, aucune date, aucun montant, aucun dialogue, aucune pensée.
- Les dates et montants sont ceux de l'article, dans sa monnaie (francs, livres, florins, dollars) ; ne convertis rien.
- Si l'article présente un fait comme incertain ou comme une légende, dis-le (« raconte-t-on », « selon la légende »).
- Ne nomme que le personnage principal et les personnages historiques que l'article nomme. Aucune autre personne privée.
- Reste neutre : on raconte, on n'accuse pas au-delà de ce que l'article établit (condamnations, aveux).

ACCROCHE (première scène, type « accroche ») : 12 mots au plus dans « ecran », qui suit la formule demandée. Elle pose \
l'énigme ou le choc sans donner la fin. « dit » = la même accroche, à l'oral, au plus 140 caractères.

Le reste :
- des scènes courtes, une idée chacune, dans l'ordre de l'histoire ;
- « date » : un moment clé ; « grand » = l'année ou la date courte (« 1902 », « 8 mai 1925 ») ; « ecran » = le lieu ou ce qui se passe (5 mots au plus) ;
- « chiffre » : un montant ou un nombre frappant de l'article ; « grand » = ce chiffre court (« 50 millions », « 7 000 ») ; « ecran » = ce qu'il mesure (5 mots au plus) ;
- « recit » : le reste ; « grand » = null ; « ecran » = 6 mots au plus, le mot clé entre astérisques (« Un *héritage* de 100 millions »).
Utilise au moins deux scènes « date » ou « chiffre ».

Ton : un conteur direct et captivant, français oral de France, phrases courtes, présent de narration. Tu peux \
interpeller le spectateur (« tu ») de temps en temps. Pas de tiret long (—), pas d'émoji.

Chaque scène : « dit » entre 50 et 140 caractères.
IMAGES : chaque scène doit être illustrée, c'est ce qui retient le regard. « image » = le numéro d'une image de la liste \
fournie qui montre ce dont parle la scène (le portrait du personnage, le lieu, un document) ; ne mets pas la même deux \
scènes de suite ; -1 si aucune ne convient VRAIMENT à cette scène. « recherche » : quand « image » vaut -1, 2 à 4 mots EN \
ANGLAIS pour trouver une photo ou gravure d'archive libre sur Wikimedia Commons : une chose réelle de l'histoire, nommée \
et visible (« Eiffel Tower 1920s », « Hotel de Crillon », « Al Capone », « ocean liner 1910s », « Banque de France », \
« Amsterdam 17th century »), jamais une idée abstraite ; sinon null. L'accroche a toujours une image ou une recherche.

« titre » : le nom de l'affaire, 40 caractères au plus.
« question » : une question courte qui fait réagir (« Tu aurais cru à son héritage ? »). Ne la mets pas dans les scènes.
« legende » : la légende TikTok, 2 à 4 lignes : l'accroche, puis une phrase qui donne envie, puis la question. Pas de \
hashtag ni de lien dans le texte, pas d'émoji.
« hashtags » : 3 à 5 hashtags en français, sans le #."""

CONSIGNES_FORMAT = {
    "serie": """FORMAT SÉRIE, PARTIE 1 SUR 2 : entre 14 et 22 scènes, de 1 200 à 1 600 caractères dits en tout. Raconte le \
début de l'histoire jusqu'au moment où tout bascule, puis ARRÊTE-TOI juste avant la révélation ou la chute. La dernière \
scène est de type « suite » : « ecran » = la question laissée en suspens (6 mots au plus), « dit » = cette question puis \
« La suite dans la partie 2. ». Ne révèle pas la fin.""",
    "chiffre": """FORMAT CHIFFRE FOU : entre 6 et 10 scènes, de 400 à 560 caractères dits en tout. Un seul fait frappant de \
l'article : l'accroche, le contexte en deux ou trois scènes, le chiffre (une scène « chiffre »), comment c'est arrivé, \
puis la dernière scène de type « lecon » : la leçon d'argent ou de psychologie que l'histoire enseigne, en une phrase \
(« ecran » = cette phrase, 90 caractères au plus ; « dit » = la même phrase).""",
    "serie2": """FORMAT SÉRIE, PARTIE 2 SUR 2 : entre 13 et 22 scènes, de 1 150 à 1 600 caractères dits en tout. La partie 1 \
(fournie entre les balises <partie1>) s'est arrêtée sur une question en suspens. La première scène (type « accroche ») \
relance en une phrase là où l'histoire s'était arrêtée (« ecran » de 12 mots au plus, par exemple « Le coffre-fort \
s'ouvre enfin. Il est vide. »). Raconte ensuite la suite et la fin, sans répéter la partie 1, jusqu'au dénouement \
(procès, chute, fuite, mort, ce qu'il reste de l'argent). La dernière scène est de type « lecon » : la leçon d'argent ou \
de psychologie que l'histoire enseigne, en une phrase (« ecran » = cette phrase, 90 caractères au plus ; « dit » = la même \
phrase).""",
}


# --------------------------------------------------------------------------- Wikipédia et Commons

def article(titre: str, langue: str = "fr") -> dict:
    """{"titre", "texte", "url", "images"} de l'article (texte brut, liste des fichiers image)."""
    r = requests.get(f"https://{langue}.wikipedia.org/w/api.php", headers=ENTETES, timeout=60, params={
        "action": "query", "format": "json", "titles": titre, "redirects": 1, "prop": "extracts|images|info",
        "explaintext": 1, "imlimit": 100, "inprop": "url"})
    r.raise_for_status()
    p = next(iter(r.json()["query"]["pages"].values()))
    if "missing" in p:
        raise RuntimeError(f"article Wikipédia introuvable : {titre} ({langue})")
    texte = re.split(r"\n== (Notes et références|Références|Voir aussi|Bibliographie|Liens externes|Notes|See also|References) ==",
                     p.get("extract", ""))[0]
    images = [i["title"] for i in p.get("images", []) if i["title"].lower().endswith((".jpg", ".jpeg", ".png", ".tif", ".tiff"))]
    return {"titre": p["title"], "texte": texte.strip(), "url": p.get("fullurl", ""), "images": images}


_DECOR = re.compile(r"logo|icon|icône|flag|drapeau|blason|coat.of.arms|signature|autograph|wiki|commons-|symbol|pictogram", re.I)


def images_libres(titres: list[str], dossier: Path, limite: int = 14, journal=print) -> list[dict]:
    """Télécharge les images libres de Commons parmi `titres` (« Fichier:… » ou « File:… ») : [{"src", "nom",
    "description", "credit"}]. Les fichiers propres à un Wikipédia (souvent non libres) ne sont pas sur Commons : écartés."""
    vus, noms = set(), []
    for t in titres:
        nom = "File:" + t.split(":", 1)[1]
        if nom not in vus and not _DECOR.search(nom):
            vus.add(nom)
            noms.append(nom)
    sortie: list[dict] = []
    for k in range(0, len(noms), 40):
        try:
            r = requests.get(COMMONS, headers=ENTETES, timeout=60, params={
                "action": "query", "format": "json", "titles": "|".join(noms[k:k + 40]), "prop": "imageinfo",
                "iiprop": "url|extmetadata|mime|size", "iiurlwidth": 1080})
            r.raise_for_status()
            pages = r.json()["query"]["pages"].values()
        except (requests.RequestException, ValueError, KeyError) as e:
            journal(f"    ⚠️ Commons : {type(e).__name__}")
            continue
        for p in pages:
            info = (p.get("imageinfo") or [{}])[0]
            meta = info.get("extmetadata") or {}
            licence = _texte(meta, "LicenseShortName")
            if ("missing" in p or info.get("mime") not in MIMES or _texte(meta, "NonFree").lower() == "true"
                    or not LICENCES.match(licence) or min(info.get("width", 0), info.get("height", 0)) < 400):
                continue
            fichier = dossier / f"img{len(sortie)}{MIMES[info['mime']]}"
            try:
                with requests.get(info.get("thumburl") or info["url"], headers=ENTETES, timeout=(15, 120)) as f:
                    f.raise_for_status()
                    fichier.write_bytes(f.content)
            except requests.RequestException:
                continue
            description = _texte(meta, "ImageDescription")[:160] or p["title"].removeprefix("File:")
            sortie.append({"src": f"{dossier.name}/{fichier.name}", "nom": p["title"], "description": description,
                           "credit": _credit(credit(_texte(meta, "Artist"), licence))})
            time.sleep(0.5)  # Commons limite les rafales (erreurs 429 vues le 02/11)
            if len(sortie) >= limite:
                return sortie
    return sortie


# --------------------------------------------------------------------------- script

def controler(script: dict, source: str, format_: str, nb_images: int) -> list[str]:
    """Problèmes qui interdisent d'utiliser le script (vide = bon)."""
    (smin, smax), (cmin, cmax) = FORMATS[format_]
    problemes = []
    scenes = script.get("scenes") or []
    if not smin <= len(scenes) <= smax:
        problemes.append(f"{len(scenes)} scènes ({smin} à {smax} attendues)")
    if not scenes or scenes[0].get("type") != "accroche":
        problemes.append("la première scène doit être l'accroche")
    elif len(re.sub(r"\*", "", scenes[0].get("ecran", "")).split()) > 13:
        problemes.append("accroche trop longue (12 mots au plus à l'écran)")
    fin = "suite" if format_ == "serie" else "lecon"
    if scenes and scenes[-1].get("type") != fin:
        problemes.append(f"la dernière scène doit être de type « {fin} »")
    parole = sum(len(sc.get("dit", "")) for sc in scenes) + len(script.get("question", ""))
    if not cmin <= parole <= cmax:
        problemes.append(f"{parole} caractères dits, il en faut de {cmin} à {cmax} (question comprise)")
    if sum(sc.get("type") in ("date", "chiffre") for sc in scenes) < (2 if format_ == "serie" else 1):
        problemes.append("pas assez de scènes « date » ou « chiffre »")
    textes = [script.get("titre", ""), script.get("question", ""), script.get("legende", "")]
    for k, sc in enumerate(scenes):
        textes += [sc.get("dit", ""), sc.get("ecran", ""), sc.get("grand") or ""]
        if len(sc.get("dit", "")) > 170:
            problemes.append(f"scène {k + 1} : voix trop longue ({len(sc['dit'])} caractères)")
        limite = {"accroche": 90, "lecon": 100, "suite": 60}.get(sc.get("type"), 50)
        if len(sc.get("ecran", "")) > limite:
            problemes.append(f"scène {k + 1} : texte écran trop long ({len(sc['ecran'])} caractères)")
        if sc.get("type") in ("date", "chiffre") and not (sc.get("grand") or "").strip():
            problemes.append(f"scène {k + 1} : « grand » vide pour une scène « {sc.get('type')} »")
        if not -1 <= int(sc.get("image", -1)) < nb_images:
            problemes.append(f"scène {k + 1} : image {sc.get('image')} hors de la liste (0 à {nb_images - 1}, ou -1)")
        elif int(sc.get("image", -1)) == -1 and not (sc.get("recherche") or "").strip() and sc.get("type") != "suite":
            problemes.append(f"scène {k + 1} : ni image ni « recherche » (chaque scène doit être illustrée)")
    tout = " ".join(textes)
    inventes = sorted(_nombres(tout) - _nombres(source) - {str(n) for n in range(0, 11)})
    if inventes:
        problemes.append("chiffres absents de l'article : " + ", ".join(inventes))
    if "—" in tout:
        problemes.append("tiret long interdit")
    return problemes


def _demander(cfg: dict, parties: list[dict], remarques: list[str]) -> dict:
    modeles = (cfg.get("video") or {}).get("modeles_gemini") or ["gemini-3.5-flash", "gemini-flash-latest"]
    consigne = "Écris le script de la vidéo."
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


def ecrire_script(cfg: dict, sujet: dict, source: dict, images: list[dict], journal=print,
                  format_: str | None = None, partie1: dict | None = None) -> dict:
    """`format_` = "serie2" avec `partie1` (le script de la partie 1) pour écrire la suite et la fin d'une série."""
    if not os.environ.get("GEMINI_API_KEY"):
        raise RuntimeError("clé GEMINI_API_KEY absente")
    format_ = format_ or sujet["format"]
    liste = "\n".join(f"[{k}] {im['description']}" for k, im in enumerate(images)) or "(aucune image)"
    parties = [{"text": f"<article titre=\"{source['titre']}\">\n{source['texte'][:16000]}\n</article>"},
               {"text": f"<images>\n{liste}\n</images>"}]
    if partie1:
        recit = "\n".join(sc.get("dit", "") for sc in partie1.get("scenes", []))
        parties.append({"text": f"<partie1>\n{recit}\n</partie1>"})
    else:
        parties.append({"text": f"L'accroche suit la formule « {sujet['formule']} » : {FORMULES[sujet['formule']]}."})
    parties.append({"text": CONSIGNES_FORMAT[format_]})
    remarques: list[str] = []
    for essai in range(4):
        script = _demander(cfg, parties, remarques)
        remarques = controler(script, source["texte"], format_, len(images))
        if not remarques:
            return script
        journal(f"    ↺ script refusé ({essai + 1}/4) : " + " ; ".join(remarques)[:300])
    raise RuntimeError("script refusé au contrôle : " + " ; ".join(remarques)[:400])


def _credit(c: str) -> str:
    """« Unknown authorUnknown author / … » (auteur répété par Commons) → « Unknown author / … »."""
    return re.sub(r"^(.{3,40}?)\1", r"\1", c)


def completer_images(script: dict, images: list[dict], dossier: Path, journal=print) -> None:
    """Scènes sans image de l'article : une archive libre de Commons trouvée par leur « recherche » ; à défaut, une image
    déjà en réserve, différente de la scène précédente (essai Lustig du 06/11 : article à 1 image, vidéo sans aucune)."""
    from .medias_commons import chercher

    deja = {im["nom"] for im in images}
    trouvees: dict[str, int] = {}
    for sc in script["scenes"]:
        if 0 <= int(sc.get("image", -1)) < len(images):
            continue
        requete = (sc.get("recherche") or "").strip()
        if not requete:
            continue
        if requete not in trouvees:
            trouve = chercher(requete, dossier, f"rech{len(images)}", deja)
            time.sleep(0.5)
            if trouve:
                images.append({"src": f"{dossier.name}/{trouve[0].name}", "nom": requete, "description": requete,
                               "credit": _credit(trouve[1])})
            trouvees[requete] = len(images) - 1 if trouve else -1
        sc["image"] = trouvees[requete]
    if not images:
        return
    precedente = -2
    for k, sc in enumerate(script["scenes"]):
        if int(sc.get("image", -1)) < 0:
            choix = [i for i in range(len(images)) if i != precedente] or [0]
            sc["image"] = choix[k % len(choix)]
        precedente = sc["image"]
    journal(f"    🖼️ {len(images)} image(s) pour {len(script['scenes'])} scènes "
            f"({sum(1 for v in trouvees.values() if v >= 0)} trouvée(s) par recherche sur {len(trouvees)})")


def legende_finale(script: dict, source: dict, images: list[dict], utilisees: set[int]) -> str:
    texte = script["legende"].replace("—", ",").strip()
    credits = sorted({images[k]["credit"] for k in utilisees})
    tags = " ".join("#" + re.sub(r"\W", "", h.lstrip("#")) for h in script.get("hashtags", [])[:5] if re.sub(r"\W", "", h))
    pied = f"Source : Wikipédia, « {source['titre']} » (CC BY-SA)."
    if credits:
        pied += " Images : " + " ; ".join(credits) + "."
    return f"{texte}\n\n{pied}\n\n{tags}".strip()[:2200]


# --------------------------------------------------------------------------- vidéo

def rendre(cfg: dict, sujet: dict, script: dict, images: list[dict], dossier: Path, sortie: Path, couverture: Path,
           journal=print, format_: str | None = None) -> set[int]:
    """MP4 et miniature ; renvoie les numéros d'images utilisées (pour les crédits)."""
    from .voix import Voix
    from .voix_conseil import STYLE_BANDE_ANNONCE, narration

    scenes, dits, utilisees = [], [], set()
    for sc in script["scenes"]:
        s = {"type": sc["type"], "ecran": sc.get("ecran") or None, "grand": sc.get("grand") or None, "soustitre": sc["dit"]}
        k = int(sc.get("image", -1))
        if 0 <= k < len(images):
            s["image"] = {"src": images[k]["src"], "credit": images[k]["credit"]}
            utilisees.add(k)
        scenes.append(s)
        dits.append(sc["dit"])
    question = script["question"].strip()
    derniere_image = next((s["image"] for s in reversed(scenes) if s.get("image")), None)
    scenes.append({"type": "question", "ecran": question, "soustitre": question, **({"image": derniere_image} if derniere_image else {})})
    dits.append(question)
    scenes.append({"type": "signature", "duree": 3.0})
    dits.append("")
    textes = [{"cle": f"s{k}", "texte": t} for k, t in enumerate(dits)]
    pistes = {}
    if (cfg.get("perso") or {}).get("voix_gemini"):
        try:
            v = (cfg.get("histoires") or {}).get("voix") or {}
            pistes = {x["cle"]: x for x in narration(cfg, textes, dossier, "voix", journal, style=STYLE_BANDE_ANNONCE,
                                                     voix=v.get("nom", "Algenib"), demi_tons=v.get("demi_tons", 1))}
        except Exception as e:
            journal(f"⚠️ Voix Schedar indisponible, relais sur la voix Chirp : {e}")
    if not pistes:
        try:
            pistes = {x["cle"]: x for x in Voix(journal).narration(textes, dossier, "voix", forcer=True) or []}
        except Exception as e:
            journal(f"⚠️ Voix off indisponible, vidéo sans voix : {e}")
    for k, sc in enumerate(scenes):
        if f"s{k}" in pistes:
            sc["voix"] = {"src": pistes[f"s{k}"]["src"], "duree": pistes[f"s{k}"]["duree"]}
        elif sc["type"] != "signature":
            sc["duree"] = max(2.5, len(sc.get("soustitre") or "") / 15)
    format_ = format_ or sujet["format"]
    props = {"serie": NOM_SERIE, "titre": script["titre"], "compte": COMPTE, "scenes": scenes,
             "partie": {"serie": "Partie 1", "serie2": "Partie 2"}.get(format_), "format": format_,
             "musique": "melodie.wav", "volume_musique": 0.10}
    _remotion("RecitReel", props, sortie)
    premiere = scenes[0]
    _remotion("RecitCouverture", {"serie": NOM_SERIE, "accroche": premiere.get("ecran") or script["titre"],
                                  "image": premiere.get("image"), "partie": props["partie"], "compte": COMPTE}, couverture, still=True)
    return utilisees


def fabriquer(cfg: dict, sujet: dict, dossier_sortie: Path, nom: str, log=print, format_: str | None = None,
              partie1: dict | None = None) -> dict:
    """Une vidéo : <nom>.mp4, <nom>.jpg et <nom>.json (script, légende, sources) dans `dossier_sortie`."""
    format_ = format_ or sujet["format"]
    dossier_sortie.mkdir(parents=True, exist_ok=True)
    travail = MOTION / "public" / "_histoires"
    shutil.rmtree(travail, ignore_errors=True)
    travail.mkdir(parents=True)
    try:
        source = article(sujet["article"])
        titres = list(source["images"])
        if sujet.get("en"):
            try:
                titres += article(sujet["en"], "en")["images"]
            except Exception as e:
                log(f"    ⚠️ article anglais : {e}")
        images = images_libres(titres, travail, journal=log)
        log(f"    📚 article de {len(source['texte'])} caractères, {len(images)} image(s) libre(s)")
        script = ecrire_script(cfg, sujet, source, images, log, format_=format_, partie1=partie1)
        parole = sum(len(s["dit"]) for s in script["scenes"])
        log(f"    📝 « {script['scenes'][0]['ecran']} », {len(script['scenes'])} scènes, {parole} caractères dits")
        completer_images(script, images, travail, log)
        utilisees = rendre(cfg, sujet, script, images, travail, dossier_sortie / f"{nom}.mp4",
                           dossier_sortie / f"{nom}.jpg", log, format_=format_)
        meta = {"sujet": sujet, "format": format_, "source": source["url"],
                "legende": legende_finale(script, source, images, utilisees), "script": script, "images": images}
        (dossier_sortie / f"{nom}.json").write_text(json.dumps(meta, ensure_ascii=False, indent=1), encoding="utf-8")
        log(f"    ✅ {nom}.mp4")
        return meta
    finally:
        shutil.rmtree(travail, ignore_errors=True)


def essai(cfg: dict, log, sujet_id: str | None = None, dossier_sortie: Path = RACINE / "sortie" / "histoires") -> bool:
    """Fabrique les vidéos d'essai (toutes, ou `sujet_id`) dans sortie/histoires/ : <id>.mp4, <id>.jpg, <id>.json."""
    ok = True
    for sujet in [PAR_ID[sujet_id]] if sujet_id else SUJETS:
        log(f"• {sujet['article']} [{sujet['format']}, accroche {sujet['formule']}]")
        try:
            fabriquer(cfg, sujet, dossier_sortie, sujet["id"], log)
        except Exception as e:
            ok = False
            log(f"    ❌ {type(e).__name__} : {str(e)[:400]}")
    return ok


# --------------------------------------------------------------------------- production quotidienne

ETAT = RACINE / "etat" / "histoires.json"
# Créneaux (heure de Paris) : la partie 2 de la série d'hier à midi, un « chiffre fou » en fin d'après-midi,
# la partie 1 d'une nouvelle série le soir (elle finit sur un suspense : la suite arrive le lendemain midi).
CRENEAUX = {"serie2": "12:30", "chiffre": "18:30", "serie": "20:30"}


def lire_etat() -> dict:
    if ETAT.exists():
        return json.loads(ETAT.read_text(encoding="utf-8"))
    return {"faits": [], "attente_partie2": None, "journal": []}


def ecrire_etat(etat: dict) -> None:
    ETAT.parent.mkdir(parents=True, exist_ok=True)
    ETAT.write_text(json.dumps(etat, ensure_ascii=False, indent=1), encoding="utf-8")


def prochain(etat: dict, format_: str) -> dict | None:
    return next((s for s in CATALOGUE if s["format"] == format_ and s["id"] not in etat["faits"]), None)


def produire(cfg: dict, log, jour: str) -> list[dict]:
    """Fabrique les vidéos du `jour` (AAAA-MM-JJ) dans sortie/histoires/<jour>/ et met à jour etat/histoires.json.
    Renvoie [{"nom", "format", "heure", "titre"}] ; une vidéo ratée n'empêche pas les autres."""
    etat = lire_etat()
    dossier = RACINE / "sortie" / "histoires" / jour
    faites = []
    taches = []
    attente = etat.get("attente_partie2")
    if attente:
        taches.append(("serie2", PAR_ID[attente["id"]], attente))
    for format_ in ("chiffre", "serie"):
        s = prochain(etat, format_)
        if s:
            taches.append((format_, s, None))
        else:
            log(f"⚠️ catalogue épuisé pour le format « {format_} » : ajouter des sujets dans agent/histoires_sujets.py")
    for format_, sujet, att in taches:
        suffixe = {"serie": "p1", "serie2": "p2", "chiffre": "c"}[format_]
        nom = f"hva-{sujet['id']}-{suffixe}"
        log(f"• {sujet['article']} [{format_}]")
        try:
            meta = fabriquer(cfg, sujet, dossier, nom, log, format_=format_, partie1=att["script"] if att else None)
        except Exception as e:
            log(f"    ❌ {type(e).__name__} : {str(e)[:400]}")
            etat["journal"].append({"jour": jour, "id": sujet["id"], "format": format_, "erreur": str(e)[:300]})
            continue
        if format_ == "serie2":
            etat["attente_partie2"] = None
        else:
            etat["faits"].append(sujet["id"])
            if format_ == "serie":
                etat["attente_partie2"] = {"id": sujet["id"], "jour_partie1": jour, "script": meta["script"]}
        titre = meta["script"]["titre"] + {"serie": " (partie 1)", "serie2": " (partie 2)"}.get(format_, "")
        faites.append({"nom": nom, "format": format_, "heure": CRENEAUX[format_], "titre": titre})
        etat["journal"].append({"jour": jour, "id": sujet["id"], "format": format_, "nom": nom})
    (dossier / "plan.json").parent.mkdir(parents=True, exist_ok=True)
    (dossier / "plan.json").write_text(json.dumps(faites, ensure_ascii=False, indent=1), encoding="utf-8")
    ecrire_etat(etat)
    return faites


def programmer(cfg: dict, log, jour: str) -> bool:
    """Met en ligne les vidéos du `jour` (GitHub Pages) et les programme dans le second compte Buffer, sur TikTok et
    YouTube, aux heures de Paris du plan."""
    from datetime import date, datetime, timedelta
    from zoneinfo import ZoneInfo

    from .hebergement import mettre_en_ligne
    from .publieurs.buffer import requete

    h = cfg.get("histoires") or {}
    canaux = h.get("canaux") or {}
    dossier = RACINE / "sortie" / "histoires" / jour
    plan = json.loads((dossier / "plan.json").read_text(encoding="utf-8")) if (dossier / "plan.json").exists() else []
    if not plan:
        log("ℹ️ rien à programmer")
        return True
    adresses = mettre_en_ligne([dossier / f"{v['nom']}.mp4" for v in plan], date.fromisoformat(jour))
    etat = lire_etat()
    etat.setdefault("programmes", [])
    ok = True
    for v in plan:
        meta = json.loads((dossier / f"{v['nom']}.json").read_text(encoding="utf-8"))
        quand = datetime.fromisoformat(f"{jour}T{v['heure']}:00").replace(tzinfo=ZoneInfo("Europe/Paris"))
        if quand < datetime.now(ZoneInfo("Europe/Paris")):
            quand = datetime.now(ZoneInfo("Europe/Paris")).replace(second=0, microsecond=0) + timedelta(minutes=20)
        for reseau, canal in canaux.items():
            metadata = ({"tiktok": {"isAiGenerated": True, "title": v["titre"][:90]}} if reseau == "tiktok" else
                        {"youtube": {"title": v["titre"][:100], "categoryId": str(h.get("categorie_youtube", "27")),
                                     "privacy": "public", "madeForKids": False, "notifySubscribers": True,
                                     "embeddable": True, "license": "youtube"}})
            entree = {"channelId": canal, "text": meta["legende"], "schedulingType": "automatic", "mode": "customScheduled",
                      "dueAt": quand.astimezone(ZoneInfo("UTC")).strftime("%Y-%m-%dT%H:%M:%S.000Z"),
                      "assets": [{"video": {"url": adresses[f"{v['nom']}.mp4"], "metadata": {"thumbnailOffset": 0}}}],
                      "metadata": metadata}
            try:
                d = requete("""mutation($input: CreatePostInput!) { createPost(input: $input) {
                    ... on PostActionSuccess { post { id } } ... on MutationError { message } } }""",
                            {"input": entree}, cle="BUFFER_API_KEY_HISTOIRES")["createPost"]
            except Exception as e:
                d = {"message": f"{type(e).__name__} : {e}"}
            if d.get("post"):
                log(f"    📅 {reseau} {quand:%d/%m %H:%M} : {v['titre']}")
                etat["programmes"].append({"jour": jour, "nom": v["nom"], "reseau": reseau, "buffer": d["post"]["id"],
                                           "heure": quand.isoformat()})
            else:
                ok = False
                log(f"    ❌ {reseau} : {d.get('message', 'refus sans motif')[:300]}")
    ecrire_etat(etat)
    return ok


__all__ = ["essai", "controler", "article", "images_libres", "SUJETS"]
