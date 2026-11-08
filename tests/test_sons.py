"""Charte sonore (agent/sons.py) : bruitages calés sur les scènes, à partir de la vraie banque de Histoires."""
import json
import shutil
import subprocess
from pathlib import Path

import pytest
import yaml

from agent import sons

RACINE = Path(__file__).resolve().parent.parent
CFG = yaml.safe_load((RACINE / "config.yaml").read_text(encoding="utf-8"))
BANQUE = RACINE / "motion" / "public" / "sons" / "histoires"


def _scenes():
    img = lambda n: {"src": f"_histoires/{n}.jpg", "credit": "x"}
    return [
        {"type": "accroche", "image": img(1), "voix": {"duree": 3.0}},
        {"type": "recit", "image": img(1), "voix": {"duree": 4.0}},    # même image : pas de transition
        {"type": "recit", "image": img(2), "voix": {"duree": 4.0}},    # nouvelle image, 7 s après le début
        {"type": "recit", "image": img(3), "voix": {"duree": 2.0}},    # nouvelle image mais 4 s après le whoosh
        {"type": "date", "grand": "1925", "voix": {"duree": 3.0}},
        {"type": "chiffre", "grand": "2 fois", "voix": {"duree": 3.0}},
        {"type": "recit", "image": img(4), "voix": {"duree": 3.0}},    # 12 s après le premier whoosh
        {"type": "lecon", "voix": {"duree": 3.0}},                     # silence voulu
        {"type": "suite", "voix": {"duree": 3.0}},
        {"type": "signature", "duree": 3.0},
    ]


def test_la_banque_couvre_chaque_moment_de_la_charte():
    b = json.loads((BANQUE / "banque.json").read_text(encoding="utf-8"))
    for moment in CFG["histoires"]["son"]["moments"]:
        prises = b["moments"][moment]
        assert len(prises) == CFG["histoires"]["son"]["prises"]
        for p in prises:
            assert (RACINE / "motion" / "public" / p["src"]).is_file()
            assert 0 <= p["attaque"] <= p["pic"] <= p["duree"]


def test_chaque_moment_recoit_son_son_et_les_transitions_sont_espacees():
    sc = _scenes()
    sons.habiller(CFG, "histoires", sc, cle="Tulipes", journal=lambda *_: None)
    par_type = [(s["type"], Path(s["sons"][0]["src"]).stem.rsplit("_", 1)[0] if s.get("sons") else None) for s in sc]
    assert par_type == [("accroche", "accroche"), ("recit", None), ("recit", "transition"), ("recit", None),
                        ("date", "date"), ("chiffre", "chiffre"), ("recit", "transition"), ("lecon", None),
                        ("suite", "suite"), ("signature", "signature")]
    riser = sc[8]["sons"][0]
    assert riser["avance"] > 2.0            # calé sur son pic : il démarre ~2,2 s avant « À SUIVRE »
    assert 0 < riser["gain"] < 1


def test_meme_video_memes_sons_autre_video_autres_prises():
    a, b, c = _scenes(), _scenes(), _scenes()
    for s, cle in ((a, "Tulipes"), (b, "Tulipes"), (c, "Lustig")):
        sons.habiller(CFG, "histoires", s, cle=cle, journal=lambda *_: None)
    src = lambda s: [x["sons"][0]["src"] for x in s if x.get("sons")]
    assert src(a) == src(b)
    assert src(a) != src(c)


def test_la_rubrique_programme_n_a_ni_boum_ni_cliffhanger_et_joue_plus_bas():
    h, p = _scenes(), _scenes()
    sons.habiller(CFG, "histoires", h, cle="x", journal=lambda *_: None)
    sons.habiller(CFG, "histoires", p, cle="x", format_="programme", journal=lambda *_: None)
    assert not p[0].get("sons") and not p[8].get("sons")
    assert p[4]["sons"][0]["gain"] < h[4]["sons"][0]["gain"]


def test_decide_flash_info_accroche_chiffres_photos_et_logo():
    photo = lambda n: {"src": f"_v3/fond{n}.jpg", "video": False}
    sc = [
        {"type": "accroche", "media": photo(0), "voix": {"duree": 3.0}},
        {"type": "media", "media": photo(1), "voix": {"duree": 4.0}},         # nouvelle photo, 4 s après l'accroche
        {"type": "explication", "illustration": {"type": "pourcent"}, "voix": {"duree": 4.0}},
        {"type": "media", "media": photo(2), "voix": {"duree": 2.0}},         # 6 s après le dernier souffle
        {"type": "explication", "illustration": {"type": "pile"}, "voix": {"duree": 3.0}},
        {"type": "outro", "duree": 3.5},
    ]
    reglages = sons.habiller(CFG, "video", sc, cle="art-1", journal=lambda *_: None)
    roles = [Path(s["sons"][0]["src"]).stem.rsplit("_", 1)[0] if s.get("sons") else None for s in sc]
    assert roles == ["accroche", "transition", "chiffre", "transition", "chiffre", "outro"]
    assert all(s["sons"][0]["src"].startswith("sons/decide/") for s in sc)
    assert reglages == {}                   # la mélodie validée le 21/10 reste la musique de DECIDE


def test_production_sans_charte_ne_change_rien():
    sc = _scenes()
    assert sons.habiller(CFG, "perso", sc, cle="x", journal=lambda *_: None) == {}
    assert not any(s.get("sons") for s in sc)


def test_niveler_ramene_le_mp4_au_volume_de_la_charte(tmp_path):
    import imageio_ffmpeg
    ff = imageio_ffmpeg.get_ffmpeg_exe()
    mp4 = tmp_path / "essai.mp4"
    subprocess.run([ff, "-v", "error", "-y", "-f", "lavfi", "-i", "color=c=black:s=320x568:d=6:r=30",
                    "-f", "lavfi", "-i", "sine=frequency=330:duration=6,volume=0.05", "-shortest",
                    "-c:v", "libx264", "-pix_fmt", "yuv420p", "-c:a", "aac", str(mp4)], check=True)
    avant = sons.mesurer(mp4)
    assert avant["lufs"] < -25
    apres = sons.niveler(CFG, "histoires", mp4, journal=lambda *_: None)
    assert abs(apres["lufs"] - CFG["histoires"]["son"]["volume_final_lufs"]) <= 1.0
    assert apres["pic"] <= -1.0
