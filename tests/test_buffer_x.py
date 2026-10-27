from agent.publieurs.buffer import BufferX
from agent.publieurs.x import longueur_x

ARTICLE = {"title": "Les salaires reviennent sur la table.", "body": "Patrons et syndicats négocient. " * 20,
           "hashtags": ["Cameroun", "Salaires"]}


def texte(article):
    return BufferX.texte(BufferX.__new__(BufferX), article, "")


def test_texte_du_producteur_trop_long_remplace():
    t = texte({**ARTICLE, "platform_texts": {"x": "a" * 300}})
    assert longueur_x(t) <= 280 and t.startswith("Les salaires")


def test_points_de_suspension_comptent_double():
    assert longueur_x("abc…") == 5 and longueur_x("l’été") == 5  # « ’ » compte 1, « … » compte 2


def test_texte_coupe_tient_dans_280_pour_x():
    # cas réel du 27/10 : texte coupé avec « … » à 280 caractères simples, refusé par X (281)
    article = {"title": "À Yaoundé I, les préinscriptions vont jusqu’au 31 octobre. Le portail affiche encore l’ancienne date.",
               "body": "Le rectorat de l’Université de Yaoundé I a prolongé les préinscriptions jusqu’au 31 octobre 2026 pour les "
                       "nouveaux bacheliers et les titulaires d’une licence qui souhaitent poursuivre leurs études cette année.",
               "hashtags": ["Cameroun", "Yaounde"]}
    assert longueur_x(texte(article)) <= 280


def test_texte_du_producteur_garde_s_il_tient():
    assert texte({**ARTICLE, "platform_texts": {"x": "Texte court #DECIDE"}}) == "Texte court #DECIDE"
