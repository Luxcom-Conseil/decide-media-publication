from .base import ErreurDefinitive, ErreurPublication, Publieur, Resultat
from .buffer import BufferLinkedIn, BufferTikTok, BufferX
from .linkedin import LinkedIn
from .meta import Facebook, FacebookShorts, Instagram
from .x import X
from .youtube import YouTube

TOUS: dict[str, type[Publieur]] = {
    "facebook": Facebook,
    "facebook_shorts": FacebookShorts,
    "instagram": Instagram,
    "linkedin": LinkedIn,
    "x": X,
    "youtube": YouTube,
    "x_buffer": BufferX,
    "linkedin_buffer": BufferLinkedIn,
    "tiktok_buffer": BufferTikTok,
}

__all__ = ["TOUS", "ErreurDefinitive", "ErreurPublication", "Publieur", "Resultat"]
