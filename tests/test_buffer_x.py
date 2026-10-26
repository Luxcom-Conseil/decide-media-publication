from agent.publieurs.buffer import BufferX
from agent.publieurs.x import longueur_x

ARTICLE = {"title": "Les salaires reviennent sur la table.", "body": "Patrons et syndicats négocient. " * 20,
           "hashtags": ["Cameroun", "Salaires"]}


def texte(article):
    return BufferX.texte(BufferX.__new__(BufferX), article, "")


def test_texte_du_producteur_trop_long_remplace():
    t = texte({**ARTICLE, "platform_texts": {"x": "a" * 300}})
    assert longueur_x(t) <= 280 and t.startswith("Les salaires")


def test_texte_du_producteur_garde_s_il_tient():
    assert texte({**ARTICLE, "platform_texts": {"x": "Texte court #DECIDE"}}) == "Texte court #DECIDE"
