"""Structures de données partagées par tout l'agent."""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path

RESEAUX = ("facebook", "instagram", "linkedin", "x", "youtube")

EXT_IMAGES = {".jpg", ".jpeg", ".png", ".webp", ".gif"}
EXT_VIDEOS = {".mp4", ".mov", ".m4v", ".webm"}
NOMS_MINIATURE = {"miniature", "thumbnail"}

MIME = {
    ".jpg": "image/jpeg", ".jpeg": "image/jpeg", ".png": "image/png",
    ".webp": "image/webp", ".gif": "image/gif",
    ".mp4": "video/mp4", ".mov": "video/quicktime", ".m4v": "video/mp4", ".webm": "video/webm",
}


@dataclass
class Media:
    nom: str
    chemin: Path
    type: str  # "image" | "video"

    @property
    def mime(self) -> str:
        return MIME.get(self.chemin.suffix.lower(), "application/octet-stream")

    @property
    def taille(self) -> int:
        return self.chemin.stat().st_size


@dataclass
class Post:
    """Une publication, telle que décrite dans le fichier « post » d'un dossier Drive."""

    date: datetime | None  # None = publier dès que possible
    reseaux: list[str]
    texte: str
    textes: dict[str, str] = field(default_factory=dict)  # versions écrites à la main par réseau
    titre: str = ""  # titre YouTube
    tags: list[str] = field(default_factory=list)
    ia: bool = True
    youtube_visibilite: str = ""
    medias: list[Media] = field(default_factory=list)
    miniature: Path | None = None

    @property
    def images(self) -> list[Media]:
        return [m for m in self.medias if m.type == "image"]

    @property
    def videos(self) -> list[Media]:
        return [m for m in self.medias if m.type == "video"]


def type_media(nom: str) -> str | None:
    ext = Path(nom).suffix.lower()
    if ext in EXT_IMAGES:
        return "image"
    if ext in EXT_VIDEOS:
        return "video"
    return None


def est_miniature(nom: str) -> bool:
    return Path(nom).stem.lower() in NOMS_MINIATURE and type_media(nom) == "image"
