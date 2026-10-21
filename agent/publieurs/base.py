from __future__ import annotations

import os
import time
from dataclasses import dataclass

import requests

from ..models import Post

TIMEOUT = (15, 300)  # (connexion, lecture) en secondes


class ErreurPublication(Exception):
    """Échec ponctuel : l'agent réessaiera au prochain passage."""


class ErreurDefinitive(ErreurPublication):
    """Échec qui ne se réglera pas tout seul (ex. Instagram sans visuel) : pas de nouvel essai."""


@dataclass
class Resultat:
    url: str
    id: str = ""


class Publieur:
    nom = ""
    variables: tuple[str, ...] = ()  # secrets requis

    def __init__(self, cfg: dict):
        self.cfg = cfg

    @classmethod
    def manquantes(cls) -> list[str]:
        return [v for v in cls.variables if not os.environ.get(v)]

    @classmethod
    def est_configure(cls) -> bool:
        return not cls.manquantes()

    def verifier(self) -> str:
        """Teste les accès sans rien publier ; renvoie le nom du compte."""
        raise NotImplementedError

    def valider(self, post: Post) -> None:
        """Lève ErreurDefinitive si le post ne peut pas aller sur ce réseau."""

    def publier(self, post: Post, texte: str) -> Resultat:
        raise NotImplementedError


def controler(r: requests.Response, contexte: str) -> requests.Response:
    if r.status_code >= 400:
        corps = r.text[:600].replace("\n", " ")
        if r.status_code in (401, 403):
            raise ErreurPublication(f"{contexte} : accès refusé (HTTP {r.status_code}) — jeton expiré "
                                    f"ou permission manquante. Détail : {corps}")
        raise ErreurPublication(f"{contexte} : HTTP {r.status_code} — {corps}")
    return r


def attendre(condition, *, delai_max: int, pas: int = 5, contexte: str):
    """Rappelle condition() jusqu'à ce qu'elle renvoie une valeur non nulle."""
    fin = time.monotonic() + delai_max
    while time.monotonic() < fin:
        v = condition()
        if v:
            return v
        time.sleep(pas)
    raise ErreurPublication(f"{contexte} : délai de traitement dépassé ({delai_max} s)")
