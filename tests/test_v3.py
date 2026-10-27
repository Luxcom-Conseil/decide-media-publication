from agent.medias_commons import LICENCES, _mots, credit
from agent.medias_libres import _hors_sujet


def test_licences_libres_seulement():
    assert all(LICENCES.match(x) for x in ("CC BY-SA 4.0", "CC BY 2.0", "CC0", "Public domain"))
    assert not any(LICENCES.match(x) for x in ("Fair use", "All rights reserved", ""))


def test_mots_du_titre_sans_accents():
    assert {"universite", "yaounde", "i"} <= _mots("File:Université de Yaoundé I.jpg")
    assert "logo" not in _mots("Beac logo.svg")


def test_credit_court():
    assert credit("Kondah (talk)", "CC BY-SA 4.0") == "Kondah / Wikimedia Commons · CC BY-SA 4.0"


def test_pixabay_hors_sujet():
    assert _hors_sujet("students campus africa", "desert, landscape, africa")
    assert not _hors_sujet("students campus africa", "student, university, campus")
    assert not _hors_sujet("african market", "africa, market, vegetables")


def test_lieux_de_la_carte():
    from agent.gabarit_v3 import lieu_connu
    assert lieu_connu("Yaoundé") and lieu_connu("Côte d’Ivoire") and lieu_connu("Lomé")
    assert not lieu_connu("Mumbai") and not lieu_connu("_")
