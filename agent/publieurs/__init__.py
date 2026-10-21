from .base import ErreurDefinitive, ErreurPublication, Publieur, Resultat
from .linkedin import LinkedIn
from .meta import Facebook, Instagram
from .x import X
from .youtube import YouTube

TOUS: dict[str, type[Publieur]] = {
    "facebook": Facebook,
    "instagram": Instagram,
    "linkedin": LinkedIn,
    "x": X,
    "youtube": YouTube,
}

__all__ = ["TOUS", "ErreurDefinitive", "ErreurPublication", "Publieur", "Resultat"]
