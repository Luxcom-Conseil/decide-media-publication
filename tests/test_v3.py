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


ARTICLE = {"title": "La taxe double", "body": "La taxe passe de 15 % à 30 % le 3 mars à Douala. La mairie a publié le texte lundi. Le montant total reste inconnu.",
           "etiquette_chiffre": {"texte": "30 %"}}
FOND = {"source": "commons", "recherche": "Douala", "logo": False, "secours": None}


def _script(*dits):
    scenes = [{"type": "accroche", "illustration": None, "fond": FOND, "ecran": dits[0], "dit": dits[0]}]
    scenes += [{"type": "media", "illustration": None, "fond": FOND, "ecran": "La *taxe* double", "dit": d} for d in dits[1:]]
    return {"accroches": ["a", "b", "c"], "titre": "La taxe double", "scenes": scenes}


def test_script_information_accepte():
    from agent.gabarit_v3 import controler_v3
    s = _script("La taxe passe à 30 % à Douala.", "Elle était de 15 %.", "Le changement date du 3 mars.", "La mairie a publié le texte.")
    assert controler_v3(s, ARTICLE) == []


def test_refuse_question_adresse_analyse_et_chiffre_invente():
    from agent.gabarit_v3 import controler_v3
    fin = ("Elle était de 15 %.", "Le changement date du 3 mars.", "La mairie a publié le texte.")
    for hook, attendu in (("La taxe va-t-elle doubler ?", "question"), ("Ta taxe passe à 30 %.", "spectateur"),
                          ("Voici la nouvelle taxe à 30 %.", "analyse"), ("La taxe passe à 2 %.", "chiffres absents")):
        assert any(attendu in p for p in controler_v3(_script(hook, *fin), ARTICLE)), hook


def test_refuse_trop_de_parties_et_personnage():
    from agent.gabarit_v3 import controler_v3
    fait = "La mairie a publié le texte."
    assert any("scènes" in p for p in controler_v3(_script(*[fait] * 9), ARTICLE))
    s = _script("La taxe passe à 30 % à Douala.", fait, fait, fait)
    s["scenes"][1].update(type="explication", fond=None, illustration={"type": "personnage"})
    assert any("dessin" in p for p in controler_v3(s, ARTICLE))


def test_secours_lit_les_phrases_de_l_article():
    from agent.gabarit_v3 import script_secours
    s = script_secours(ARTICLE)
    assert s["scenes"][0]["ecran"] == "30 %"
    assert [sc["dit"] for sc in s["scenes"]][1] == "La mairie a publié le texte lundi."
    assert script_secours({"title": "x", "body": ""}) is None
    methode = {"title": "x", "body": "Cet article s'appuie sur un texte du journal. Voici l'angle critique du dossier. Ils sont menés par la police."}
    assert script_secours(methode) is None
