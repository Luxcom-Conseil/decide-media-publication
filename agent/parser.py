"""Lecture du fichier « post » écrit par l'utilisateur.

Format :

    date: 20/10/2026 09:30
    reseaux: facebook, linkedin, instagram, x, youtube
    titre: Titre de la vidéo YouTube
    ---
    Texte commun à tous les réseaux.

    [x]
    Version courte écrite à la main pour X (facultatif).
"""
from __future__ import annotations

import re
import unicodedata
from datetime import datetime
from zoneinfo import ZoneInfo

from .models import RESEAUX, Post


class ErreurFormat(ValueError):
    pass


ALIAS_RESEAUX = {
    "facebook": "facebook", "fb": "facebook",
    "instagram": "instagram", "insta": "instagram", "ig": "instagram",
    "linkedin": "linkedin",
    "x": "x", "twitter": "x",
    "youtube": "youtube", "yt": "youtube",
}

OUI = {"oui", "o", "yes", "y", "true", "1", "vrai"}
NON = {"non", "n", "no", "false", "0", "faux"}

_RE_SECTION = re.compile(r"^\s*\[\s*([a-zA-Z]+)\s*\]\s*$")
_RE_DATE = re.compile(
    r"^(?:(\d{4})-(\d{1,2})-(\d{1,2})|(\d{1,2})/(\d{1,2})/(\d{4}))"
    r"(?:[ T]+(\d{1,2})\s*[:hH]\s*(\d{2})?)?$"
)


def _normaliser_cle(cle: str) -> str:
    sans_accents = unicodedata.normalize("NFKD", cle).encode("ascii", "ignore").decode()
    return sans_accents.strip().lower().replace(" ", "_").replace("-", "_")


def _reseau(nom: str) -> str:
    r = ALIAS_RESEAUX.get(_normaliser_cle(nom))
    if not r:
        raise ErreurFormat(f"réseau inconnu « {nom} » (valeurs possibles : {', '.join(RESEAUX)})")
    return r


def parser_date(valeur: str, fuseau: str) -> datetime | None:
    v = valeur.strip()
    if v.lower() in {"", "maintenant", "now", "asap", "des_que_possible", "dès que possible"}:
        return None
    m = _RE_DATE.match(v)
    if not m:
        raise ErreurFormat(f"date illisible « {valeur} » (exemple attendu : 20/10/2026 09:30)")
    if m.group(1):
        annee, mois, jour = int(m.group(1)), int(m.group(2)), int(m.group(3))
    else:
        jour, mois, annee = int(m.group(4)), int(m.group(5)), int(m.group(6))
    heure = int(m.group(7) or 9)  # sans heure : 9h00 par défaut
    minute = int(m.group(8) or 0)
    try:
        return datetime(annee, mois, jour, heure, minute, tzinfo=ZoneInfo(fuseau))
    except ValueError as e:
        raise ErreurFormat(f"date invalide « {valeur} » : {e}") from None


def _liste(valeur: str) -> list[str]:
    return [p.strip() for p in re.split(r"[,;]", valeur) if p.strip()]


def parser_post(contenu: str, fuseau: str = "Europe/Paris") -> Post:
    contenu = contenu.replace("﻿", "").replace("\r\n", "\n").replace("\r", "\n")
    lignes = contenu.split("\n")

    try:
        sep = next(i for i, l in enumerate(lignes) if l.strip() == "---")
    except StopIteration:
        raise ErreurFormat("ligne « --- » manquante entre l'en-tête (date, réseaux…) et le texte") from None

    entete: dict[str, str] = {}
    for n, ligne in enumerate(lignes[:sep], start=1):
        if not ligne.strip() or ligne.lstrip().startswith("#"):
            continue
        if ":" not in ligne:
            raise ErreurFormat(f"ligne {n} de l'en-tête sans « : » → « {ligne.strip()} »")
        cle, valeur = ligne.split(":", 1)
        entete[_normaliser_cle(cle)] = valeur.strip()

    # Corps : texte commun puis sections [reseau] facultatives
    textes: dict[str, list[str]] = {"": []}
    courant = ""
    for ligne in lignes[sep + 1:]:
        m = _RE_SECTION.match(ligne)
        if m and _normaliser_cle(m.group(1)) in ALIAS_RESEAUX:
            courant = _reseau(m.group(1))
            textes[courant] = []
            continue
        textes[courant].append(ligne)
    corps = {k: "\n".join(v).strip() for k, v in textes.items()}

    if "reseaux" not in entete:
        raise ErreurFormat("champ « reseaux: » manquant (ex. reseaux: facebook, linkedin)")
    reseaux = []
    for nom in _liste(entete["reseaux"]):
        if nom.lower() in {"tous", "all"}:
            reseaux = list(RESEAUX)
            break
        r = _reseau(nom)
        if r not in reseaux:
            reseaux.append(r)
    if not reseaux:
        raise ErreurFormat("aucun réseau indiqué dans « reseaux: »")

    texte = corps.pop("")
    if not texte and not corps:
        raise ErreurFormat("le texte de la publication est vide")

    ia_val = entete.get("ia", "oui").lower()
    if ia_val not in OUI | NON:
        raise ErreurFormat(f"« ia: {ia_val} » — mettre oui ou non")

    visibilite = entete.get("youtube_visibilite", "").lower()
    visibilite = {"publique": "public", "privee": "private", "privée": "private",
                  "non_repertoriee": "unlisted", "non répertoriée": "unlisted"}.get(visibilite, visibilite)
    if visibilite and visibilite not in {"public", "private", "unlisted"}:
        raise ErreurFormat("youtube_visibilite : public, unlisted ou private")

    return Post(
        date=parser_date(entete.get("date", ""), fuseau),
        reseaux=reseaux,
        texte=texte,
        textes={k: v for k, v in corps.items() if v},
        titre=entete.get("titre", ""),
        tags=[t.lstrip("#") for t in _liste(entete.get("tags", ""))],
        ia=ia_val in OUI,
        youtube_visibilite=visibilite,
    )
