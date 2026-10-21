"""Article d'un lot DECIDE MEDIA → scénario de motion design (Remotion, projet decide-motion) → vidéo MP4.

Sans IA : le scénario est construit à partir des champs du manifeste (protocole v1.2) :
content_type, country, event_date, title, body, value_added, topic, sources, hashtags.
"""
from __future__ import annotations

import json
import os
import re
import shutil
import subprocess
import tempfile
import unicodedata
from datetime import date
from pathlib import Path

# modèle Remotion : dossier motion/ du dépôt (GitHub), sinon l'ancien emplacement sur le PC
MOTION = Path(os.environ.get("DECIDE_MOTION_DIR") or Path(__file__).resolve().parent.parent / "motion")
RUBRIQUES = {"news": "ACTUALITÉ", "explainer": "DÉCRYPTAGE", "practical_guide": "GUIDE PRATIQUE",
             "analysis": "ANALYSE", "critical_explainer": "DÉCRYPTAGE", "factual_news": "ACTUALITÉ"}
LIBELLES = {
    "news": ["Le fait", "À savoir", "À noter", "En pratique"],
    "practical_guide": ["Le bon réflexe", "Comment faire", "À ne pas oublier", "En pratique"],
    "explainer": ["Le contexte", "À comprendre", "Les enjeux", "En pratique"],
}
# priorité des unités pour choisir le chiffre clé (montants et pourcentages d'abord)
PRIORITE_UNITES = [("%", "pour cent"), ("milliard", "million", "fcfa", "franc", "euro", "dollar"),
                   ("personnes", "candidats", "enfants", "emplois", "postes", "tonne", "kilom", "km"),
                   ("seconde", "minute", "jour", "semaine", "mois", "ans")]
MOIS = ["janvier", "février", "mars", "avril", "mai", "juin", "juillet", "août", "septembre", "octobre",
        "novembre", "décembre"]
ICONES = [  # (mots-clés, icône)
    (("santé", "vaccin", "maladie", "hôpital", "médic", "cancer", "rougeole"), "🩺"),
    (("mains", "savon", "hygiène", "lavage"), "🧼"),
    (("emploi", "recrut", "consultant", "poste", "travail", "candidat"), "💼"),
    (("financement", "dollars", "fcfa", "euros", "budget", "banque", "crédit", "lève", "subvention"), "💰"),
    (("école", "étudiant", "concours", "enam", "formation", "examen", "résultats"), "🎓"),
    (("agricult", "récolte", "karité", "soja", "cacao", "rural"), "🌾"),
    (("solaire", "énergie", "électricité"), "☀️"),
    (("route", "transport", "mobilité"), "🛣️"),
    (("numérique", "internet", "téléphone", "digital"), "📱"),
    (("football", "sport", "caf", "match"), "⚽"),
    (("eau", "inondation", "pluie"), "💧"),
    (("export", "commerce", "marché", "prix"), "📦"),
    (("femmes",), "👩🏾"),
    (("enfant", "parents", "famille"), "👨‍👩‍👧"),
    (("environnement", "vert", "climat"), "🌍"),
    (("report", "annul", "date", "calendrier"), "🗓️"),
]
ICONES_PAR_DEFAUT = ["📌", "🔎", "👥", "✅"]
RE_CHIFFRE = re.compile(
    r"(?<![\d/])(\d{1,3}(?:[   .]\d{3})*(?:,\d+)?|\d+(?:,\d+)?)\s*"
    r"(%|pour cent|(?:millions?|milliards?)(?:\s+(?:de\s+|d[’'])?(?:dollars?|FCFA|francs CFA|euros?|personnes|habitants|tonnes?))?|"
    r"secondes?|minutes?|heures?|jours?|semaines?|mois|ans|"
    r"FCFA|francs CFA|euros?|dollars?|personnes|candidats|enfants|emplois|postes|kilomètres?|km|tonnes?)",
    re.IGNORECASE,
)


def _sans_accents(t: str) -> str:
    return unicodedata.normalize("NFKD", t).encode("ascii", "ignore").decode().lower()


def _icone(texte: str, k: int) -> str:
    t = texte.lower()
    for mots, icone in ICONES:
        if any(m in t for m in mots):
            return icone
    return ICONES_PAR_DEFAUT[k % len(ICONES_PAR_DEFAUT)]


def _phrases(corps: str) -> list[str]:
    morceaux = re.split(r"(?<=[.!?])\s+(?=[A-ZÀ-ÖØ-Þ«\"0-9])", re.sub(r"\s+", " ", corps.strip()))
    return [m.strip() for m in morceaux if len(m.strip()) > 3]


def _couper(texte: str, n: int) -> str:
    if len(texte) <= n:
        return texte
    return texte[:n].rsplit(" ", 1)[0].rstrip(",;:") + "…"


def _lignes_titre(titre: str) -> list[str]:
    titre = re.sub(r"^(guide pratique|décryptage|decryptage|analyse|actualité)\s*[—–-]\s*", "", titre, flags=re.I)
    if ":" in titre:
        a, b = titre.split(":", 1)
        parties = [a.strip() + " :", b.strip()]  # espace insécable : le « : » ne reste jamais seul
    else:
        parties = [titre.strip()]
    largeur = 18 if len(titre) <= 50 else 22  # le modèle réduit la police quand il y a plus de 3 lignes
    lignes = []
    for p in parties:
        mots, ligne = [m for m in p.split(" ") if m], ""  # split(" ") : garde l'espace insécable avant « : »
        for m in mots:
            if len(ligne) + len(m) + 1 > largeur and ligne:
                lignes.append(ligne)
                ligne = m
            else:
                ligne = f"{ligne} {m}".strip()
        if ligne:
            lignes.append(ligne)
    return lignes[:6]


def _date_fr(iso: str | None) -> str | None:
    try:
        d = date.fromisoformat(str(iso)[:10])
        return f"{d.day} {MOIS[d.month - 1]} {d.year}"
    except (ValueError, TypeError):
        return None


def _chiffre(phrases: list[str]) -> dict | None:
    """Chiffre clé : on écarte heures, années, bornes d'intervalle ; on préfère montants et pourcentages."""
    candidats = []
    for p in phrases:
        for m in RE_CHIFFRE.finditer(p):
            avant = p[max(0, m.start() - 14):m.start()].lower()
            unite = m.group(2)
            u = unite.lower()
            if u.startswith("heure") or re.search(r"\b(à|a|vers)\s*$", avant):
                continue  # une heure de rendez-vous n'est pas un chiffre clé
            if re.search(r"\bentre\s+\d+\s+et\s*$", p[:m.start()].lower()) or re.search(r"\bentre\s*$", avant):
                continue  # borne d'un intervalle (« entre 9 et 59 mois »)
            brut = m.group(1).replace(" ", "").replace(" ", "").replace(" ", "").replace(".", "").replace(",", ".")
            try:
                valeur = float(brut)
            except ValueError:
                continue
            if u == "ans" and 1900 < valeur < 2100:
                continue
            rang = next((i for i, groupe in enumerate(PRIORITE_UNITES) if any(g in u for g in groupe)), 9)
            if rang >= 3 and valeur < 2:
                continue
            candidats.append((rang, p, m, valeur, unite))
    if not candidats:
        return None
    rang, p, m, valeur, unite = min(candidats, key=lambda c: c[0])
    reste = (p[:m.start()] + p[m.end():]).strip(" ,.;:")
    legende = _couper(re.sub(r"\s{2,}", " ", reste), 80)
    return {"valeur": valeur, "unite": unite, "legende": legende,
            "compte_a_rebours": unite.lower().startswith("seconde"), "decimales": 1 if valeur != int(valeur) else 0}


def construire_scenario(article: dict, image_publique: str, musique: str | None = "melodie.wav") -> dict:
    corps = article.get("body") or article.get("post_text", "")
    phrases = _phrases(corps)
    type_ = article.get("content_type", "news")
    libelles = LIBELLES.get(type_, LIBELLES["news"])
    accroche = _couper(phrases[0], 110) if phrases else ""
    milieu = phrases[1:-1] if len(phrases) > 2 else phrases[1:]
    milieu = milieu[:4]
    etapes = [{"titre": libelles[k % len(libelles)], "detail": _couper(p, 175), "icone": _icone(p, k)}
              for k, p in enumerate(milieu)]
    if len(etapes) < 2:  # textes courts : on découpe davantage
        etapes = [{"titre": libelles[k], "detail": _couper(p, 175), "icone": _icone(p, k)} for k, p in enumerate(phrases[:3])]
    fin = phrases[-1] if phrases else ""
    if len(phrases) > 2 and len(fin) < 70:  # une dernière phrase trop courte s'appuie sur la précédente
        fin = phrases[-2] + " " + fin
    editeurs = []
    for s in article.get("sources") or []:
        nom = (s or {}).get("publisher")
        if nom and nom not in editeurs:
            editeurs.append(nom)
    scenario = {
        "rubrique": RUBRIQUES.get(type_, "ACTUALITÉ"),
        "pays": (article.get("country") or "").upper() or None,
        "date": _date_fr(article.get("event_date")),
        "titre": _lignes_titre(article.get("title", "")),
        "image": image_publique,
        "accroche": accroche,
        "contexte": _couper(article.get("value_added", ""), 170) or None,
        "etapes": etapes,
        "chiffre": _chiffre(phrases),
        "conclusion": _couper(fin, 150) if len(phrases) > 1 else accroche,
        "source": ("Source : " + ", ".join(editeurs[:3])) if editeurs else None,
        "hashtags": [h if h.startswith("#") else f"#{h}" for h in (article.get("hashtags") or [])][:6],
    }
    if musique:
        scenario.update({"musique": musique, "volume_musique": 0.10})
    # Les champs vides restent présents à null : sinon Remotion reprendrait ceux de l'exemple par défaut.
    for cle in ("pays", "date", "contexte", "chiffre", "liste", "source", "audio", "musique", "durees"):
        scenario.setdefault(cle, None)
    return {k: (None if v in ("", []) else v) for k, v in scenario.items()}


def rendre_video(article: dict, image: Path, sortie: Path, journal=print) -> Path:
    """Fabrique le MP4 avec Remotion. Le visuel est copié dans public/_lots/ le temps du rendu."""
    if not (MOTION / "node_modules").exists():  # premier rendu sur une machine neuve
        subprocess.run(["npm.cmd" if shutil.which("npm.cmd") else "npm", "ci", "--no-audit", "--no-fund"],
                       cwd=MOTION, check=True, capture_output=True, timeout=900)
    dossier = MOTION / "public" / "_lots"
    dossier.mkdir(parents=True, exist_ok=True)
    nom_image = f"{article.get('id', 'article')}{image.suffix.lower()}"
    shutil.copy(image, dossier / nom_image)
    scenario = construire_scenario(article, f"_lots/{nom_image}")
    with tempfile.TemporaryDirectory() as d:
        props = Path(d) / "props.json"
        props.write_text(json.dumps(scenario, ensure_ascii=False), encoding="utf-8")
        commande = ["npx.cmd" if shutil.which("npx.cmd") else "npx", "remotion", "render", "src/index.ts", "DecideShort",
                    str(sortie.resolve()), f"--props={props}", "--codec=h264", "--crf=20", "--log=warn"]
        r = subprocess.run(commande, cwd=MOTION, capture_output=True, text=True, timeout=1800)
    try:
        (dossier / nom_image).unlink()
    except OSError:
        pass
    if r.returncode != 0 or not sortie.exists():
        raise RuntimeError(f"rendu Remotion impossible (code {r.returncode}) : {(r.stderr + r.stdout)[-1500:]}")
    return sortie
