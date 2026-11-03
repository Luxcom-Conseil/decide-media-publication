import json
from datetime import date

from agent.controle_lot import controler, diagnostiquer, titre_alerte
from agent.sources import Dossier, Fichier

JOUR = date(2026, 11, 4)
NOM = JOUR.isoformat()


def article(i):
    return {"id": f"a{i}", "status": "ready", "title": f"Titre {i}", "content_type": "news", "post_text": "Texte",
            "platform_texts": {"facebook": "Texte FB"}, "image_file": {"id": f"img{i}", "name": "x.png"}}


def lot_pret():
    return {"protocol_version": "2.0", "date": NOM, "status": "ready", "article_count": 5,
            "required_article_count": 5, "delivery_deadline": "x", "delivered_on_time": True, "completed_at": "x",
            "articles": [article(i) for i in range(1, 6)]}


class FauxDrive:
    def __init__(self, dossiers=(), manifeste=None):
        self.dossiers = list(dossiers)
        self.manifeste = manifeste

    def lister_dossiers(self):
        return [Dossier(n, n) for n in self.dossiers]

    def lister_fichiers(self, dossier):
        return [] if self.manifeste is None else [Fichier("m", "manifest.json", "")]

    def lire_brut(self, fichier):
        return self.manifeste if isinstance(self.manifeste, bytes) else json.dumps(self.manifeste).encode()


class FaussesIssues:
    def __init__(self, existante=None):
        self.existante = existante
        self.ouvertes = []
        self.refermees = []

    def trouver(self, titre):
        return self.existante

    def ouvrir(self, titre, corps):
        self.ouvertes.append((titre, corps))
        return {"html_url": "https://exemple/1"}

    def refermer(self, numero, message):
        self.refermees.append(numero)


def test_diagnostic():
    assert "Aucun dossier" in diagnostiquer(FauxDrive(["2026-11-03", "2026-11-04_TEST"]), JOUR)
    assert "manifest.json" in diagnostiquer(FauxDrive([NOM]), JOUR)
    assert "illisible" in diagnostiquer(FauxDrive([NOM], {"status": "failed", "issues": ["illisible"]}), JOUR)
    assert "contrôles" in diagnostiquer(FauxDrive([NOM], b"{pas du json"), JOUR)
    assert "contrôles" in diagnostiquer(FauxDrive([NOM], {**lot_pret(), "article_count": 4}), JOUR)
    assert diagnostiquer(FauxDrive([NOM], lot_pret()), JOUR) is None


def test_alerte_ouverte_une_seule_fois():
    issues = FaussesIssues()
    controler(FauxDrive(), issues, JOUR, lambda _: None)
    assert [t for t, _ in issues.ouvertes] == [titre_alerte(JOUR)]
    assert "Aucun dossier" in issues.ouvertes[0][1]

    issues = FaussesIssues(existante={"number": 7, "state": "open", "html_url": "u"})
    controler(FauxDrive(), issues, JOUR, lambda _: None)
    assert issues.ouvertes == [] and issues.refermees == []


def test_lot_arrive_referme_l_alerte():
    issues = FaussesIssues(existante={"number": 7, "state": "open", "html_url": "u"})
    controler(FauxDrive([NOM], lot_pret()), issues, JOUR, lambda _: None)
    assert issues.refermees == [7] and issues.ouvertes == []


def test_lot_present_sans_alerte_ne_fait_rien():
    issues = FaussesIssues()
    controler(FauxDrive([NOM], lot_pret()), issues, JOUR, lambda _: None)
    assert issues.ouvertes == [] and issues.refermees == []


def test_simulation_n_ouvre_rien():
    journal = []
    controler(FauxDrive(), None, JOUR, journal.append, simulation=True)
    assert "Aucun dossier" in journal[0]
