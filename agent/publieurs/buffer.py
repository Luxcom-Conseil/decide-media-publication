"""X et LinkedIn via Buffer (plan gratuit) : chaque post est déposé dans le planificateur de Buffer, qui publie à l'heure.

Buffer ne reçoit pas de fichier : il va chercher le visuel ou le Short à une adresse publique (voir hebergement.py).
Lot DECIDE MEDIA : les `shorts_par_lot` premiers articles partent en vidéo (le Short YouTube), les suivants en visuel,
dans la limite de `max_par_lot` (file d'attente gratuite : 10 posts par chaîne).
"""
from __future__ import annotations

import os
import re
from datetime import date, timezone
from pathlib import Path

import requests

from ..models import Post
from .base import TIMEOUT, ErreurDefinitive, ErreurPublication, Publieur, Resultat, controler
from .x import couper_pour_x

API = "https://api.buffer.com"
_HEBERGES: dict[Path, str] = {}  # même média pour X et LinkedIn : mis en ligne une seule fois par passage


def requete(query: str, variables: dict | None = None) -> dict:
    r = controler(requests.post(API, json={"query": query, "variables": variables or {}}, timeout=TIMEOUT,
                                headers={"Authorization": f"Bearer {os.environ['BUFFER_API_KEY']}"}), "buffer")
    corps = r.json()
    if corps.get("errors"):
        raise ErreurPublication("buffer : " + "; ".join(e.get("message", "?") for e in corps["errors"])[:500])
    return corps["data"]


def texte_x(article: dict) -> str:
    """Version courte pour X (280 caractères) : titre, phrase d'accroche, deux hashtags."""
    titre = article.get("title", "").strip()
    corps = re.sub(r"\s+", " ", article.get("body") or "").strip()
    tags = " ".join(h if h.startswith("#") else f"#{h}" for h in (article.get("hashtags") or [])[:2])
    fin = f"\n\n{tags}" if tags else ""
    budget = 280 - len(fin) - len(titre) - 2
    accroche = ""
    for phrase in re.split(r"(?<=[.!?])\s", corps):  # phrases entières tant qu'elles tiennent
        if len(f"{accroche} {phrase}".strip()) > budget:
            break
        accroche = f"{accroche} {phrase}".strip()
    return couper_pour_x(f"{titre}\n\n{accroche or corps}", 280 - len(fin)) + fin


class _Buffer(Publieur):
    variables = ("BUFFER_API_KEY",)
    canal = ""  # clé de config.yaml (buffer.canaux)

    def _canal(self) -> str:
        return str(self.cfg["buffer"]["canaux"][self.canal])

    def verifier(self) -> str:
        d = requete("query($id: ChannelId!) { channel(input: {id: $id}) { name service } }", {"id": self._canal()})
        return f"Buffer → {d['channel']['service']} « {d['channel']['name']} »"

    def valider(self, post: Post) -> None:
        raise ErreurDefinitive("Buffer : utilisé seulement pour les lots DECIDE MEDIA")

    def texte(self, article: dict, texte: str) -> str:
        return texte

    def programmer(self, texte: str, image: Path, quand, article: dict | None = None) -> Resultat:
        from ..hebergement import mettre_en_ligne
        from ..scenario import short_en_cache

        article = article or {}
        en_video = article.get("_rang", 99) <= int(self.cfg["buffer"].get("shorts_par_lot", 0))
        media = short_en_cache(article, image) if en_video else image
        nom = f"{article.get('id', 'article')}{media.suffix.lower()}"
        if nom not in _HEBERGES:
            copie = media.with_name(nom)
            if copie != media:
                copie.write_bytes(media.read_bytes())
            jour = date.fromisoformat(article.get("_lot") or quand.date().isoformat())
            _HEBERGES[nom] = mettre_en_ligne([copie], jour)[nom]
        asset = {"video": {"url": _HEBERGES[nom]}} if en_video else {"image": {"url": _HEBERGES[nom]}}
        d = requete("""
            mutation($input: CreatePostInput!) {
              createPost(input: $input) {
                ... on PostActionSuccess { post { id } }
                ... on MutationError { message }
              }
            }""", {"input": {
            "channelId": self._canal(), "text": self.texte(article, texte), "schedulingType": "automatic",
            "mode": "customScheduled", "assets": [asset],
            "dueAt": quand.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.000Z"),
        }})["createPost"]
        if not d.get("post"):
            raise ErreurPublication(f"buffer {self.canal} : {d.get('message', 'refus sans motif')}")
        return Resultat(f"https://publish.buffer.com/channels/{self._canal()}/schedule", d["post"]["id"])

    def trouver_programme(self, texte: str) -> dict | None:
        return None  # le journal (etat/lots.json) suffit : il est enregistré après chaque dépôt


class BufferX(_Buffer):
    nom = canal = "x_buffer"

    def texte(self, article: dict, texte: str) -> str:
        return (article.get("platform_texts") or {}).get("x") or texte_x(article)


class BufferLinkedIn(_Buffer):
    nom = canal = "linkedin_buffer"

    def texte(self, article: dict, texte: str) -> str:
        return (article.get("platform_texts") or {}).get("linkedin") or texte
