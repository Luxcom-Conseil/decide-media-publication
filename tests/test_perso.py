from datetime import datetime, timezone

from agent.config import charger_config
from agent.perso import EtatPerso, controler, creneaux_semaine, est_le_moment, fiche, legende_finale
from agent.perso_sujets import CATEGORIES, PAR_ID, SUJETS, prochain

CFG = charger_config("config.yaml")
CFG["perso"].update(jours=["lundi", "jeudi"], heure="12:00", horaires=["12:30", "18:30", "21:00"], delai_production_heures=3)
SOURCE = fiche(PAR_ID["pareto"])
DIT = "Tu passes des heures sur des tâches qui ne rapportent presque rien, et ça n'avance pas."


def _sc(type_="texte", ecran="*80 %* des résultats", dit=DIT, **kw):
    s = {"type": type_, "emoji": "🎯", "ecran": ecran, "dit": dit, "recherche": None,
         "a": None, "b": None, "valeur_a": None, "valeur_b": None}
    s.update(kw)
    return s


def _script(scenes=None, **kw):
    s = {"accroches": [{"formule": "f", "texte": "t"}] * 3, "titre": "La loi de Pareto", "question": "Et toi ?",
         "legende": "Une ligne.", "hashtags": ["psychologie"],
         "scenes": scenes or [_sc("accroche", "Tu travailles *trop* pour rien ?")] + [_sc() for _ in range(14)]}
    s.update(kw)
    return s


def test_controle_accepte_un_bon_script():
    assert controler(_script(), SOURCE) == []


def test_controle_exige_l_accroche_en_premier():
    assert any("accroche" in p for p in controler(_script(scenes=[_sc() for _ in range(15)]), SOURCE))


def test_controle_refuse_chiffre_invente():
    scenes = [_sc("accroche", "Accroche")] + [_sc(ecran="73 % des gens") for _ in range(14)]
    assert any("73" in p for p in controler(_script(scenes=scenes), SOURCE))


def test_controle_refuse_etude():
    scenes = [_sc("accroche", "Accroche")] + [_sc(dit="Une étude a montré que ça marche, vraiment, je te le dis.") for _ in range(14)]
    assert any("étude" in p for p in controler(_script(scenes=scenes), SOURCE))


def test_controle_refuse_trop_court():
    scenes = [_sc("accroche", "Accroche")] + [_sc(dit="Court.") for _ in range(14)]
    assert any("trop court" in p for p in controler(_script(scenes=scenes), SOURCE))


def test_controle_refuse_commentaire_dans_les_scenes():
    scenes = [_sc("accroche", "Accroche")] + [_sc() for _ in range(13)] + [_sc(dit="Dis-le moi en commentaire, " + DIT)]
    assert any("commentaire" in p for p in controler(_script(scenes=scenes), SOURCE))


def test_controle_comparaison_complete():
    scenes = [_sc("accroche", "Accroche")] + [_sc() for _ in range(13)] + [_sc("comparaison", "Perte vs gain", a="Perdre")]
    assert any("comparaison" in p for p in controler(_script(scenes=scenes), SOURCE))


def test_rotation_des_categories():
    publies, vus = [], []
    for _ in range(len(CATEGORIES) * 2):
        s, _ = prochain(publies)
        publies.append(s[0])
        vus.append(s[1])
    assert len(set(publies)) == len(publies)
    assert all(a != b for a, b in zip(vus, vus[1:]))


def test_cycle_complet_puis_recommence_avec_un_angle():
    s, angle = prochain([s[0] for s in SUJETS])
    assert s[0] in PAR_ID and angle


def test_creneaux_de_la_semaine():
    mardi_14h = datetime(2026, 10, 27, 13, 0, tzinfo=timezone.utc)  # 14 h à Paris
    c = creneaux_semaine(CFG, mardi_14h, set())
    assert len(c) == 21  # mardi 18 h 30 (14 h + 3 h de production) jusqu'au mardi suivant 12 h 30 inclus
    assert c[0].isoformat().startswith("2026-10-27T18:30") and c[-1].isoformat().startswith("2026-11-03T12:30")
    assert len(creneaux_semaine(CFG, mardi_14h, {x.isoformat() for x in c[:5]})) == 16


def test_moment(tmp_path):
    etat = EtatPerso(tmp_path / "p.json")
    lundi_matin = datetime(2026, 10, 26, 8, 0, tzinfo=timezone.utc)
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
