import json

from agent.gabarit_v3 import PHOTOS_PAR_SHORT, photos_du_sujet
from agent.lots import cle_photo
from agent.medias_commons import BANQUE

INDEX = json.loads((BANQUE / "index.json").read_text(encoding="utf-8"))


def _article(entree):
    return {"_lot": "2026-11-05", "image_provenance": {"page": entree["page"]}}


def _premiere(theme):
    return next(e for e in INDEX if e["theme"] == theme and e["personnes"] in ("aucune", "loin") and not e["marque"])


def test_photo_hors_banque_rien(tmp_path):
    assert photos_du_sujet({"image_provenance": {"page": "https://exemple.org/x.jpg"}}, tmp_path, set(), {}) == []
    assert photos_du_sujet({}, tmp_path, set(), {}) == []


def test_theme_generique_donne_la_photo_puis_le_theme(tmp_path):
    e = _premiere("bois_foret")
    photos = photos_du_sujet(_article(e), tmp_path, set(), {})
    assert photos[0]["credit"] == e["credit"]  # la photo de l'article d'abord
    assert 2 <= len(photos) <= PHOTOS_PAR_SHORT
    assert all((tmp_path / p["src"].split("/")[-1]).exists() for p in photos)


def test_theme_precis_seulement_la_photo(tmp_path):
    e = _premiere("institutions")  # un bâtiment nommé : pas d'autre bâtiment à sa place
    assert len(photos_du_sujet(_article(e), tmp_path, set(), {})) == 1


def test_photos_recentes_ecartees(tmp_path):
    e = _premiere("bois_foret")
    autres = [x for x in INDEX if x["theme"] == "bois_foret" and x is not e]
    recentes = {cle_photo(x["page"]): "2026-11-03" for x in autres}
    photos = photos_du_sujet(_article(e), tmp_path, set(), recentes)
    assert [p["credit"] for p in photos] == [e["credit"]]
