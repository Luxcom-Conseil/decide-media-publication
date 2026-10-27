"""Photos et logos libres de Wikimedia Commons (la photothèque de Wikipédia), avec leur crédit.

Pour les Shorts DECIDE : les lieux, bâtiments et institutions nommés dans l'article (« Université de Yaoundé I »,
« logo BEAC »), que les banques d'images comme Pixabay n'ont pas. Seules les licences libres sont gardées (domaine
public, CC0, CC BY, CC BY-SA) ; le crédit (auteur, licence) est affiché à l'écran, comme ces licences l'exigent.
Les images des chaînes d'info ne sont jamais reprises : elles ne sont pas libres, même citées.
Gratuit, sans clé. Wikimedia demande un User-Agent qui identifie l'outil.
"""
from __future__ import annotations

import re
import unicodedata
from pathlib import Path

import requests

API = "https://commons.wikimedia.org/w/api.php"
ENTETES = {"User-Agent": "DecideMediaPublication/1.0 (https://github.com/Luxcom-Conseil/decide-media-publication)"}
LICENCES = re.compile(r"^(public domain|pd|cc0|cc by(-sa)?( \d\.\d)?|attribution)", re.I)
MIMES = {"image/jpeg": ".jpg", "image/png": ".png", "image/svg+xml": ".png", "image/webp": ".jpg"}
_MOTS_VIDES = {"logo", "de", "du", "des", "la", "le", "les", "et", "of", "the"}


def _sans_accents(t: str) -> str:
    return unicodedata.normalize("NFKD", t).encode("ascii", "ignore").decode().lower()


def _mots(t: str) -> set[str]:
    return {m for m in re.findall(r"[a-z0-9]+", _sans_accents(t)) if m not in _MOTS_VIDES and (len(m) >= 3 or m.isdigit() or m == "i")}


def _texte(meta: dict, cle: str) -> str:
    return re.sub(r"\s+", " ", re.sub(r"<[^>]+>", "", (meta.get(cle) or {}).get("value", ""))).strip()


def credit(auteur: str, licence: str) -> str:
    """« Photo : Kondah / Wikimedia Commons · CC BY-SA 4.0 » (auteur raccourci : il est affiché en petit)."""
    auteur = re.sub(r"\s*\(.*?\)", "", auteur).strip()[:40] or "auteur inconnu"
    return f"{auteur} / Wikimedia Commons · {licence}"


def chercher(requete: str, dossier: Path, nom: str, deja: set[str], logo: bool = False) -> tuple[Path, str] | None:
    """(fichier, crédit) de la meilleure image libre pour `requete`, ou None. Le titre du fichier doit contenir
    l'essentiel des mots de la requête : la recherche de Commons renvoie aussi des images sans rapport."""
    if not requete.strip():
        return None
    try:
        r = requests.get(API, headers=ENTETES, timeout=30, params={
            "action": "query", "format": "json", "generator": "search", "gsrsearch": requete + (" logo" if logo and "logo" not in requete.lower() else ""),
            "gsrnamespace": 6, "gsrlimit": 15, "prop": "imageinfo", "iiprop": "url|extmetadata|mime|size", "iiurlwidth": 1080})
        r.raise_for_status()
        pages = sorted((r.json().get("query") or {}).get("pages", {}).values(), key=lambda p: p.get("index", 0))
    except (requests.RequestException, ValueError):
        return None
    voulus = _mots(requete)
    for p in pages:
        info = (p.get("imageinfo") or [{}])[0]
        meta = info.get("extmetadata") or {}
        titre = p.get("title", "")
        if titre in deja or info.get("mime") not in MIMES or _texte(meta, "NonFree").lower() == "true":
            continue
        licence = _texte(meta, "LicenseShortName")
        if not LICENCES.match(licence):
            continue
        presents = voulus & _mots(titre)
        if voulus and len(presents) / len(voulus) < 0.6:
            continue
        if logo and "logo" not in titre.lower():
            continue
        if not logo and min(info.get("width", 0), info.get("height", 0)) < 600:
            continue
        url = info.get("thumburl") or info.get("url")
        sortie = dossier / f"{nom}{MIMES[info['mime']]}"
        try:
            with requests.get(url, headers=ENTETES, timeout=(15, 120)) as f:
                f.raise_for_status()
                sortie.write_bytes(f.content)
        except requests.RequestException:
            continue
        deja.add(titre)
        return sortie, credit(_texte(meta, "Artist"), licence)
    return None
