from datetime import datetime, timezone

import agent.reponses_facebook as R


class J:
    def __init__(self, d):
        self.d = d
        self.sauve = 0

    def sauver(self):
        self.sauve += 1


class Rep:
    def __init__(self, j):
        self.j = j

    def json(self):
        return self.j


def test_video_id():
    assert R.video_id("https://www.facebook.com/123/videos/1161470126851854") == "1161470126851854"
    assert R.video_id("https://www.facebook.com/reel/1808105007077130/") == "1808105007077130"
    assert R.video_id("https://www.facebook.com/watch/?v=1812805096535964") == "1812805096535964"
    assert R.video_id("https://www.tiktok.com/@d/video/1") is None


def test_choisir_seulement_les_commentaires_recopies_sans_lien():
    publics = [{"id": "1", "texte": "C'est pour chacun ou à partager ?"}, {"id": "2", "texte": "Arnaque !!"},
               {"id": "3", "texte": "c’est pour chacun ou à partager"}, {"id": "4", "texte": "le lien ? www.x.com"},
               {"id": "5", "texte": "Le lien ?"}]
    copies = ["C'est pour chacun ou à partager ?", "le lien ? www.x.com", "le lien ?"]
    assert [c["id"] for c in R.choisir(copies, publics)] == ["1", "3", "5"]
    assert [c["id"] for c in R.choisir(copies, publics, {"1"})] == ["3", "5"]


def test_a_suivre_seulement_les_reponses_facebook():
    a = {"editorial_type": "reponse", "reponse": {"plateformes": ["facebook"], "video_origine": "u",
                                                   "commentaires": ["a ?", "b ?"], "reponse": "Phrase."}}
    assert R.a_suivre(a) == {"origine": "u", "commentaires": ["a ?", "b ?"], "phrase": "Phrase.", "faits": []}
    assert R.a_suivre({**a, "reponse": {**a["reponse"], "plateformes": ["tiktok"]}}) is None
    assert R.a_suivre({"editorial_type": "news"}) is None


def _journal(quand="2026-11-13T09:15:00+00:00"):
    return J({"art-1": {"facebook_shorts": {
        "statut": "programme", "post_id": "999", "programme_pour": quand, "titre": "Réponse",
        "reponse_fb": {"origine": "https://www.facebook.com/1/videos/123456789", "commentaires": ["Pour qui ?", "pour qui"],
                       "phrase": "Chacun doit recevoir 275 000 FCFA, selon le Minepat.", "faits": []}}}})


def test_repondre_sous_les_commentaires_une_fois(monkeypatch):
    monkeypatch.setenv("META_PAGE_TOKEN", "x")
    envois = []

    def get(url, params=None, timeout=None):
        if url.endswith("/999"):
            return Rep({"published": True, "permalink_url": "/reel/999/"})
        return Rep({"data": [{"id": "c1", "message": "Pour qui ?"}, {"id": "c2", "message": "nul"},
                             {"id": "c3", "message": "pour qui"}]})

    monkeypatch.setattr(R.requests, "get", get)
    monkeypatch.setattr(R.requests, "post", lambda url, data=None, timeout=None: envois.append((url, data["message"])) or Rep({"id": "r"}))
    j = _journal()
    cfg = {"meta": {"version_api": "v25.0"}}
    now = datetime(2026, 11, 13, 10, 0, tzinfo=timezone.utc)
    assert R.repondre(cfg, j, log=lambda m: None, maintenant=now) == 2
    assert [u.rsplit("/", 2)[-2] for u, _ in envois] == ["c1", "c3"]
    assert envois[0][1] == ("Chacun doit recevoir 275 000 FCFA, selon le Minepat.\n\n"
                            "La réponse en vidéo : https://www.facebook.com/reel/999/")
    assert R.repondre(cfg, j, log=lambda m: None, maintenant=now) == 0  # terminé : pas de seconde réponse
    assert len(envois) == 2


def test_attend_que_la_video_soit_en_ligne(monkeypatch):
    monkeypatch.setenv("META_PAGE_TOKEN", "x")
    monkeypatch.setattr(R.requests, "get", lambda url, params=None, timeout=None: Rep({"published": False}))
    monkeypatch.setattr(R.requests, "post", lambda *a, **k: (_ for _ in ()).throw(AssertionError("pas d'envoi")))
    j = _journal()
    now = datetime(2026, 11, 13, 10, 0, tzinfo=timezone.utc)
    assert R.repondre({"meta": {"version_api": "v25.0"}}, j, log=lambda m: None, maintenant=now) == 0
    assert "termine" not in j.d["art-1"]["facebook_shorts"]["reponse_fb"]
    # horaire pas encore passé : on ne regarde même pas
    j2 = _journal("2026-11-13T11:00:00+00:00")
    assert R.repondre({"meta": {"version_api": "v25.0"}}, j2, log=lambda m: None, maintenant=now) == 0
