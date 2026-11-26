from .base import ErreurDefinitive, ErreurPublication, Publieur, Resultat
from .buffer import BufferLinkedIn, BufferTikTok, BufferX, BufferYouTube
from .linkedin import LinkedIn
from .meta import Facebook, FacebookShorts, Instagram
from .x import X
from .youtube import YouTube, YouTubeAfrique, YouTubeBenin, YouTubeBurkina

TOUS: dict[str, type[Publieur]] = {
    "facebook": Facebook,
    "facebook_shorts": FacebookShorts,
    "instagram": Instagram,
    "linkedin": LinkedIn,
    "x": X,
    "youtube": YouTube,
    "youtube_bf": YouTubeBurkina,  # antenne Burkina, API directe
    "youtube_af": YouTubeAfrique,  # antenne Afrique, API directe (après autorisation)
    "youtube_bj": YouTubeBenin,  # antenne Bénin, API directe (27/11/2026)
    "x_buffer": BufferX,
    "linkedin_buffer": BufferLinkedIn,
    "tiktok_buffer": BufferTikTok,
    "youtube_buffer": BufferYouTube,  # antennes (YouTube par Buffer)
}

__all__ = ["TOUS", "ErreurDefinitive", "ErreurPublication", "Publieur", "Resultat"]
