"""Chargement de config.yaml (réglages non secrets). Les secrets viennent des variables d'environnement."""
from __future__ import annotations

import copy
from pathlib import Path

import yaml

DEFAUTS = {
    "fuseau_horaire": "Europe/Paris",
    "retard_max_heures": 24,
    "tentatives_max": 3,
    "fichiers_post": ["post.txt", "post.md", "post"],
    "ia": {
        "active": True,
        "modele": "claude-opus-5-5",
        "effort": "medium",
        "marque": "",
        "ton": "Professionnel et chaleureux.",
        "consignes": "",
        "hashtags_max": {"facebook": 3, "instagram": 8, "linkedin": 4, "x": 2},
    },
    "meta": {"version_api": "v25.0"},
    "linkedin": {"version_api": "202608"},
    "youtube": {"visibilite_defaut": "public", "categorie": "22"},
    "lots": {
        "dossier_drive": "1T_1QBeDbS1GIgHY2UsZsNnN3wJu5Cmwa",  # Article DECIDE MEDIA - Quotidien
        "reseaux": ["facebook"],
        "jours_max": 0,  # 0 = uniquement le lot du jour ; 1 = aussi celui de la veille s'il n'a pas été programmé
        "fuseau_creneaux": "Africa/Douala",
        "creneaux": ["07:00", "08:30", "10:00", "11:30", "13:00", "14:30", "16:00", "17:30", "19:00", "20:30"],
        "marge_minutes": 20,  # Facebook exige au moins 10 min entre la programmation et la publication
        "ecart_minimum_minutes": 45,  # si des créneaux sont passés, les articles sont espacés d'au moins 45 min
    },
}


def _fusion(base: dict, ajout: dict) -> dict:
    out = copy.deepcopy(base)
    for k, v in (ajout or {}).items():
        out[k] = _fusion(out[k], v) if isinstance(v, dict) and isinstance(out.get(k), dict) else v
    return out


def charger_config(chemin: str | Path = "config.yaml") -> dict:
    p = Path(chemin)
    if not p.exists():
        return copy.deepcopy(DEFAUTS)
    with p.open(encoding="utf-8") as f:
        return _fusion(DEFAUTS, yaml.safe_load(f) or {})
