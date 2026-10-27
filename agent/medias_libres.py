"""Vidéos et photos réalistes libres de droits pour les fonds des Reels.

- Pixabay (gratuit, clé PIXABAY_API_KEY) : la source principale. Pexels a suspendu la délivrance de nouvelles clés
  (constaté le 27/10/2026). Les vidéos Pixabay sont surtout horizontales : le gabarit les recadre en vertical.
- Pexels (clé PEXELS_API_KEY), utilisé seulement si une clé existe.
D'abord une courte vidéo (verticale de préférence), sinon une photo verticale. Les médias sont téléchargés (pas de
lien direct vers les banques d'images). Sans clé ou sans résultat : None, et la scène garde le fond animé.
"""
from __future__ import annotations

import os
from pathlib import Path

import requests


def disponible() -> bool:
    return bool(os.environ.get("PIXABAY_API_KEY") or os.environ.get("PEXELS_API_KEY"))


def _telecharger(url: str, sortie: Path) -> Path:
    with requests.get(url, stream=True, timeout=(15, 120)) as r:
        r.raise_for_status()
        with sortie.open("wb") as f:
            for bloc in r.iter_content(1 << 20):
                f.write(bloc)
    return sortie


def _pixabay(requete: str, dossier: Path, nom: str, deja: set[str]) -> tuple[Path, bool] | None:
    cle = os.environ["PIXABAY_API_KEY"]
    r = requests.get("https://pixabay.com/api/videos/", timeout=30,
                     params={"key": cle, "q": requete[:100], "per_page": 20, "safesearch": "true", "video_type": "film"})
    r.raise_for_status()
    candidats = []
    for v in r.json().get("hits", []):
        if f"x{v['id']}" in deja or v.get("duration", 0) < 4:
            continue
        tailles = [t for t in (v.get("videos") or {}).values() if t.get("url") and (t.get("height") or 0) >= 720]
        if not tailles:
            continue
        # la plus légère qui reste nette une fois recadrée en 1080×1920 ; les vidéos verticales passent devant
        t = min(tailles, key=lambda t: (t["height"] < 1080, t.get("size") or 1e12))
        candidats.append((t["height"] <= t["width"], v["id"], t["url"]))
    if candidats:
        _, ident, url = sorted(candidats, key=lambda c: c[0])[0]
        deja.add(f"x{ident}")
        return _telecharger(url, dossier / f"{nom}.mp4"), True
    r = requests.get("https://pixabay.com/api/", timeout=30, params={"key": cle, "q": requete[:100], "image_type": "photo",
                                                                     "orientation": "vertical", "per_page": 20, "safesearch": "true"})
    r.raise_for_status()
    for p in r.json().get("hits", []):
        if f"y{p['id']}" not in deja:
            deja.add(f"y{p['id']}")
            return _telecharger(p["largeImageURL"], dossier / f"{nom}.jpg"), False
    return None


def _pexels(requete: str, dossier: Path, nom: str, deja: set[str]) -> tuple[Path, bool] | None:
    entetes = {"Authorization": os.environ["PEXELS_API_KEY"]}
    r = requests.get("https://api.pexels.com/videos/search", headers=entetes, timeout=30,
                     params={"query": requete, "orientation": "portrait", "size": "medium", "per_page": 10})
    r.raise_for_status()
    for v in r.json().get("videos", []):
        if f"v{v['id']}" in deja or v.get("duration", 0) < 4:
            continue
        fichiers = [f for f in v.get("video_files", []) if f.get("file_type") == "video/mp4"
                    and (f.get("height") or 0) >= 1280 and (f.get("height") or 0) > (f.get("width") or 0)]
        if fichiers:
            deja.add(f"v{v['id']}")
            return _telecharger(min(fichiers, key=lambda f: f["height"])["link"], dossier / f"{nom}.mp4"), True
    r = requests.get("https://api.pexels.com/v1/search", headers=entetes, timeout=30,
                     params={"query": requete, "orientation": "portrait", "per_page": 10})
    r.raise_for_status()
    for p in r.json().get("photos", []):
        if f"p{p['id']}" not in deja:
            deja.add(f"p{p['id']}")
            return _telecharger(p["src"]["large2x"], dossier / f"{nom}.jpg"), False
    return None


def chercher(requete: str, dossier: Path, nom: str, deja: set[str]) -> tuple[Path, bool] | None:
    """(fichier, est_une_vidéo) pour la requête (en anglais), en évitant les médias déjà pris (`deja`)."""
    if not requete.strip():
        return None
    for variable, source in (("PIXABAY_API_KEY", _pixabay), ("PEXELS_API_KEY", _pexels)):
        if not os.environ.get(variable):
            continue
        try:
            trouve = source(requete, dossier, nom, deja)
        except requests.RequestException:
            trouve = None
        if trouve:
            return trouve
    return None
