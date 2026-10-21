"""Mémoire de l'agent : ce qui a déjà été publié, sur quel réseau, avec combien d'essais.

Stockée dans etat/etat.json, recommitée dans le dépôt par le workflow GitHub après chaque passage.
C'est elle qui garantit qu'un post n'est jamais publié deux fois.
"""
from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path


class Etat:
    def __init__(self, chemin: str | Path = "etat/etat.json"):
        self.chemin = Path(chemin)
        self.donnees: dict = {}
        if self.chemin.exists():
            self.donnees = json.loads(self.chemin.read_text(encoding="utf-8") or "{}")

    def post(self, dossier_id: str, nom: str) -> dict:
        e = self.donnees.setdefault(dossier_id, {"nom": nom, "reseaux": {}, "termine": False})
        e["nom"] = nom
        return e

    def est_termine(self, dossier_id: str) -> bool:
        return bool(self.donnees.get(dossier_id, {}).get("termine"))

    def noter(self, dossier_id: str, reseau: str, *, ok: bool, url: str = "", erreur: str = "",
              definitif: bool = False, tentatives_max: int = 3) -> None:
        r = self.donnees[dossier_id]["reseaux"].setdefault(reseau, {"tentatives": 0})
        r["tentatives"] += 1
        if definitif:
            r["tentatives"] = max(r["tentatives"], tentatives_max)
        r["statut"] = "ok" if ok else "echec"
        r["url"] = url
        r["erreur"] = erreur[:1000]
        r["date"] = datetime.now(timezone.utc).isoformat(timespec="seconds")

    def sauver(self) -> None:
        self.chemin.parent.mkdir(parents=True, exist_ok=True)
        tmp = self.chemin.with_suffix(".tmp")
        tmp.write_text(json.dumps(self.donnees, ensure_ascii=False, indent=2, sort_keys=True), encoding="utf-8")
        tmp.replace(self.chemin)
