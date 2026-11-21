import agent.gabarit_v3 as g


def test_un_script_juste_mais_court_est_garde_plutot_que_le_secours(monkeypatch, tmp_path):
    # lot test du 21/11/2026 : trois refus « voix trop courte », puis le secours lisait moins encore
    monkeypatch.setenv("GEMINI_API_KEY", "x")
    longueurs = iter([600, 800, 700])
    monkeypatch.setattr(g, "_demander_gemini", lambda a, c, r: {"n": next(longueurs)})
    monkeypatch.setattr(g, "_reparer", lambda e: {"scenes": [{"dit": "a" * e["n"]}]})
    monkeypatch.setattr(g, "controler_v3", lambda e, a: ["voix trop courte (… caractères)"])
    ecrit = g.script_v3({"id": "t"}, {}, journal=lambda *_: None, cache=tmp_path)
    assert len(ecrit["scenes"][0]["dit"]) == 800 and (tmp_path / "t.json").exists()


def test_un_autre_defaut_garde_le_refus(monkeypatch):
    monkeypatch.setenv("GEMINI_API_KEY", "x")
    monkeypatch.setattr(g, "_demander_gemini", lambda a, c, r: {})
    monkeypatch.setattr(g, "_reparer", lambda e: {"scenes": []})
    monkeypatch.setattr(g, "controler_v3", lambda e, a: ["voix trop courte (…)", "chiffres absents de l'article : 13"])
    assert g.script_v3({"id": "t"}, {}, journal=lambda *_: None) is None
