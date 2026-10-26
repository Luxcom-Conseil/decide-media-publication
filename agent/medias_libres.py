"""Vidéos et photos réalistes libres de droits pour les fonds des Reels : Pexels (gratuit, clé PEXELS_API_KEY, usage
commercial permis sans attribution obligatoire). D'abord une courte vidéo verticale, sinon une photo verticale.
Sans clé ou sans résultat : None, et la scène garde le fond animé.
"""
from __future__ import annotations

import os
from pathlib import Path

import requests

API = "https://api.pexels.com"


def disponible() -> bool:
    return bool(os.environ.get("PEXELS_API_KEY"))


def _get(chemin: str, **params) -> dict:
    r = requests.get(f"{API}{chemin}", params=params, headers={"Authorization": os.environ["PEXELS_API_KEY"]}, timeout=30)
    r.raise_for_status()
    return r.json()


def _telecharger(url: str, sortie: Path) -> Path:
    with requests.get(url, stream=True, timeout=(15, 120)) as r:
        r.raise_for_status()
        with sortie.open("wb") as f:
            for bloc in r.iter_content(1 << 20):
                f.write(bloc)
    return sortie


def chercher(requete: str, dossier: Path, nom: str, deja: set[str]) -> tuple[Path, bool] | None:
    """(fichier, est_une_vidéo) pour la requête (en anglais), en évitant les médias déjà pris (`deja`)."""
    if not disponible() or not requete.strip():
        return None
    try:
        for v in _get("/videos/search", query=requete, orientation="portrait", size="medium", per_page=10).get("videos", []):
            if f"v{v['id']}" in deja or v.get("duration", 0) < 4:
                continue
            fichiers = [f for f in v.get("video_files", []) if f.get("file_type") == "video/mp4"
                        and (f.get("height") or 0) >= 1280 and (f.get("height") or 0) > (f.get("width") or 0)]
            if not fichiers:
                continue
            choisi = min(fichiers, key=lambda f: f["height"])  # le plus léger qui reste net en 1080×1920
            deja.add(f"v{v['id']}")
            return _telecharger(choisi["link"], dossier / f"{nom}.mp4"), True
        for p in _get("/v1/search", query=requete, orientation="portrait", per_page=10).get("photos", []):
            if f"p{p['id']}" in deja:
                continue
            deja.add(f"p{p['id']}")
            return _telecharger(p["src"]["large2x"], dossier / f"{nom}.jpg"), False
    except requests.RequestException:
        return None
    return None
