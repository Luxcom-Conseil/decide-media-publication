from datetime import date

from agent.bilan import _titre, construire, rapport

AUJ = date(2026, 11, 12)


def _p(titre, jour, vues, commentaires=0, lien=None):
    return {"titre": titre, "date": jour, "vues": vues, "reactions": 0, "commentaires": commentaires, "partages": 0, "lien": lien}


def test_titre_coupe_la_legende():
    assert _titre("Coup de pouce à 275 000 francs Le Projet Filets sociaux verse…\n#cameroun") == "Coup de pouce à 275 000 francs"
    assert _titre("Le blé russe attend ses preuves. Un second paragraphe.") == "Le blé russe attend ses preuves"
    assert len(_titre("mot " * 60)) <= 100


def test_construire_classe_et_recopie_les_commentaires_des_videos_commentees():
    appels = []
    releves = {
        "tiktok": [_p("A", "2026-11-06", 1000, 300, "https://www.tiktok.com/@d/video/1"), _p("B", "2026-11-09", 50, 2),
                   _p("Vieux", "2023-05-01", 9999)],
        "youtube": [_p("A", "2026-11-06", 20), _p("C", "2026-11-12", 0)],
        "facebook": "indisponible : RuntimeError",
    }
    b = construire(releves, AUJ, commentaires=lambda lien: appels.append(lien) or [{"texte": "le lien ?", "jaime": 3}])
    assert [p["titre"] for p in b["top"]][:2] == ["A", "B"]
    assert appels == ["https://www.tiktok.com/@d/video/1"]
    assert b["top"][0]["commentaires_du_public"][0]["texte"] == "le lien ?"
    assert b["sujets_forts"][0] == {"titre": "A", "vues": 1020, "reseaux": {"tiktok": 1000, "youtube": 20}}
    assert "C" not in [s["titre"] for s in b["sujets_faibles"]]  # publié aujourd'hui : pas encore jugé
    assert b["reseaux"]["tiktok"]["depuis_le_debut"]["vues"] == 1050  # 2023 exclu
    assert b["reseaux"]["facebook"] == {"etat": "indisponible : RuntimeError"}
    titre, corps = rapport(b)
    assert titre == "Bilan DECIDE MEDIA de la semaine du 12/11/2026"
    assert "| Facebook (vidéos) | indisponible" in corps and "1 000 vues" in corps


def test_facebook_commentees_des_2_commentaires():
    vus = []
    releves = {"facebook": [_p("F1", "2026-11-10", 40, 3, "https://www.facebook.com/1/videos/123456789"),
                            _p("F2", "2026-11-10", 900, 1, "https://www.facebook.com/1/videos/987654321"),
                            _p("F3", "2026-10-01", 10, 9, "https://www.facebook.com/1/videos/555555555")]}
    b = construire(releves, AUJ, commentaires=lambda l: [],
                   commentaires_fb=lambda l: vus.append(l) or [{"texte": "c'est pour qui ?", "jaime": 1, "reponses": 0}])
    assert [p["titre"] for p in b["facebook_commentees"]] == ["F1"]  # F2 : 1 seul commentaire ; F3 : trop ancien
    assert vus == ["https://www.facebook.com/1/videos/123456789"]
    assert b["facebook_commentees"][0]["commentaires_du_public"][0]["texte"] == "c'est pour qui ?"
