"""Mise en ligne des visuels et des Shorts : Buffer exige une adresse web publique et directe pour chaque média.

Les fichiers sont déposés dans la branche « medias » du dépôt, publiée par GitHub Pages :
    https://<compte>.github.io/<depot>/<AAAA-MM-JJ>/<fichier>
La branche est réécrite à chaque dépôt (un seul commit) et ne garde que les derniers jours : le dépôt ne grossit pas.
"""
from __future__ import annotations

import os
import random
import shutil
import subprocess
import time
from datetime import date, timedelta
from pathlib import Path

import requests

RACINE = Path(__file__).resolve().parent.parent
BRANCHE = "medias"
# 1 = la veille et le jour même. Le 10/11/2026, avec 9 vidéos par jour du compte « Histoires vraies d'argent », 4 jours
# faisaient 1,14 Go : au-delà de la limite de 1 Go de GitHub Pages, le déploiement échouait et rien n'était programmé.
# Buffer va chercher la vidéo à l'heure de publication, puis n'en a plus besoin (relance des refus : histoires.relancer).
JOURS_GARDES = 1
JOURS_GARDES_SEMAINE = 10  # Reels Instagram perso produits le dimanche pour toute la semaine


def _git(*args: str, cwd: Path | None = None) -> str:
    r = subprocess.run(["git", *args], cwd=cwd or RACINE, capture_output=True, text=True)
    if r.returncode:
        raise RuntimeError(f"git {' '.join(args[:2])} : {(r.stderr or r.stdout).strip()[-300:]}")
    return r.stdout.strip()


def adresse_site() -> str:
    """https://luxcom-conseil.github.io/decide-media-publication à partir du dépôt git d'origine."""
    url = _git("remote", "get-url", "origin").removesuffix(".git")
    compte, depot = url.rstrip("/").split("/")[-2:]
    return f"https://{compte.lower()}.github.io/{depot}"


def _deposer(fichiers: list[Path], jour: date, nom_dossier: str | None) -> bool:
    """Un essai : repart du dernier état de la branche, ajoute les fichiers et pousse.
    Faux si un autre dépôt est passé entre la lecture et la poussée : rien n'est écrasé, l'essai est à refaire."""
    jeton = f"{os.getpid()}-{int(time.time() * 1000)}"
    dossier = RACINE / ".medias" / jeton  # un dossier et une branche par passage : deux tâches du PC ne se gênent pas
    ref = f"refs/medias-lu/{jeton}"
    branche = f"{BRANCHE}-publie-{jeton}"
    existe = subprocess.run(["git", "fetch", "-q", "origin", f"+refs/heads/{BRANCHE}:{ref}"], cwd=RACINE,
                            capture_output=True).returncode == 0
    lu = _git("rev-parse", ref) if existe else ""  # l'état de la branche sur lequel ce dépôt s'appuie
    dossier.parent.mkdir(exist_ok=True)
    _git("worktree", "add", "-q", "--detach", str(dossier), ref if existe else "HEAD")
    try:
        _git("checkout", "-q", "--orphan", branche, cwd=dossier)
        if not existe:
            _git("rm", "-rqf", "--ignore-unmatch", ".", cwd=dossier)
        # jamais au-delà d'aujourd'hui (Paris) : DECIDE dépose déjà le 26/11 le 24/11, ce qui effaçait les vidéos du jour
        # avant que Buffer ne vienne les chercher (dossier 2026-11-24 absent le 24/11/2026 à midi)
        from datetime import datetime
        from zoneinfo import ZoneInfo
        limite = min(jour - timedelta(days=JOURS_GARDES), datetime.now(ZoneInfo("Europe/Paris")).date())
        limite_semaine = jour - timedelta(days=JOURS_GARDES_SEMAINE)
        for sous in dossier.iterdir():  # on ne garde que les derniers jours
            if sous.is_dir() and sous.name[:4].isdigit() and sous.name < limite.isoformat():
                shutil.rmtree(sous)
            elif sous.is_dir() and sous.name.startswith("perso-") and sous.name[6:] < limite_semaine.isoformat():
                shutil.rmtree(sous)
        (dossier / ".nojekyll").touch()
        cible = dossier / (nom_dossier or jour.isoformat())
        cible.mkdir(exist_ok=True)
        for f in fichiers:
            shutil.copy(f, cible / f.name)
        _git("add", "-A", cwd=dossier)
        _git("-c", "user.name=agent-publication", "-c", "user.email=agent-publication@users.noreply.github.com",
             "commit", "-q", "--allow-empty", "-m", f"médias du {jour.isoformat()}", cwd=dossier)
        # Le commit est réécrit (un seul commit : la branche ne grossit pas), mais la poussée n'est acceptée que si la
        # branche est encore celle qu'on a lue. Le 24/11/2026, des dépôts simultanés s'écrasaient : 3 vidéos du
        # discours présidentiel ont disparu de l'hébergement avant leur heure de publication.
        r = subprocess.run(["git", "push", "-q", f"--force-with-lease=refs/heads/{BRANCHE}:{lu}", "origin",
                            f"HEAD:refs/heads/{BRANCHE}"], cwd=dossier, capture_output=True, text=True)
        if r.returncode == 0:
            return True
        message = (r.stderr or r.stdout).strip()
        if any(m in message for m in ("stale info", "rejected", "fetch first", "non-fast-forward")):
            return False
        raise RuntimeError(f"git push : {message[-300:]}")
    finally:
        subprocess.run(["git", "worktree", "remove", "--force", str(dossier)], cwd=RACINE, capture_output=True)
        shutil.rmtree(dossier, ignore_errors=True)
        subprocess.run(["git", "branch", "-D", branche], cwd=RACINE, capture_output=True)
        subprocess.run(["git", "update-ref", "-d", ref], cwd=RACINE, capture_output=True)


def _nettoyer_restes() -> None:
    """Dossiers de travail laissés par un passage interrompu (plus d'une heure), et l'ancien dossier unique."""
    racine = RACINE / ".medias"
    if (racine / ".git").exists():  # ancienne version : .medias était lui-même le dossier de travail
        subprocess.run(["git", "worktree", "remove", "--force", str(racine)], cwd=RACINE, capture_output=True)
        shutil.rmtree(racine, ignore_errors=True)
        subprocess.run(["git", "branch", "-D", f"{BRANCHE}-publie"], cwd=RACINE, capture_output=True)
    if racine.is_dir():
        for d in racine.iterdir():
            if d.is_dir() and time.time() - d.stat().st_mtime > 3600:
                subprocess.run(["git", "worktree", "remove", "--force", str(d)], cwd=RACINE, capture_output=True)
                shutil.rmtree(d, ignore_errors=True)
    subprocess.run(["git", "worktree", "prune"], cwd=RACINE, capture_output=True)


def mettre_en_ligne(fichiers: list[Path], jour: date, attente_max: int = 300, nom_dossier: str | None = None,
                    essais: int = 8) -> dict[str, str]:
    """Dépose les fichiers (nom → adresse publique) et attend que GitHub Pages les serve.
    `nom_dossier` (ex. « perso-2026-10-27 », Reels Instagram de la semaine) : gardé JOURS_GARDES_SEMAINE jours.
    Plusieurs tâches peuvent déposer en même temps (antennes, lots, PC et GitHub Actions) : chaque dépôt repart du
    dernier état de la branche, et recommence si un autre est passé entre la lecture et la poussée."""
    _nettoyer_restes()
    for n in range(essais):
        if _deposer(fichiers, jour, nom_dossier):
            break
        time.sleep(3 + random.uniform(0, 4) * (n + 1))  # un autre dépôt vient de passer : on relit et on refait
    else:
        raise RuntimeError(f"médias non déposés : la branche {BRANCHE} a changé à chacun des {essais} essais")

    base = adresse_site()
    urls = {f.name: f"{base}/{nom_dossier or jour.isoformat()}/{f.name}" for f in fichiers}
    fin = time.time() + attente_max
    for url in urls.values():  # GitHub Pages met environ une minute à publier
        while True:
            try:
                if requests.head(url, timeout=20, allow_redirects=False).status_code == 200:
                    break
            except requests.RequestException:
                pass
            if time.time() > fin:
                raise RuntimeError(f"média pas encore en ligne après {attente_max} s : {url}")
            time.sleep(10)
    return urls
