"""Série « Le point pays » (antenne Afrique, test du 24/11 au 7/12/2026) : script sans IA tiré du champ `serie`."""
from agent.gabarit_v3 import est_serie, script_serie


def article(n=4, accroche="Le point Nigeria", **autres):
    breves = [{"titre": f"Titre {k}", "phrases": [f"Première phrase de la brève {k}.", f"Deuxième phrase de la brève {k}."],
               "source_url": "https://exemple.ng", "photo_page": f"https://commons.wikimedia.org/wiki/File:{k}.jpg"}
              for k in range(1, n + 1)]
    return {"editorial_type": "serie_pays", "country": "Nigeria", "title": "Le point Nigeria : 4 infos",
            "serie": {"accroche": accroche, "breves": breves}, **autres}


def test_une_carte_par_breve_avec_le_decompte():
    s = script_serie(article())
    cartes = [sc for sc in s["scenes"] if sc["type"] == "breve"]
    assert [sc["compteur"] for sc in cartes] == [{"n": k, "total": 4} for k in range(1, 5)]
    assert cartes[0]["ecran"] == "Titre 1" and cartes[0]["dit"] == "Première phrase de la brève 1."


def test_les_phrases_sont_lues_telles_quelles_dans_l_ordre():
    s = script_serie(article())
    dits = [sc["dit"] for sc in s["scenes"][1:]]
    attendu = [p for k in range(1, 5) for p in (f"Première phrase de la brève {k}.", f"Deuxième phrase de la brève {k}.")]
    assert dits == attendu
    assert all(sc["compteur"]["n"] == 2 for sc in s["scenes"] if "brève 2" in sc["dit"])


def test_accroche_ne_repete_pas_le_pays():
    assert script_serie(article())["scenes"][0]["dit"] == "Le point Nigeria : les 4 infos du jour."
    assert script_serie(article(accroche="Le point"))["scenes"][0]["dit"] == "Le point Nigeria : les 4 infos du jour."


def test_photo_de_chaque_breve():
    s = script_serie(article())
    assert {sc["photo_page"] for sc in s["scenes"] if sc.get("compteur", {}).get("n") == 3} == {"https://commons.wikimedia.org/wiki/File:3.jpg"}


def test_hors_limites_pas_de_serie():
    assert script_serie(article(n=2)) is None
    assert script_serie(article(n=6)) is None
    assert not est_serie({"editorial_type": "critical_explainer", "serie": {"breves": [1]}})
    assert not est_serie({"editorial_type": "serie_pays"})
