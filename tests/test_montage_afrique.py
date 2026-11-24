"""Montage Afrique (demande de Stéphane du 23/11/2026) : drapeau, carte d'ouverture, photos du pays, portraits, accroche.
Le Cameroun et le Burkina (sans DECIDE_ANTENNE=afrique) ne changent pas."""
import json

import pytest

from agent import gabarit_v3 as g


def _scenes():
    return [{"type": "accroche"}, {"type": "explication", "illustration": {"type": "photo"}},
            {"type": "explication", "illustration": {"type": "pourcent"}}]


def test_drapeaux_des_54_pays_et_de_l_ua():
    from pathlib import Path
    index = json.loads((g.DRAPEAUX / "index.json").read_text(encoding="utf-8"))
    assert len(index) == 55 and all(e["licence"] == "Public domain" for e in index.values())
    assert all((g.DRAPEAUX / e["fichier"]).exists() for e in index.values())
    assert g.drapeau_de("Égypte") == "drapeaux/egypte.png"
    assert g.drapeau_de("Côte d'Ivoire") and g.drapeau_de("RD Congo") and g.drapeau_de("Afrique")
    assert g.drapeau_de("Atlantide") is None


def test_ouverture_pays_met_carte_et_drapeau_apres_l_accroche():
    sc = _scenes()
    g.ouverture_pays(sc, {"country": "Égypte"}, "drapeaux/egypte.png", lambda *_: None)
    assert sc[1]["illustration"] == {"type": "carte", "texte": "Égypte"} and sc[1]["drapeau"] == "drapeaux/egypte.png"
    assert sc[2]["illustration"]["type"] == "pourcent"  # un dessin chiffré n'est pas écrasé


def test_ouverture_pays_garde_un_dessin_chiffre():
    sc = [{"type": "accroche"}, {"type": "explication", "illustration": {"type": "pile"}},
          {"type": "explication", "illustration": {"type": "photo"}}]
    g.ouverture_pays(sc, {"country": "Kenya"}, None, lambda *_: None)
    assert sc[1]["illustration"]["type"] == "pile" and sc[2]["illustration"]["type"] == "carte"


def test_portrait_jamais_pour_un_fait_negatif(monkeypatch, tmp_path):
    (tmp_path / "index.json").write_text(json.dumps([{"nom": "Paul Kagame", "variantes": [], "fichier": "x.jpg", "credit": "c"}]),
                                         encoding="utf-8")
    monkeypatch.setattr(g, "PORTRAITS", tmp_path)
    assert [e["nom"] for e in g.portraits_cites({"title": "", "body": "Paul Kagame a inauguré le pont."})] == ["Paul Kagame"]
    assert g.portraits_cites({"title": "", "body": "Paul Kagame est accusé par un rapport."}) == []


def test_secours_afrique_ouvre_sur_la_phrase_du_chiffre(monkeypatch):
    art = {"title": "T", "etiquette_chiffre": {"texte": "2,3 milliards"},
           "body": "Le FMI et l'Égypte ont conclu un accord sur le dernier examen du programme. "
                   "L'Égypte recevrait environ 2,3 milliards de dollars si le conseil approuve. Rien n'est versé pour l'instant.",
           "accroche_appui": "L'Égypte recevrait environ 2,3 milliards de dollars si le conseil approuve."}
    monkeypatch.setenv("DECIDE_ANTENNE", "afrique")
    assert g.script_secours(art)["scenes"][0]["dit"].startswith("L'Égypte recevrait")
    monkeypatch.delenv("DECIDE_ANTENNE")
    assert g.script_secours(art)["scenes"][0]["dit"].startswith("Le FMI")  # Cameroun et Burkina : comme avant


def test_sans_antenne_afrique_rien_ne_change(monkeypatch):
    monkeypatch.delenv("DECIDE_ANTENNE", raising=False)
    assert not g.antenne_afrique()
