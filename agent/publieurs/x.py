"""Compte X (ex-Twitter) — API v2, authentification OAuth 1.0a « utilisateur »."""
from __future__ import annotations

import os
import re

import requests
from requests_oauthlib import OAuth1

from ..models import Media, Post
from .base import TIMEOUT, ErreurPublication, Publieur, Resultat, attendre, controler

API = "https://api.x.com/2"
TAILLE_BLOC = 4 * 1024 * 1024
_URL = re.compile(r"https?://\S+")


def longueur_x(texte: str) -> int:
    """Approximation du décompte X : chaque lien compte pour 23 caractères."""
    return len(_URL.sub("x" * 23, texte))


def couper_pour_x(texte: str, limite: int = 280) -> str:
    if longueur_x(texte) <= limite:
        return texte
    mots, sortie = texte.split(), ""
    for mot in mots:
        essai = f"{sortie} {mot}".strip()
        if longueur_x(essai) > limite - 1:
            break
        sortie = essai
    return sortie.rstrip(" ,;:.") + "…"


class X(Publieur):
    nom = "x"
    variables = ("X_API_KEY", "X_API_SECRET", "X_ACCESS_TOKEN", "X_ACCESS_TOKEN_SECRET")

    def __init__(self, cfg: dict):
        super().__init__(cfg)
        self.auth = OAuth1(os.environ.get("X_API_KEY", ""), os.environ.get("X_API_SECRET", ""),
                           os.environ.get("X_ACCESS_TOKEN", ""), os.environ.get("X_ACCESS_TOKEN_SECRET", ""))

    def verifier(self) -> str:
        r = controler(requests.get(f"{API}/users/me", auth=self.auth, timeout=TIMEOUT), "x lecture du compte")
        return "@" + r.json()["data"]["username"]

    def _envoyer(self, media: Media) -> str:
        if media.type == "video":
            categorie = "tweet_video"
        elif media.mime == "image/gif":
            categorie = "tweet_gif"
        else:
            categorie = "tweet_image"
        init = controler(requests.post(f"{API}/media/upload/initialize", auth=self.auth, timeout=TIMEOUT, json={
            "media_type": media.mime, "total_bytes": media.taille, "media_category": categorie,
        }), "x initialisation média").json()
        mid = (init.get("data") or init)["id"]

        with media.chemin.open("rb") as f:
            index = 0
            while bloc := f.read(TAILLE_BLOC):
                controler(requests.post(f"{API}/media/upload/{mid}/append", auth=self.auth, timeout=TIMEOUT,
                                        data={"segment_index": index}, files={"media": ("bloc", bloc)}),
                          "x envoi média")
                index += 1

        fin = controler(requests.post(f"{API}/media/upload/{mid}/finalize", auth=self.auth, timeout=TIMEOUT),
                        "x finalisation média").json()
        if (fin.get("data") or fin).get("processing_info"):
            def termine():
                s = controler(requests.get(f"{API}/media/upload", auth=self.auth, timeout=TIMEOUT,
                                           params={"command": "STATUS", "media_id": mid}), "x statut média").json()
                etat = ((s.get("data") or s).get("processing_info") or {}).get("state")
                if etat == "failed":
                    raise ErreurPublication(f"X n'a pas pu traiter le média {media.nom}")
                return etat in (None, "succeeded")
            attendre(termine, delai_max=600, pas=5, contexte="X traitement média")
        return str(mid)

    def publier(self, post: Post, texte: str) -> Resultat:
        corps: dict = {"text": couper_pour_x(texte)}
        medias = post.videos[:1] or post.images[:4]  # X : 1 vidéo OU jusqu'à 4 images
        if medias:
            corps["media"] = {"media_ids": [self._envoyer(m) for m in medias]}
        r = controler(requests.post(f"{API}/tweets", auth=self.auth, json=corps, timeout=TIMEOUT),
                      "x publication").json()
        tid = r["data"]["id"]
        return Resultat(f"https://x.com/i/web/status/{tid}", tid)
