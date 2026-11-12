from agent.gabarit_v3 import consignes_reponse, controler_v3, script_secours
from agent.publieurs.buffer import BufferTikTok

Q = "C'est 275 000 FCFA pour chacun ?"
ARTICLE = {"title": "Coup de pouce par jeune", "editorial_type": "reponse", "hashtags": ["#cameroun"],
           "body": "Le Projet Filets sociaux verse 275 000 FCFA à chaque jeune retenu. Le versement se fait en une fois. "
                   "Le programme vise 20 000 jeunes du secteur informel. Les critères d'inscription ne sont pas publiés.",
           "reponse": {"question": Q, "plateformes": ["tiktok"],
                       "reponse": "Le Projet Filets sociaux verse 275 000 FCFA à chaque jeune retenu."}}


def _script(premiere):
    faits = ["Le Projet Filets sociaux verse 275 000 FCFA à chaque jeune retenu.", "Le versement se fait en une fois.",
             "Le programme vise 20 000 jeunes du secteur informel.", "Les critères d'inscription ne sont pas publiés."]
    return {"accroches": [Q] * 3, "titre": "Coup de pouce",
            "scenes": [{"type": "accroche", "fond": None, "illustration": None, "ecran": premiere, "dit": premiere}] +
                      [{"type": "explication", "illustration": {"type": "photo"}, "fond": None, "ecran": "Un fait",
                        "dit": f} for f in faits]}


def test_la_question_ouvre_la_reponse_et_echappe_aux_regles_du_hook():
    assert Q in consignes_reponse(ARTICLE) and consignes_reponse({"title": "x"}) == ""
    problemes = controler_v3(_script(Q), ARTICLE)
    assert not [p for p in problemes if "question" in p or "spectateur" in p or "hook" in p], problemes
    assert any("question du public" in p for p in controler_v3(_script("275 000 FCFA par jeune."), ARTICLE))


def test_une_question_reste_interdite_dans_un_short_ordinaire():
    ordinaire = {k: v for k, v in ARTICLE.items() if k not in ("editorial_type", "reponse")}
    assert any("pas de question" in p for p in controler_v3(_script(Q), ordinaire))


def test_secours_et_legende_tiktok():
    s = script_secours(ARTICLE)
    assert s["scenes"][0]["dit"] == Q and s["scenes"][1]["dit"].startswith("Le Projet Filets sociaux")
    legende = BufferTikTok({"buffer": {"canaux": {}}}).texte(ARTICLE, "")
    assert legende.startswith(f"Vous avez demandé : {Q}")
