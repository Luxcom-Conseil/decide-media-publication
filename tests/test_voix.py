import pytest

from agent.voix import normaliser, preparer

CAS = [
    ("L'inflation atteint 3,5 % en septembre.", "L'inflation atteint trois virgule cinq pour cent en septembre."),
    ("Le taux passe à 12,75.", "Le taux passe à douze virgule soixante-quinze."),
    ("Soit 3,05 points.", "Soit trois virgule zéro cinq points."),
    ("6 471 candidats", "six mille quatre cent soixante et onze candidats"),
    ("50 000 FCFA par mois", "cinquante mille francs CFA par mois"),
    ("un prêt de 1.200 €", "un prêt de mille deux cents euros"),
    ("un logement de 120 m²", "un logement de cent vingt mètres carrés"),
    ("la 2e édition et le 1er forum", "la deuxième édition et le premier forum"),
    ("la 12ème session", "la douzième session"),
    ("le 22 octobre 2026", "le vingt-deux octobre deux mille vingt-six"),
    ("à 14h30", "à quatorze heures trente"),
    ("$5 millions", "cinq millions de dollars"),
    ("pour $40", "pour quarante dollars"),
    ("1,5 milliard de dollars", "un virgule cinq milliard de dollars"),
]


@pytest.mark.parametrize("brut,attendu", CAS)
def test_normaliser(brut, attendu):
    assert normaliser(brut) == attendu


def test_preparer_lexique_apres_nombres():
    assert preparer("Dion Ngute, 2e fois", [("Ngute", "Ngouté")]) == "Dion Ngouté, deuxième fois"
