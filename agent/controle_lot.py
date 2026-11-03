"""Alerte « pas de lot aujourd'hui » : python -m agent.controle_lot [--forcer] [--simulation]

Le rattrapage étant coupé, un jour sans lot publiable ne publie rien. Ce contrôle ouvre alors une issue GitHub,
attribuée au propriétaire du dépôt, ce qui lui envoie un e-mail. Une seule issue par jour, même si plusieurs passages
constatent le problème ; si le lot arrive plus tard, l'issue est refermée et le message le dit.
"""
from __future__ import annotations

import argparse
import json
import os
import sys
from datetime import date, datetime, time
from zoneinfo import ZoneInfo

import requests

from .config import charger_config
from .lots import LotInvalide, controler_manifeste
from .sources import SourceDrive

# Le premier passage part à 6 h 45 (cron-job.org) ; les crons GitHub, eux, arrivent parfois à n'importe quelle heure.
# Avant cette heure, le producteur (4 h 07) peut encore être en train de travailler : pas d'alerte.
HEURE_ALERTE = time(6, 40)


def diagnostiquer(drive, jour: date) -> str | None:
    """Pourquoi rien ne sera publié ce jour-là ; None si le lot du jour est publiable."""
    nom = jour.isoformat()
    dossier = next((d for d in drive.lister_dossiers() if d.nom == nom), None)
    if dossier is None:
        return f"Aucun dossier « {nom} » sur le Drive : le producteur n'a rien déposé."
    fichiers = {f.nom: f for f in drive.lister_fichiers(dossier)}
    if "manifest.json" not in fichiers:
        return f"Le dossier « {nom} » existe, mais son manifest.json n'a pas été déposé."
    try:
        manifeste = json.loads(drive.lire_brut(fichiers["manifest.json"]).decode("utf-8-sig"))
        if manifeste.get("status") == "failed":
            causes = " ; ".join(str(c) for c in manifeste.get("issues") or []) or "aucune cause indiquée"
            return f"Le producteur a déclaré le lot en échec. Cause : {causes}"
        controler_manifeste(manifeste, nom)
    except (LotInvalide, ValueError, AttributeError) as e:
        return f"Le lot est refusé par les contrôles : {e}"
    return None


class Issues:
    """Le peu de l'API GitHub dont l'alerte a besoin, avec le jeton fourni par le workflow."""

    def __init__(self, depot: str, proprietaire: str, jeton: str):
        self.url = f"https://api.github.com/repos/{depot}/issues"
        self.proprietaire = proprietaire
        self.entetes = {"Authorization": f"Bearer {jeton}", "Accept": "application/vnd.github+json"}

    def _appel(self, methode: str, url: str, **kw):
        r = requests.request(methode, url, headers=self.entetes, timeout=30, **kw)
        r.raise_for_status()
        return r.json()

    def trouver(self, titre: str) -> dict | None:
        # state=all : une issue refermée à la main ne doit pas revenir au passage suivant
        for issue in self._appel("GET", self.url, params={"state": "all", "per_page": 100}):
            if issue["title"] == titre:
                return issue
        return None

    def ouvrir(self, titre: str, corps: str) -> dict:
        return self._appel("POST", self.url, json={"title": titre, "body": corps, "assignees": [self.proprietaire]})

    def refermer(self, numero: int, message: str) -> None:
        self._appel("POST", f"{self.url}/{numero}/comments", json={"body": message})
        self._appel("PATCH", f"{self.url}/{numero}", json={"state": "closed", "state_reason": "completed"})


def titre_alerte(jour: date) -> str:
    return f"DECIDE MEDIA : pas de lot publiable le {jour.strftime('%d/%m/%Y')}"


def corps_alerte(raison: str) -> str:
    return ("**Tant que ce problème dure, aucun article DECIDE MEDIA ne part aujourd'hui.**\n\n"
            f"```\n{raison[:1500]}\n```\n\n"
            "Rien n'est à faire si le lot arrive plus tard : les passages de la matinée le reprendront "
            "et cette alerte se refermera toute seule. Sinon, la journée reste sans publication.")


def controler(drive, issues, jour: date, log, *, simulation: bool = False) -> None:
    raison = diagnostiquer(drive, jour)
    titre = titre_alerte(jour)
    if simulation:
        log(f"[simulation] {raison or 'lot du jour publiable'}")
        return
    existante = issues.trouver(titre)
    if raison:
        log(f"⚠️ {raison}")
        if existante:
            log(f"Alerte déjà envoyée : {existante['html_url']}")
        else:
            log(f"Alerte envoyée : {issues.ouvrir(titre, corps_alerte(raison))['html_url']}")
        return
    log(f"✅ Lot du {jour.isoformat()} publiable")
    if existante and existante["state"] == "open":
        issues.refermer(existante["number"], "Le lot est arrivé : la publication reprend.")
        log(f"Alerte refermée : {existante['html_url']}")


def main(argv: list[str] | None = None) -> int:
    for flux in (sys.stdout, sys.stderr):  # emojis lisibles même dans une console Windows
        if hasattr(flux, "reconfigure"):
            flux.reconfigure(encoding="utf-8")
    p = argparse.ArgumentParser(prog="agent.controle_lot", description="Alerte si le lot du jour n'est pas publiable.")
    p.add_argument("--forcer", action="store_true", help="contrôler même avant l'heure d'alerte")
    p.add_argument("--simulation", action="store_true", help="dire ce qui serait signalé, sans ouvrir d'issue")
    p.add_argument("--config", default="config.yaml")
    a = p.parse_args(argv)

    cfg = charger_config(a.config)
    maintenant = datetime.now(ZoneInfo(cfg["fuseau_horaire"]))
    lignes: list[str] = []

    def log(texte: str) -> None:
        print(texte)
        lignes.append(texte)

    if not a.forcer and maintenant.time() < HEURE_ALERTE:
        log(f"{maintenant:%H:%M} : avant l'heure d'alerte, pas de contrôle.")
    else:
        os.environ.setdefault("DRIVE_FOLDER_ID", cfg["lots"]["dossier_drive"])
        simulation = a.simulation or os.environ.get("SIMULATION", "").lower() in ("1", "true", "oui")
        issues = None if simulation else Issues(os.environ["GITHUB_REPOSITORY"], os.environ["GITHUB_REPOSITORY_OWNER"],
                                                os.environ["GITHUB_TOKEN"])
        controler(SourceDrive.depuis_env(), issues, maintenant.date(), log, simulation=simulation)

    chemin = os.environ.get("GITHUB_STEP_SUMMARY")
    if chemin:
        with open(chemin, "a", encoding="utf-8") as f:
            f.write("## Contrôle du lot du jour\n\n```\n" + "\n".join(lignes) + "\n```\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())
