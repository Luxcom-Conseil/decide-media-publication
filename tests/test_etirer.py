from agent.gabarit_v3 import DUREE_MIN, TENUE_MAX, controler_v3, duree_scene, etirer


def _sc(duree, type_="explication"):
    return {"type": type_, "voix": {"src": "x.mp3", "duree": duree}}


def test_un_short_court_atteint_30_secondes_en_tenant_chaque_phrase():
    scenes = [_sc(3.0, "accroche"), _sc(5.0), _sc(5.0), _sc(5.0), _sc(1.5, "outro")]
    total = etirer(scenes)
    assert DUREE_MIN <= total < DUREE_MIN + 0.2
    assert all(0 < sc["tenue"] <= TENUE_MAX for sc in scenes[:-1])


def test_le_reste_va_au_generique_quand_les_phrases_ne_suffisent_pas():
    scenes = [_sc(2.0, "accroche"), _sc(3.0), {"type": "outro", "duree": 3.5}]
    assert etirer(scenes) >= DUREE_MIN
    assert scenes[0]["tenue"] == TENUE_MAX and scenes[-1]["tenue"] > 10


def test_un_short_deja_long_ne_change_pas():
    scenes = [_sc(8.0, "accroche"), _sc(9.0), _sc(9.0), _sc(4.0, "outro")]
    avant = sum(map(duree_scene, scenes))
    assert etirer(scenes) == avant and not any("tenue" in sc for sc in scenes)


def test_voix_trop_courte_refusee_seulement_si_l_article_a_de_la_matiere():
    script = {"accroches": ["a", "b", "c"], "titre": "T",
              "scenes": [{"type": "accroche", "ecran": "Hook court", "dit": "Phrase une."}] +
                        [{"type": "explication", "illustration": {"type": "photo"}, "fond": None, "ecran": "Fait",
                          "dit": "Une phrase de fait."} for _ in range(4)]}
    long = {"title": "T", "body": "Une phrase de fait. " * 60}
    court = {"title": "T", "body": "Une phrase de fait. Phrase une."}
    assert any("trop courte" in p for p in controler_v3(script, long))
    assert not any("trop courte" in p for p in controler_v3(script, court))
