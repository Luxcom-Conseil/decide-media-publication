"""Mise en ligne des visuels et des Shorts : Buffer exige une adresse web publique et directe pour chaque média.

Les fichiers sont déposés dans la branche « medias » du dépôt, publiée par GitHub Pages :
    https://<compte>.github.io/<depot>/<AAAA-MM-JJ>/<fichier>
La branche est réécrite à chaque dépôt (un seul commit) et ne garde que les derniers jours : le dépôt ne grossit pas.
"""
from __future__ import annotations

import shutil
import subprocess
import time
from datetime import date, timedelta
from pathlib import Path

import requests

RACINE = Path(__file__).resolve().parent.parent
BRANCHE = "medias"
JOURS_GARDES = 3


def _git(*args: str, cwd: Path = RACINE) -> str:
    r = subprocess.run(["git", *args], cwd=cwd, capture_output=True, text=True)
    if r.returncode:
        raise RuntimeError(f"git {' '.join(args[:2])} : {(r.stderr or r.stdout).strip()[-300:]}")
    return r.stdout.strip()


def adresse_site() -> str:
    """https://luxcom-conseil.github.io/decide-media-publication à partir du dépôt git d'origine."""
    url = _git("remote", "get-url", "origin").removesuffix(".git")
    compte, depot = url.rstrip("/").split("/")[-2:]
    return f"https://{compte.lower()}.github.io/{depot}"


def mettre_en_ligne(fichiers: list[Path], jour: date, attente_max: int = 300) -> dict[str, str]:
    """Dépose les fichiers (nom → adresse publique) et attend que GitHub Pages les serve."""
    dossier = RACINE / ".medias"
    if dossier.exists():
        subprocess.run(["git", "worktree", "remove", "--force", str(dossier)], cwd=RACINE, capture_output=True)
        shutil.rmtree(dossier, ignore_errors=True)
    subprocess.run(["git", "branch", "-D", f"{BRANCHE}-publie"], cwd=RACINE, capture_output=True)  # passage précédent
    existe = subprocess.run(["git", "fetch", "-q", "origin", BRANCHE], cwd=RACINE, capture_output=True).returncode == 0
    _git("worktree", "add", "-q", "--detach", str(dossier), "FETCH_HEAD" if existe else "HEAD")
    try:
        _git("checkout", "-q", "--orphan", f"{BRANCHE}-publie", cwd=dossier)
        if not existe:
            _git("rm", "-rqf", ".", cwd=dossier)
        limite = jour - timedelta(days=JOURS_GARDES)
        for sous in dossier.iterdir():  # on ne garde que les derniers jours
            if sous.is_dir() and sous.name[:4].isdigit() and sous.name < limite.isoformat():
                shutil.rmtree(sous)
        (dossier / ".nojekyll").touch()
        cible = dossier / jour.isoformat()
        cible.mkdir(exist_ok=True)
        for f in fichiers:
            shutil.copy(f, cible / f.name)
        _git("add", "-A", cwd=dossier)
        _git("-c", "user.name=agent-publication", "-c", "user.email=agent-publication@users.noreply.github.com",
             "commit", "-q", "--allow-empty", "-m", f"médias du {jour.isoformat()}", cwd=dossier)
        _git("push", "-q", "-f", "origin", f"HEAD:{BRANCHE}", cwd=dossier)
    finally:
        subprocess.run(["git", "worktree", "remove", "--force", str(dossier)], cwd=RACINE, capture_output=True)

    base = adresse_site()
    urls = {f.name: f"{base}/{jour.isoformat()}/{f.name}" for f in fichiers}
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
