"""La banque de photos Afrique lue par la production DECIDE MEDIA reste cohérente."""
import json
import re
from pathlib import Path

from PIL import Image

BANQUE = Path(__file__).parent.parent / "banque_photos_af"
ENTREES = json.loads((BANQUE / "index.json").read_text(encoding="utf-8"))


def test_chaque_entree_a_son_fichier_et_sa_planche():
    for e in ENTREES:
        assert (BANQUE / e["fichier"]).is_file(), e["fichier"]
        assert (BANQUE / f"planche_{e['theme']}.jpg").is_file(), e["theme"]


def test_aucun_fichier_hors_index():
    connus = {e["fichier"] for e in ENTREES}
    for f in BANQUE.glob("*/*.jpg"):
        assert f.relative_to(BANQUE).as_posix() in connus, f.name


def test_provenance_complete_et_licence_libre():
    for e in ENTREES:
        for c in ("montre", "lieu", "date", "auteur", "page", "credit"):
            assert e[c], (e["fichier"], c)
        assert re.match(r"(CC0|Public domain|CC BY(-SA)? \d\.\d)$", e["licence"]), e["licence"]
        assert e["page"].startswith("https://commons.wikimedia.org/")
        assert e["personnes"] in ("aucune", "loin", "visibles", "enfants")


def test_le_credit_nomme_lieu_auteur_licence():
    for e in ENTREES:
        lieu = e["lieu"] if e["lieu"] != "inconnu" else e["pays"]  # lieu inconnu : le crédit nomme le pays
        assert lieu in e["credit"] and e["auteur"] in e["credit"] and e["licence"] in e["credit"]
        assert e["credit"].endswith("recadrée")


def test_pas_de_doublon():
    assert len({e["page"] for e in ENTREES}) == len(ENTREES)
    assert len({e["fichier"] for e in ENTREES}) == len(ENTREES)


def test_photos_assez_grandes_pour_un_carre():
    for e in ENTREES:
        with Image.open(BANQUE / e["fichier"]) as im:
            assert min(im.size) >= 850, e["fichier"]


PAYS = {
    "Afrique du Sud", "Algérie", "Angola", "Bénin", "Botswana", "Burkina Faso", "Burundi", "Cabo Verde", "Cameroun",
    "Centrafrique", "Comores", "Congo", "Côte d'Ivoire", "Djibouti", "Égypte", "Érythrée", "Eswatini", "Éthiopie",
    "Gabon", "Gambie", "Ghana", "Guinée", "Guinée-Bissau", "Guinée équatoriale", "Kenya", "Lesotho", "Liberia", "Libye",
    "Madagascar", "Malawi", "Mali", "Maroc", "Maurice", "Mauritanie", "Mozambique", "Namibie", "Niger", "Nigeria",
    "Ouganda", "RD Congo", "Rwanda", "Sao Tomé-et-Principe", "Sénégal", "Seychelles", "Sierra Leone", "Somalie",
    "Soudan", "Soudan du Sud", "Tanzanie", "Tchad", "Togo", "Tunisie", "Zambie", "Zimbabwe", "Afrique"}


def test_chaque_photo_porte_un_pays_connu_du_controle():
    """verifier_lot.py --antenne afrique refuse une photo d'un autre pays que l'article : le nom doit être exact."""
    for e in ENTREES:
        assert e.get("pays") in PAYS, (e["fichier"], e.get("pays"))
