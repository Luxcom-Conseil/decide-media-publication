from datetime import datetime, timezone

from agent.config import charger_config
from agent.perso import EtatPerso, controler, est_le_moment, legende_finale

CFG = charger_config("config.yaml")
CFG["perso"].update(jours=["lundi", "jeudi"], heure="12:00")


def _script(**kw):
    s = {"rubrique": "carnet", "transcription": "", "titre": "t", "question": "Et toi ?", "legende": "Une ligne.",
         "hashtags": ["ecriture"],
         "scenes": [{"type": "texte", "photo": None, "ecran": "Écrire", "dit": "J'écris depuis 1998."}] * 5}
    s.update(kw)
    return s


def test_controle_accepte_chiffres_de_la_matiere():
    assert controler(_script(), "J'ai commencé à écrire en 1998.", 0) == []


def test_controle_refuse_chiffre_invente():
    assert any("1998" in p for p in controler(_script(), "J'ai commencé à écrire jeune.", 0))


def test_controle_chiffre_du_vocal_accepte():
    assert controler(_script(transcription="depuis 1998"), "", 0) == []


def test_controle_photo_inexistante():
    scenes = [{"type": "photo", "photo": 2, "ecran": "x", "dit": "y"}] * 5
    assert any("photo n°2" in p for p in controler(_script(scenes=scenes), "", 1))


def test_moment(tmp_path):
    etat = EtatPerso(tmp_path / "p.json")
    lundi_matin = datetime(2026, 10, 26, 8, 0, tzinfo=timezone.utc)  # 9 h à Paris
    lundi_midi = datetime(2026, 10, 26, 12, 45, tzinfo=timezone.utc)
    mardi = datetime(2026, 10, 27, 12, 45, tzinfo=timezone.utc)
    assert not est_le_moment(CFG, lundi_matin, etat)[0]
    assert est_le_moment(CFG, lundi_midi, etat)[0]
    assert not est_le_moment(CFG, mardi, etat)[0]
    etat.d["publications"].append({"jour": "2026-10-26"})
    assert not est_le_moment(CFG, lundi_midi, etat)[0]


def test_legende_sans_tiret_long_et_hashtags():
    t = legende_finale(_script(legende="Une idée — simple.", hashtags=["#écriture", "biographe"]))
    assert "—" not in t and t.endswith("#écriture #biographe")
