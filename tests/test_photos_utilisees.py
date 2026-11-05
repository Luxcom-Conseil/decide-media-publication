import json

from agent.lots import cle_photo, noter_photos


def _art(page):
    return {"image_provenance": {"page": page}}


def test_noter_photos_garde_la_derniere_date_et_oublie_les_anciennes(tmp_path):
    f = tmp_path / "photos_utilisees.json"
    noter_photos([_art("https://commons.wikimedia.org/wiki/File:A%27b.jpg")], "2026-10-01", f)
    noter_photos([_art("https://commons.wikimedia.org/wiki/File:B.jpg")], "2026-11-04", f)
    noter_photos([_art("http://commons.wikimedia.org/wiki/File:B.jpg/")], "2026-11-05", f)
    noter_photos([_art("https://commons.wikimedia.org/wiki/File:B.jpg")], "2026-11-03", f)  # relecture d'un lot plus ancien
    d = json.loads(f.read_text(encoding="utf-8"))
    assert d == {"https://commons.wikimedia.org/wiki/File:B.jpg": "2026-11-05"}


def test_cle_photo_ignore_l_encodage():
    assert cle_photo("https://x/File:A%27b.jpg") == cle_photo("https://x/File:A'b.jpg")


def test_article_sans_photo_ignore(tmp_path):
    f = tmp_path / "p.json"
    noter_photos([{"illustration": True}], "2026-11-05", f)
    assert json.loads(f.read_text(encoding="utf-8")) == {}
