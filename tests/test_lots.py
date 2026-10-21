import json
from datetime import datetime, timezone
from pathlib import Path

import pytest

from agent.config import charger_config
from agent.lots import Journal, LotInvalide, controler_manifeste, creneaux, traiter_lots
from agent.publieurs import Resultat
from agent.sources import Dossier, Fichier

CFG = charger_config("inexistant.yaml")
MATIN = datetime(2026, 10, 21, 4, 30, tzinfo=timezone.utc)  # 05:30 à Douala, 06:30 à Paris


def article(i, **kw):
    a = {"id": f"decide-media-2026-10-21-{i:02d}", "status": "ready", "title": f"Titre {i}",
         "content_type": "news", "post_text": f"Texte {i}", "platform_texts": {"facebook": f"Texte FB {i}"},
         "image_file": {"id": f"img{i}", "name": f"{i:02d}-sujet.png"}}
    a.update(kw)
    return a


def manifeste(**kw):
    m = {"protocol_version": "1.2", "date": "2026-10-21", "status": "ready", "article_count": 10,
         "required_article_count": 10, "delivery_deadline": "x", "delivered_on_time": True,
         "completed_at": "x", "articles": [article(i) for i in range(1, 11)]}
    m.update(kw)
    return m


def test_controle_manifeste():
    assert len(controler_manifeste(manifeste(), "2026-10-21")) == 10
    for m, msg in [(manifeste(status="failed"), "ready"), (manifeste(status="empty"), "ready"),
                   (manifeste(article_count=9), "10 articles"), (manifeste(date="2026-10-20"), "date"),
                   (manifeste(protocol_version="1.1"), "1.2")]:
        with pytest.raises(LotInvalide, match=msg):
            controler_manifeste(m, "2026-10-21")
    m = manifeste()
    m["articles"][3]["platform_texts"] = {}
    with pytest.raises(LotInvalide, match="platform_texts.facebook"):
        controler_manifeste(m, "2026-10-21")


def test_creneaux_du_jour_et_decalage():
    h = creneaux(CFG, datetime(2026, 10, 21).date(), 10, MATIN, [])
    assert [x.strftime("%H:%M") for x in h[:3]] == ["07:00", "08:30", "10:00"]
    tard = datetime(2026, 10, 21, 12, 0, tzinfo=timezone.utc)  # 13:00 à Douala
    h = creneaux(CFG, tard.date(), 10, tard, [])
    assert h[0] > tard and all(b - a >= __import__("datetime").timedelta(minutes=45) for a, b in zip(h, h[1:]))


class FauxDrive:
    def __init__(self, m):
        self.m = m
        self.telechargements = 0

    def lister_dossiers(self):
        return [Dossier("d1", "2026-10-21"), Dossier("d0", "2026-10-15"), Dossier("r", "_references")]

    def lister_fichiers(self, d):
        return [Fichier("man", "manifest.json", "")] if d.id == "d1" else []

    def lire_brut(self, f):
        return json.dumps(self.m).encode()

    def telecharger_id(self, fid, nom, dest: Path):
        self.telechargements += 1
        p = dest / nom
        p.write_bytes(b"png")
        return p


class FauxFacebook:
    def __init__(self, deja=None, panne=None):
        self.programmes, self.deja, self.panne = [], deja or {}, panne

    def trouver_programme(self, texte):
        return self.deja.get(texte)

    def programmer(self, texte, image, quand, article=None):
        if self.panne and self.panne in texte:
            raise RuntimeError("timeout")
        self.programmes.append((texte, quand))
        return Resultat("url", f"post-{len(self.programmes)}")


def test_programme_les_10_sans_doublon(tmp_path):
    fb, drive, j = FauxFacebook(), FauxDrive(manifeste()), Journal(tmp_path / "lots.json")
    traiter_lots(CFG, drive, {"facebook": fb}, j, print, maintenant=MATIN)
    assert len(fb.programmes) == 10 and fb.programmes[0][0] == "Texte FB 1"
    traiter_lots(CFG, drive, {"facebook": fb}, Journal(tmp_path / "lots.json"), print, maintenant=MATIN)
    assert len(fb.programmes) == 10  # second passage : rien de nouveau


def test_reprise_apres_incident(tmp_path):
    deja = {"Texte FB 2": {"id": "ancien", "quand": "2026-10-21T08:30:00+01:00"}}
    fb = FauxFacebook(deja=deja, panne="FB 5")
    j = Journal(tmp_path / "lots.json")
    traiter_lots(CFG, FauxDrive(manifeste()), {"facebook": fb}, j, print, maintenant=MATIN)
    assert len(fb.programmes) == 8  # 2 déjà présent, 5 en panne
    assert j.get("decide-media-2026-10-21-02", "facebook")["post_id"] == "ancien"
    assert j.get("decide-media-2026-10-21-05", "facebook")["statut"] == "echec"
    fb.panne = None
    traiter_lots(CFG, FauxDrive(manifeste()), {"facebook": fb}, j, print, maintenant=MATIN)
    assert len(fb.programmes) == 9


def test_lot_non_ready_ignore(tmp_path):
    fb = FauxFacebook()
    traiter_lots(CFG, FauxDrive(manifeste(status="failed")), {"facebook": fb}, Journal(tmp_path / "l.json"),
                 print, maintenant=MATIN)
    assert not fb.programmes


class FauxLinkedIn:
    """Pas de méthode programmer() : l'agent publie lui-même à l'heure."""

    def __init__(self):
        self.publies = []

    def valider(self, post):
        pass

    def publier(self, post, texte):
        self.publies.append((texte, post.images[0].nom))
        return Resultat("https://linkedin/p", f"urn:li:share:{len(self.publies)}")


def test_linkedin_publie_a_l_heure(tmp_path):
    from datetime import timedelta
    li, fb = FauxLinkedIn(), FauxFacebook()
    m = manifeste()
    for a in m["articles"]:
        a["platform_texts"]["linkedin"] = a["post_text"] + " (LI)"
    j = Journal(tmp_path / "l.json")
    pubs = {"facebook": fb, "linkedin": li}
    cfg = {**CFG, "lots": {**CFG["lots"], "reseaux": ["facebook", "linkedin"]}}
    traiter_lots(cfg, FauxDrive(m), pubs, j, print, maintenant=MATIN)  # 05:30 Douala : rien n'est encore dû
    assert len(fb.programmes) == 10 and not li.publies
    a_7h05 = MATIN + timedelta(hours=1, minutes=35)  # 07:05 Douala
    traiter_lots(cfg, FauxDrive(m), pubs, j, print, maintenant=a_7h05)
    assert li.publies == [("Texte 1 (LI)", "01-sujet.png")]
    traiter_lots(cfg, FauxDrive(m), pubs, j, print, maintenant=a_7h05)
    assert len(li.publies) == 1  # pas de doublon
    soir = MATIN + timedelta(hours=16)  # 21:30 Douala : tous dus
    traiter_lots(cfg, FauxDrive(m), pubs, j, print, maintenant=soir)
    assert len(li.publies) == 10 and len(fb.programmes) == 10
    lendemain = MATIN + timedelta(days=3)  # trop tard : abandon, pas de publication tardive
    j2 = Journal(tmp_path / "l2.json")
    traiter_lots(cfg, FauxDrive(m), {"linkedin": li}, j2, print, maintenant=MATIN)
    traiter_lots({**cfg, "lots": {**cfg["lots"], "jours_max": 5}}, FauxDrive(m), {"linkedin": li}, j2, print,
                 maintenant=lendemain)
    assert j2.get("decide-media-2026-10-21-01", "linkedin")["statut"] == "abandonne"


def test_plafond_par_lot(tmp_path):
    yt = FauxFacebook()  # même interface programmer()/trouver_programme() que YouTube
    cfg = {**CFG, "lots": {**CFG["lots"], "reseaux": ["youtube"], "max_par_lot": {"youtube": 6}},
           "youtube": {**CFG["youtube"], "modele_valide": True}}
    traiter_lots({**cfg, "youtube": {"modele_valide": False}}, FauxDrive(manifeste()), {"youtube": yt},
                 Journal(tmp_path / "x.json"), print, maintenant=MATIN)
    assert not yt.programmes  # verrou : rien tant que le modèle n'est pas validé
    j = Journal(tmp_path / "l.json")
    traiter_lots(cfg, FauxDrive(manifeste()), {"youtube": yt}, j, print, maintenant=MATIN)
    assert len(yt.programmes) == 6
    traiter_lots(cfg, FauxDrive(manifeste()), {"youtube": yt}, j, print, maintenant=MATIN)
    assert len(yt.programmes) == 6  # pas de dépassement au passage suivant


def test_simulation_ne_programme_rien(tmp_path):
    fb, drive = FauxFacebook(), FauxDrive(manifeste())
    traiter_lots(CFG, drive, {"facebook": fb}, Journal(tmp_path / "l.json"), print, simulation=True,
                 maintenant=MATIN)
    assert not fb.programmes and drive.telechargements == 0
