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


def test_nombre_ecrit_en_lettres_dans_l_article_accepte():
    article = {**ARTICLE, "body": ARTICLE["body"] + " Le chantier doit durer quinze mois."}
    s = script(*[scene("Le chantier dure 15 mois.", "15 mois", {"type": "calendrier", "texte": "15 mois"})] * 8)
    assert controler(s, article) == []


def test_million_en_chiffres_accepte():
    s = script(*[scene("Elle emprunte 1 000 000 FCFA.", "Prêt : 1 000 000 FCFA")] * 8)
    assert controler(s, ARTICLE) == []


def test_liste_sans_points_refusee():
    s = script(*[scene("Ce qu'il faut faire.", "À faire", {"type": "liste", "texte": None})] * 8)
    assert any("liste sans ses points" in p for p in controler(s, ARTICLE))


def test_exemple_fictif_refuse():
    s = script(*[scene("Prenons un exemple inventé.", "Exemple fictif")] * 8)
    assert any("Prenons un exemple" in p for p in controler(s, ARTICLE))


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
