"""Rubrique « Présidentielle 2027 » du compte Histoires vraies d'argent : le programme de La France insoumise expliqué,
une mesure ou un constat chiffré par vidéo, en plus des 3 histoires quotidiennes.

Décisions de Stéphane du 07/11/2026 :
- ton explicatif (on explique, on ne fait pas campagne), dans la ligne « histoire économique de la France et de
  l'Europe d'aujourd'hui » ; format proche des histoires, avec des accroches et des relances plus travaillées ;
- 6 vidéos par jour jusqu'au 7 janvier 2027, puis 2 en semaine et 4 le week-end jusqu'au 16 avril ;
- rien les 17 et 18 avril (veille et jour du premier tour : Code électoral, article L49) ;
- entre les deux tours, 6 par jour si LFI est qualifiée (config.yaml, programme.second_tour), rien sinon ; rien les
  1er et 2 mai.

Sources : documents publiés par la campagne (sources/programme/*.txt, texte extrait des PDF et pages officiels),
découpés une fois pour toutes en fiches (sources/programme/fiches.json, commande programme-fiches) : une fiche = un
passage exact du document, une mesure ou un constat. Contrôle : aucun chiffre absent du passage, l'attribution à LFI
est obligatoire, aucun appel au vote.
"""
from __future__ import annotations

import json
import re
import shutil
import time
from datetime import date, timedelta
from pathlib import Path

from . import histoires as h
from .perso import MOTION, RACINE

SOURCES = RACINE / "sources" / "programme"
FICHES = SOURCES / "fiches.json"
ETAT = RACINE / "etat" / "programme.json"
DOCS = {  # nom du fichier → titre du document, tel que publié par la campagne
    "comptes-publics": "Comment nous allons remettre de l'ordre dans les comptes publics",
    "pole-public-bancaire": "Pour un pôle public bancaire au service des besoins",
    "plan-sante": "Comment nous allons reconstruire notre système de santé",
    "plan-esr": "Comment nous allons refonder l'enseignement supérieur, la recherche et la formation continue",
    "plan-ruralites": "Comment nous allons garantir l'égalité pour des ruralités où il fait bon vivre",
    "plan-btp-logement": "Plan d'investissement BTP et logement",
    "plan-automobile": "Plan d'investissement automobile",
    # contributions.txt (synthèse des 24 000 contributions) n'est pas une source de fiches : ce sont des propositions de
    # citoyens, pas des mesures de LFI ; les lui attribuer serait faux.
}

# --------------------------------------------------------------------------- calendrier

PREMIER_TOUR, SECOND_TOUR = date(2027, 4, 18), date(2027, 5, 2)
CRENEAUX = {  # heure de Paris ; les histoires gardent 12 h 30, 18 h 30 et 20 h 30
    6: ["07:30", "09:45", "11:15", "14:30", "16:30", "22:00"],
    4: ["09:45", "14:30", "16:30", "22:00"],
    2: ["11:15", "22:00"],
}


def quota(jour: date, cfg: dict) -> int:
    """Nombre de vidéos programme à publier ce jour-là."""
    if jour in (PREMIER_TOUR - timedelta(1), PREMIER_TOUR, SECOND_TOUR - timedelta(1), SECOND_TOUR):
        return 0  # veille et jour de scrutin : aucune propagande électorale (Code électoral, L49)
    if jour <= date(2027, 1, 7):
        return 6
    if jour < PREMIER_TOUR:
        return 4 if jour.weekday() >= 5 else 2
    if jour < SECOND_TOUR:
        return 6 if (cfg.get("programme") or {}).get("second_tour") is True else 0
    return 0


# --------------------------------------------------------------------------- fiches

def _plat(t: str) -> str:
    """Texte réduit à ses lettres et chiffres, pour retrouver un passage malgré les coupures de lignes des PDF."""
    t = re.sub(r"\s*-\s*\n\s*", "", t)  # « investisse -\nments »
    return re.sub(r"[^0-9a-zà-ÿœæ]+", " ", t.lower()).strip()


def _fidele(extrait: str, document: str) -> bool:
    """Le passage vient bien du document : 80 % de ses suites de 6 mots s'y retrouvent, et tous ses chiffres."""
    mots, doc = _plat(extrait).split(), " " + _plat(document) + " "
    if len(mots) < 25:
        return False
    suites = [" ".join(mots[k:k + 6]) for k in range(0, len(mots) - 5, 3)]
    if sum(f" {s} " in doc for s in suites) < 0.8 * len(suites):
        return False
    return h._nombres(extrait) <= h._nombres(document)


SCHEMA_FICHES = {"type": "object", "properties": {"fiches": {"type": "array", "items": {
    "type": "object", "properties": {"titre": h._TXT, "extrait": h._TXT, "angle": h._TXT,
                                     "formule": {"type": "string", "enum": ["Chiffre", "Question", "Contre-pied", "Toi"]}},
    "required": ["titre", "extrait", "angle", "formule"], "additionalProperties": False}}},
    "required": ["fiches"], "additionalProperties": False}

SYSTEME_FICHES = """Tu prépares des sujets de vidéos courtes explicatives à partir d'un document de programme électoral \
(La France insoumise, élection présidentielle française de 2027). Une fiche = UNE mesure précise, OU UN constat chiffré \
que le document avance, assez riche pour une vidéo de 35 secondes. Pour chaque fiche :
- « extrait » : la COPIE EXACTE, mot pour mot, d'un passage continu du document de 300 à 1 200 caractères, qui contient \
tout ce qu'il faut pour expliquer la mesure ou le constat (chiffres compris). Tu peux seulement recoller les mots coupés \
par un tiret en fin de ligne. N'ajoute, ne résume et ne reformule rien.
- « titre » : le sujet en 6 mots au plus (« Le livret A à 30 000 euros »).
- « angle » : en une phrase, ce qui peut arrêter le défilement d'un spectateur français (le chiffre qui étonne, ce que ça \
changerait dans sa vie).
- « formule » : la formule d'accroche qui convient le mieux (Chiffre, Question, Contre-pied ou Toi).
GRAIN FIN (impératif) : une fiche par mesure. Quand un passage aligne plusieurs mesures chiffrées (par exemple une \
taxe à 9 milliards, un impôt à 10 milliards, une réforme à 20 milliards), fais UNE FICHE PAR MESURE ; leurs extraits \
peuvent alors se recouper. Un constat chiffré important (dette, déficit, épargne, investissement) a aussi sa propre \
fiche. Vise une fiche pour 400 à 800 caractères de document utile.
Ignore les sommaires, menus, mentions légales, notes, légendes de graphique isolées, et les passages sans mesure ni \
constat. Deux fiches ne doivent pas traiter la même mesure. Prends tout ce qui mérite une vidéo, sans limite de nombre."""


def extraire_fiches(cfg: dict, log=print, seulement: str | None = None) -> list[dict]:
    """Découpe chaque document en fiches (Gemini), garde celles dont le passage est fidèle, et écrit fiches.json.
    Les fiches déjà extraites d'un document sont gardées (on ne redécoupe que `seulement` ou les documents absents)."""
    fiches = json.loads(FICHES.read_text(encoding="utf-8")) if FICHES.exists() else []
    faits = {f["doc"] for f in fiches}
    for doc in DOCS:
        if (seulement and doc != seulement) or (not seulement and doc in faits):
            continue
        fiches = [f for f in fiches if f["doc"] != doc]
        texte = (SOURCES / f"{doc}.txt").read_text(encoding="utf-8")
        corps = texte.split("\n\n", 1)[1] if texte.startswith("SOURCE") else texte
        gardees, ecartees, n = [], 0, 0
        passes = [(f"<document titre=\"{DOCS[doc]}\">\n{corps[max(0, d - 500):d + 4000]}\n</document>",
                   "Prépare les fiches de ce morceau du document.") for d in range(0, len(corps), 4000)]
        passes.append(None)  # passe de complément sur le document entier, une fois les morceaux faits
        for passe in passes:
            if passe is None:
                deja = "\n".join(f"- {g['titre']}" for g in gardees)
                passe = (f"<document titre=\"{DOCS[doc]}\">\n{corps[:60000]}\n</document>\n<deja>\n{deja}\n</deja>",
                         "Les fiches de la liste <deja> existent déjà. Prépare UNIQUEMENT les fiches des mesures ou "
                         "constats chiffrés du document qui n'y sont pas (aucune si rien ne manque).")
            r = None
            for attente in (0, 90, 180):  # offre gratuite souvent saturée (HTTP 503) : on patiente avant d'abandonner
                time.sleep(attente)
                try:
                    r = h._demander(cfg, [{"text": passe[0]}], [], systeme=SYSTEME_FICHES, schema=SCHEMA_FICHES,
                                    consigne=passe[1])
                    break
                except Exception as e:
                    log(f"    ⚠️ {doc} : {str(e)[:120]}")
            for f in (r or {}).get("fiches", []):
                n += 1
                titres = {_plat(g["titre"]) for g in gardees}
                if not _fidele(f["extrait"], corps) or _plat(f["titre"]) in titres:
                    ecartees += 1
                    continue
                gardees.append({"id": f"{doc}-{len(gardees) + 1:03d}", "doc": doc, **f})
        log(f"• {doc} : {len(gardees)} fiche(s) gardée(s), {ecartees} écartée(s) sur {n}")
        fiches += gardees
        FICHES.write_text(json.dumps(fiches, ensure_ascii=False, indent=1), encoding="utf-8")
    return fiches


def _ordre(fiches: list[dict]) -> list[dict]:
    """Les documents en alternance (un sujet de chaque à tour de rôle), pour varier d'une vidéo à l'autre."""
    par_doc: dict[str, list[dict]] = {}
    for f in fiches:
        par_doc.setdefault(f["doc"], []).append(f)
    files = list(par_doc.values())
    sortie = []
    for k in range(max((len(x) for x in files), default=0)):
        sortie += [x[k] for x in files if k < len(x)]
    return sortie


# --------------------------------------------------------------------------- script

FORMULES = {
    "Chiffre": "un chiffre réel de l'extrait qui étonne, posé sans contexte (« 1 337 euros. C'est le seuil que LFI veut garantir à chaque jeune. »)",
    "Question": "une question directe sur la vie du spectateur (« Et si ton livret A rapportait enfin plus que l'inflation ? »)",
    "Contre-pied": "ce que tout le monde croit, puis ce que dit le document (« On croit que l'État n'a plus d'argent. LFI dit qu'il en a laissé filer. »)",
    "Toi": "qui est concerné, en le désignant (« Si tu as un livret A, cette mesure te concerne directement. »)",
}

SYSTEME = """Tu écris le script d'une vidéo TikTok verticale d'environ 60 secondes pour le compte « Histoires vraies \
d'argent », rubrique Présidentielle 2027 : on explique, une mesure ou un constat à la fois, le programme de La France \
insoumise (LFI) pour l'élection présidentielle française des 18 avril et 2 mai 2027, comme on raconte l'histoire \
économique de la France d'aujourd'hui. Public : adultes de France qui font défiler leur fil. Tu as 2 secondes pour les \
arrêter, puis chaque scène doit donner envie de voir la suivante.

TON EXPLICATIF (impératif) :
- Tu expliques, tu ne fais pas campagne. Jamais d'appel au vote ni au soutien, jamais « nous » ou « notre » pour parler \
du programme, aucun adjectif qui juge la mesure à ton compte (formidable, injuste, irréaliste, catastrophique).
- Tout ce que dit le document est la position de LFI : attribue-le (« LFI propose », « selon LFI », « d'après le \
programme »). Les constats et chiffres sur la situation actuelle sont ceux qu'avance LFI : « selon LFI », « d'après ses \
chiffres ». Les mesures sont au conditionnel ou attribuées (« LFI veut porter le livret A à 30 000 euros »).
- Chaque jugement, justification ou promesse du document reste attribué DANS LA MÊME PHRASE, y compris dans la scène \
« lecon » : jamais « Ces mesures sont indispensables », toujours « Pour LFI, ces mesures sont indispensables ».
- NOMS : alterne souvent entre « LFI » (ou « La France insoumise », « les insoumis ») et « Jean-Luc Mélenchon », le \
candidat de LFI à la présidentielle 2027 (« Jean-Luc Mélenchon veut… », « dans le programme de Jean-Luc Mélenchon… », \
« pour Mélenchon… ») : au moins deux fois chacun dans la vidéo, jamais le même nom deux phrases de suite. Ne lui prête \
que ce que dit le document. Ne nomme pas d'autre personne que celles que l'extrait nomme.

STORYTELLING (la vidéo se raconte comme une histoire, pas comme une fiche) :
- Un point de départ concret et vécu : une situation que connaît le spectateur (« Imagine : fin du mois, ton compte est \
à découvert le 20. »), sans inventer de personne réelle, de chiffre ni de fait.
- La tension : le problème, tel que le décrit LFI ; fais monter l'enjeu.
- Le tournant : la mesure, posée comme une révélation.
- La suite : comment elle marcherait, qui paierait, ce qui l'accompagne, avec des enchaînements qui donnent envie \
(« Et c'est là que ça devient intéressant. », « Mais attends. », « Sauf que… »).
- La chute : retour au point de départ (ce que ça changerait pour toi), puis la scène « lecon ».
- Les phrases s'enchaînent comme un récit dit d'un seul souffle : connecteurs, rebonds, jamais une liste.

EXACTITUDE : ta seule source est l'extrait fourni. N'invente aucun fait, aucune date, aucun montant. Garde les unités \
(milliards, % du PIB, euros net). Si l'extrait dit « environ » ou « jusqu'à », garde-le.

ACCROCHE (première scène, type « accroche ») : 12 mots au plus dans « ecran », selon la formule demandée ; « dit » = la \
même accroche à l'oral, 140 caractères au plus.

RÉTENTION (le plus important après l'exactitude) :
- Dès la 2e scène, ouvre une boucle que tu fermeras plus loin (« Et le plus surprenant, c'est qui paierait. »).
- Toutes les deux ou trois scènes, une relance : une question, un chiffre, un « mais », un « sauf que », un « et ce \
n'est pas tout ».
- Rends concret : ce que ça changerait pour un salarié, un étudiant, un retraité, un épargnant, quand l'extrait le permet.
- Phrases courtes, français oral de France, présent ; tu peux dire « tu ». Pas de tiret long (—), pas d'émoji.

Scènes : une idée chacune, « dit » entre 40 et 140 caractères.
- « chiffre » : un montant ou un nombre de l'extrait ; « grand » = ce chiffre court (« 100 milliards », « 1 700 € net ») ; \
« ecran » = ce qu'il mesure (5 mots au plus) ;
- « date » : « grand » = l'année ou la date courte ; « ecran » = ce qui se passe (5 mots au plus) ;
- « recit » : le reste ; « grand » = null ; « ecran » = 6 mots au plus, le mot clé entre astérisques (« Le *livret A* plafonné ») ;
- la dernière scène est de type « lecon » : ce qu'il faut retenir, en une phrase attribuée (« ecran » = cette phrase, \
90 caractères au plus ; « dit » = la même phrase).
Au moins une scène « chiffre » ou « date ».

IMAGES : « image » = -1 pour chaque scène (aucune image n'est fournie) et « recherche » = 2 à 4 mots EN ANGLAIS pour \
trouver une photo libre sur Wikimedia Commons d'une chose réelle et visible liée à la scène (« Assemblee nationale \
hemicycle », « Banque de France », « euro banknotes », « French hospital », « Paris Bourse », « La Poste France », \
« Jean-Luc Melenchon »), jamais une idée abstraite ; deux scènes qui se suivent n'ont pas la même recherche.

« titre » : le sujet, 40 caractères au plus. « question » : une question courte qui fait réagir sans orienter la \
réponse (« Tu serais pour ou contre ? », « Ça changerait quoi pour toi ? »). Ne la mets pas dans les scènes.
« legende » : la légende, 2 à 4 lignes : l'accroche, une phrase qui donne envie, la question. Pas de hashtag ni de \
lien, pas d'émoji. « hashtags » : 3 à 5 hashtags en français sans le #, dont presidentielle2027."""

CONSIGNE_FORMAT = """FORMAT PROGRAMME (60 secondes) : entre 12 et 16 scènes, de 950 à 1 100 caractères dits en tout, \
question comprise (vise 1 000). La scène 1 est TOUJOURS de type « accroche » ; le point de départ vécu (« Imagine… ») \
vient en scène 2. Puis : la tension (le problème selon LFI) ; le tournant (la mesure) ; \
comment elle marcherait et combien elle coûterait ou rapporterait, si l'extrait le dit ; ce qui l'accompagne ; ce que \
ça changerait concrètement ; la scène « lecon »."""

_ATTRIBUTION = re.compile(r"\b(LFI|France insoumise|insoumis|Mélenchon)", re.I)
_CAMPAGNE = re.compile(r"\b(vote[zr]?|votons|votez|élisez|soutenez|rejoignez|notre programme|nous proposons)\b", re.I)


def controler(script: dict, source: str) -> list[str]:
    # le cadre de la rubrique (présidentielle 2027, 18 avril et 2 mai) peut être cité même si l'extrait ne le dit pas
    problemes = h.controler(script, source + "\nPrésidentielle 2027 : 18 avril et 2 mai 2027.", "programme", 0)
    problemes = [p for p in problemes if "hors de la liste" not in p]  # images : toujours -1 + recherche ici
    dits = " ".join(sc.get("dit", "") for sc in script.get("scenes") or [])
    if not _ATTRIBUTION.search(dits):
        problemes.append("la voix doit attribuer la mesure à LFI au moins une fois (« LFI propose », « selon LFI »)")
    tout = " ".join([dits, script.get("legende", ""), script.get("question", "")])
    if m := _CAMPAGNE.search(tout):
        problemes.append(f"ton de campagne interdit (« {m.group(0)} ») : on explique, on ne fait pas campagne")
    return problemes


def ecrire_script(cfg: dict, fiche: dict, source: str, journal=print) -> dict:
    parties = [{"text": f"<extrait document=\"{DOCS[fiche['doc']]}\" sujet=\"{fiche['titre']}\">\n{source}\n</extrait>"},
               {"text": f"La vidéo porte sur cette mesure : « {fiche['titre']} ». Le reste de l'extrait sert de contexte "
                        "(pourquoi, combien ça coûte ou rapporte, à qui ça s'applique) ; ne dérive pas vers une autre mesure."},
               {"text": f"Angle suggéré : {fiche['angle']}"},
               {"text": f"L'accroche suit la formule « {fiche['formule']} » : {FORMULES[fiche['formule']]}."},
               {"text": CONSIGNE_FORMAT}]
    remarques: list[str] = []
    for essai in range(4):
        script = h._demander(cfg, parties, remarques, systeme=SYSTEME)
        remarques = controler(script, source)
        if not remarques:
            return script
        journal(f"    ↺ script refusé ({essai + 1}/4) : " + " ; ".join(remarques)[:300])
    raise RuntimeError("script refusé au contrôle : " + " ; ".join(remarques)[:400])


def _url(doc: str) -> str:
    t = (SOURCES / f"{doc}.txt").read_text(encoding="utf-8")
    return t.split("\n", 1)[0].removeprefix("SOURCE : ").strip() if t.startswith("SOURCE") else ""


def legende(script: dict, fiche: dict, images: list[dict], utilisees: set[int]) -> str:
    texte = script["legende"].replace("—", ",").strip()
    tags = [re.sub(r"\W", "", t.lstrip("#")) for t in script.get("hashtags", [])[:5]]
    tags = [t for t in tags if t] + ([] if "presidentielle2027" in [t.lower() for t in tags] else ["presidentielle2027"])
    pied = f"Source : programme de La France insoumise, « {DOCS[fiche['doc']]} » ({_url(fiche['doc'])})."
    credits = sorted({images[k]["credit"] for k in utilisees})
    if credits:
        pied += " Images : " + " ; ".join(credits) + "."
    return f"{texte}\n\n{pied}\n\n{' '.join('#' + t for t in tags)}".strip()[:2200]


def _contexte(fiche: dict, taille: int = 3000) -> str:
    """L'extrait et le texte qui l'entoure dans le document (≈ `taille` caractères) : un extrait court donne sinon
    un script maigre et répétitif. Le contrôle des chiffres porte sur ce même passage."""
    corps = " ".join((SOURCES / f"{fiche['doc']}.txt").read_text(encoding="utf-8").split())
    debut = " ".join(fiche["extrait"].split())[:60]
    i = corps.find(debut)
    if i < 0 or len(fiche["extrait"]) >= taille:
        return fiche["extrait"]
    marge = (taille - len(fiche["extrait"])) // 2
    a, b = max(0, i - marge), min(len(corps), i + len(fiche["extrait"]) + marge)
    a = corps.rfind(". ", 0, a) + 2 if corps.rfind(". ", 0, a) > 0 else a  # commence et finit sur une phrase
    b = (corps.find(". ", b) + 1) or b
    return corps[a:b]


def fabriquer(cfg: dict, fiche: dict, dossier_sortie: Path, nom: str, log=print) -> dict:
    """Une vidéo : <nom>.mp4, .jpg et .json dans `dossier_sortie`."""
    dossier_sortie.mkdir(parents=True, exist_ok=True)
    travail = MOTION / "public" / "_histoires"
    shutil.rmtree(travail, ignore_errors=True)
    travail.mkdir(parents=True)
    try:
        script = ecrire_script(cfg, fiche, _contexte(fiche), log)
        parole = sum(len(s["dit"]) for s in script["scenes"])
        log(f"    📝 « {script['scenes'][0]['ecran']} », {len(script['scenes'])} scènes, {parole} caractères dits")
        images: list[dict] = []
        h.completer_images(script, images, travail, log)
        utilisees = h.rendre(cfg, {"format": "programme"}, script, images, travail, dossier_sortie / f"{nom}.mp4",
                             dossier_sortie / f"{nom}.jpg", log, format_="programme")
        meta = {"fiche": fiche, "source": _url(fiche["doc"]), "legende": legende(script, fiche, images, utilisees),
                "script": script, "images": images}
        (dossier_sortie / f"{nom}.json").write_text(json.dumps(meta, ensure_ascii=False, indent=1), encoding="utf-8")
        log(f"    ✅ {nom}.mp4")
        return meta
    finally:
        shutil.rmtree(travail, ignore_errors=True)


# --------------------------------------------------------------------------- production quotidienne

def lire_etat() -> dict:
    return json.loads(ETAT.read_text(encoding="utf-8")) if ETAT.exists() else {"faits": [], "ecartes": {}, "journal": []}


def ecrire_etat(etat: dict) -> None:
    ETAT.parent.mkdir(parents=True, exist_ok=True)
    ETAT.write_text(json.dumps(etat, ensure_ascii=False, indent=1), encoding="utf-8")


def produire(cfg: dict, log, jour: str) -> list[dict]:
    """Fabrique les vidéos programme du `jour` dans sortie/programme/<jour>/ (autant que le calendrier en prévoit)."""
    n = quota(date.fromisoformat(jour), cfg)
    dossier = RACINE / "sortie" / "programme" / jour
    dossier.mkdir(parents=True, exist_ok=True)
    faites: list[dict] = []
    if not n:
        log(f"ℹ️ aucune vidéo programme prévue le {jour} (calendrier électoral)")
    else:
        etat = lire_etat()
        fiches = [f for f in _ordre(json.loads(FICHES.read_text(encoding="utf-8")))
                  if f["id"] not in etat["faits"] and f["id"] not in etat["ecartes"]]
        heures = CRENEAUX[n]
        deja = sum(1 for j in etat["journal"] if j["jour"] == jour)  # relance dans la journée : seulement le manque
        n -= deja
        echecs = etat.setdefault("echecs", {})
        for fiche in fiches[:n + 4]:  # 4 fiches de réserve si un script est refusé
            if len(faites) >= n:
                break
            nom = f"prog-{fiche['id']}"
            log(f"• {fiche['titre']} [{fiche['doc']}, accroche {fiche['formule']}]")
            try:
                meta = fabriquer(cfg, fiche, dossier, nom, log)
            except Exception as e:
                log(f"    ❌ {type(e).__name__} : {str(e)[:400]}")
                echecs[fiche["id"]] = echecs.get(fiche["id"], 0) + 1
                if echecs[fiche["id"]] >= 2:  # deux passages ratés : la fiche sort du catalogue
                    etat["ecartes"][fiche["id"]] = str(e)[:200]
                continue
            etat["faits"].append(fiche["id"])
            faites.append({"nom": nom, "format": "programme", "heure": heures[deja + len(faites)],
                           "titre": meta["script"]["titre"]})
            etat["journal"].append({"jour": jour, "id": fiche["id"], "nom": nom})
        if len(faites) < n:
            log(f"⚠️ {len(faites)} vidéo(s) sur {n} prévues ; reste {len(fiches) - len(faites)} fiche(s) au catalogue")
        ecrire_etat(etat)
    (dossier / "plan.json").write_text(json.dumps(faites, ensure_ascii=False, indent=1), encoding="utf-8")
    return faites


def programmer(cfg: dict, log, jour: str) -> bool:
    return h.programmer(cfg, log, jour, dossier=RACINE / "sortie" / "programme" / jour, lire=lire_etat, ecrire=ecrire_etat)
