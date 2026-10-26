from datetime import datetime, timezone

from agent.config import charger_config
from agent.perso import EtatPerso, controler, est_le_moment, fiche, legende_finale
from agent.perso_sujets import CATEGORIES, PAR_ID, SUJETS, prochain

CFG = charger_config("config.yaml")
CFG["perso"].update(jours=["lundi", "jeudi"], heure="12:00")
SUJET = PAR_ID["pareto"]


def _script(**kw):
    dit = "Tu passes des heures sur des tâches qui ne rapportent presque rien, et tu te demandes pourquoi ça n'avance pas."
    s = {"titre": "La loi de Pareto", "question": "Et toi ?", "legende": "Une ligne.", "hashtags": ["psychologie"],
         "scenes": [{"type": "texte", "photo": None, "ecran": "80 % des résultats", "dit": dit}] * 12}
    s.update(kw)
    return s


def test_controle_accepte_chiffres_de_la_fiche():
    assert controler(_script(), fiche(SUJET), 0) == []


def test_controle_refuse_chiffre_invente():
    scenes = [{"type": "texte", "photo": None, "ecran": "73 % des gens", "dit": "x" * 100}] * 12
    assert any("73" in p for p in controler(_script(scenes=scenes), fiche(SUJET), 0))


def test_controle_refuse_etude():
    scenes = [{"type": "texte", "photo": None, "ecran": "x", "dit": "Une étude a montré que ça marche, " + "x" * 80}] * 12
    assert any("étude" in p for p in controler(_script(scenes=scenes), fiche(SUJET), 0))


def test_controle_refuse_trop_court():
    scenes = [{"type": "texte", "photo": None, "ecran": "x", "dit": "Court."}] * 12
    assert any("trop court" in p for p in controler(_script(scenes=scenes), fiche(SUJET), 0))


def test_controle_portrait_inexistant():
    scenes = [{"type": "photo", "photo": 2, "ecran": "x", "dit": "y" * 100}] * 12
    assert any("portrait n°2" in p for p in controler(_script(scenes=scenes), fiche(SUJET), 1))


def test_rotation_des_categories():
    publies, vus = [], []
    for _ in range(len(CATEGORIES) * 2):
        s = prochain(publies)
        publies.append(s[0])
        vus.append(s[1])
    assert len(set(publies)) == len(publies)  # pas de doublon
    assert all(a != b for a, b in zip(vus, vus[1:]))  # deux catégories différentes d'affilée


def test_cycle_complet_puis_recommence():
    publies = [s[0] for s in SUJETS]
    assert prochain(publies)[0] in PAR_ID


def test_moment(tmp_path):
    etat = EtatPerso(tmp_path / "p.json")
    lundi_matin = datetime(2026, 10, 26, 8, 0, tzinfo=timezone.utc)  # 9 h à Paris
    lundi_midi = datetime(2026, 10, 26, 12, 45, tzinfo=timezone.utc)
    mardi = datetime(2026, 10, 27, 12, 45, tzinfo=timezone.utc)
    assert not est_le_moment(CFG, lundi_matin, etat)[0]
    assert est_le_moment(CFG, lundi_midi, etat)[0]
    assert not est_le_moment(CFG, mardi, etat)[0]
    etat.d["publications"].append({"jour": "2026-10-26", "sujet": "pareto"})
    assert not est_le_moment(CFG, lundi_midi, etat)[0]


def test_legende_sans_tiret_long_et_hashtags():
    t = legende_finale(_script(legende="Une idée — simple.", hashtags=["#psychologie", "astuces"]))
    assert "—" not in t and t.endswith("#psychologie #astuces")
