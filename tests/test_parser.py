import pytest

from agent.parser import ErreurFormat, parser_post
from agent.publieurs.linkedin import formater_commentaire
from agent.publieurs.x import couper_pour_x, longueur_x


def test_post_complet():
    p = parser_post(
        "﻿Date : 20/10/2026 9h30\r\n"
        "Réseaux: Facebook, Twitter; insta, YouTube\r\n"
        "titre: Ma vidéo\r\ntags: seo, #angouleme\r\nyoutube_visibilite: non_repertoriee\r\n"
        "---\r\nTexte commun\r\n\r\n[x]\r\nVersion X\r\n[LinkedIn]\r\nVersion LI\r\n"
    )
    assert p.date.isoformat() == "2026-10-20T09:30:00+02:00"
    assert p.reseaux == ["facebook", "x", "instagram", "youtube"]
    assert p.texte == "Texte commun"
    assert p.textes == {"x": "Version X", "linkedin": "Version LI"}
    assert p.titre == "Ma vidéo" and p.tags == ["seo", "angouleme"]
    assert p.youtube_visibilite == "unlisted" and p.ia


def test_date_iso_maintenant_et_tous():
    assert parser_post("date: 2026-12-01 18:00\nreseaux: x\n---\nA").date.hour == 18
    assert parser_post("date: 2026-12-01\nreseaux: x\n---\nA").date.hour == 9  # heure par défaut
    p = parser_post("date: maintenant\nreseaux: tous\nia: non\n---\nA")
    assert p.date is None and len(p.reseaux) == 5 and not p.ia


def test_crochets_non_reseau_restent_dans_le_texte():
    p = parser_post("reseaux: x\n---\n[Offre spéciale]\nBonjour")
    assert p.texte == "[Offre spéciale]\nBonjour"


@pytest.mark.parametrize("contenu, message", [
    ("reseaux: x\nTexte sans séparateur", "---"),
    ("date: 32/13/2026\nreseaux: x\n---\nA", "date"),
    ("date: demain\nreseaux: x\n---\nA", "date illisible"),
    ("reseaux: tiktok\n---\nA", "réseau inconnu"),
    ("date: 20/10/2026\n---\nA", "reseaux"),
    ("reseaux: x\n---\n", "vide"),
    ("reseaux: x\nia: peut-être\n---\nA", "ia"),
])
def test_erreurs_lisibles(contenu, message):
    with pytest.raises(ErreurFormat, match=message):
        parser_post(contenu)


def test_x_coupe_proprement():
    long = "mot " * 100 + "https://exemple.fr/une/url/tres/longue/qui/compte/pour/vingt-trois"
    assert longueur_x(couper_pour_x(long)) <= 280
    assert couper_pour_x("court") == "court"
    assert longueur_x("voir https://exemple.fr/" + "a" * 100) == len("voir ") + 23


def test_linkedin_echappe_et_hashtags():
    assert formater_commentaire("SEO (local) #Angoulême @moi") == r"SEO \(local\) {hashtag|\#|Angoulême} \@moi"
