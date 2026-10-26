from agent.script_video import _en_scenes, controler

ARTICLE = {"title": "Le crédit baisse à 10,99 % dans la CEMAC.",
           "body": "Une couturière emprunte 1 million de FCFA. Douze versements de 90 000 FCFA : elle rembourse 1 080 000 FCFA."}


def scene(dit, ecran="", illustration=None, type_="explication"):
    return {"type": type_, "etiquette": "LE FAIT", "illustration": illustration or {"type": "banque"}, "ecran": ecran, "dit": dit}


def script(*scenes):
    return {"titre": "Crédit : le vrai prix", "question": "Et toi ?", "scenes": list(scenes)}


def test_chiffres_de_l_article_acceptes():
    s = script(*[scene("Elle paie 90 000 FCFA par mois, pendant 12 mois.", "Total : 1 080 000 FCFA",
                       {"type": "pile", "montant": "1 080 000"})] * 8)
    assert controler(s, ARTICLE) == []


def test_chiffre_invente_refuse():
    s = script(*[scene("Le taux passe à 9,5 %.", "9,5 %")] * 8)
    assert any("9.5" in p for p in controler(s, ARTICLE))


def test_longueurs_et_dessin_controles():
    s = script(*[scene("x" * 150, "y" * 50)] * 3, {**scene("ok"), "illustration": None})
    problemes = " | ".join(controler(s, ARTICLE))
    assert "scènes" in problemes and "voix trop longue" in problemes and "texte écran" in problemes and "sans dessin" in problemes


def test_fin_en_question_et_outro():
    s = _en_scenes(script(scene("Un crédit, c'est de l'argent prêté.", "Un crédit", {"type": "banque", "montant": None})))
    assert [sc["type"] for sc in s["scenes"]] == ["explication", "question", "outro"]
    assert s["scenes"][0]["illustration"] == {"type": "banque"}
    assert s["scenes"][1]["dit"] == "Et toi ? Dis-le en commentaire."
