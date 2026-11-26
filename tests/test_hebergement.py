"""Hébergement des médias : deux dépôts simultanés ne doivent jamais s'effacer (incident du 24/11/2026)."""
import subprocess
from datetime import date
from pathlib import Path

import pytest

from agent import hebergement as h


def git(cwd, *args):
    return subprocess.run(["git", *args], cwd=cwd, capture_output=True, text=True, check=True).stdout.strip()


@pytest.fixture
def depot(tmp_path, monkeypatch):
    """Un dépôt d'origine nu et deux clones : deux machines (PC et GitHub Actions) qui déposent sur la même branche."""
    origine = tmp_path / "origine.git"
    git(tmp_path, "init", "-q", "--bare", str(origine))
    clones = []
    for nom in ("pc", "actions"):
        c = tmp_path / nom
        git(tmp_path, "clone", "-q", str(origine), str(c))
        git(c, "-c", "user.name=t", "-c", "user.email=t@t", "commit", "-q", "--allow-empty", "-m", "init")
        clones.append(c)
    monkeypatch.setattr(h.time, "sleep", lambda s: None)
    return origine, clones


def fichier(tmp_path, nom):
    f = tmp_path / nom
    f.write_bytes(nom.encode())
    return f


def contenu(origine):
    return set(git(origine, "ls-tree", "-r", "--name-only", "medias").splitlines())


def deposer(monkeypatch, clone, fichiers, jour, nom_dossier=None):
    monkeypatch.setattr(h, "RACINE", clone)
    ok = h._deposer(fichiers, jour, nom_dossier)
    return ok


def test_depots_successifs_gardent_tout(depot, tmp_path, monkeypatch):
    origine, (pc, actions) = depot
    jour = date(2026, 11, 24)
    assert deposer(monkeypatch, pc, [fichier(tmp_path, "a.mp4")], jour)
    assert deposer(monkeypatch, actions, [fichier(tmp_path, "b.mp4")], jour, "2026-11-24-discours")
    assert {"2026-11-24/a.mp4", "2026-11-24-discours/b.mp4"} <= contenu(origine)
    assert not list((pc / ".medias").iterdir()) and not list((actions / ".medias").iterdir())


def test_depot_concurrent_refuse_puis_refait_sans_rien_effacer(depot, tmp_path, monkeypatch):
    """A lit la branche ; B dépose pendant que A prépare son commit ; la poussée de A est refusée, A relit et refait."""
    origine, (pc, actions) = depot
    jour = date(2026, 11, 24)
    assert deposer(monkeypatch, pc, [fichier(tmp_path, "depart.mp4")], jour)

    vrai_git = h._git
    intrus = {"fait": False}

    def git_avec_intrus(*args, cwd=None):
        if "commit" in args and not intrus["fait"]:  # B passe juste avant la poussée de A
            intrus["fait"] = True
            h.RACINE = actions
            assert h._deposer([fichier(tmp_path, "b.mp4")], jour, "2026-11-24-discours")
            h.RACINE = pc
        return vrai_git(*args, cwd=cwd) if cwd is not None else vrai_git(*args)

    monkeypatch.setattr(h, "RACINE", pc)
    monkeypatch.setattr(h, "_git", git_avec_intrus)
    monkeypatch.setattr(h, "adresse_site", lambda: "https://exemple")
    monkeypatch.setattr(h.requests, "head", lambda *a, **k: type("R", (), {"status_code": 200})())
    urls = h.mettre_en_ligne([fichier(tmp_path, "a.mp4")], jour)

    assert intrus["fait"]
    assert urls == {"a.mp4": "https://exemple/2026-11-24/a.mp4"}
    assert {"2026-11-24/depart.mp4", "2026-11-24/a.mp4", "2026-11-24-discours/b.mp4"} <= contenu(origine)
    assert len(git(origine, "rev-list", "medias").splitlines()) == 1  # toujours un seul commit


def test_anciens_jours_toujours_retires(depot, tmp_path, monkeypatch):
    origine, (pc, _) = depot
    assert deposer(monkeypatch, pc, [fichier(tmp_path, "vieux.mp4")], date(2026, 11, 20))
    assert deposer(monkeypatch, pc, [fichier(tmp_path, "neuf.mp4")], date(2026, 11, 24))
    assert contenu(origine) == {".nojekyll", "2026-11-24/neuf.mp4"}
