from datetime import datetime, timezone
from pathlib import Path

from PIL import Image

from agent.config import charger_config
from agent.etat import Etat
from agent.orchestrateur import executer
from agent.publieurs import ErreurPublication, Publieur, Resultat
from agent.publieurs.meta import Instagram, preparer_image_instagram
from agent.sources import SourceLocale

MAINTENANT = datetime(2026, 10, 20, 8, 0, tzinfo=timezone.utc)  # 10h00 à Paris


class Faux(Publieur):
    def __init__(self, nom, echecs=0):
        super().__init__({})
        self.nom, self.echecs, self.appels = nom, echecs, []

    def publier(self, post, texte):
        self.appels.append((texte, [m.nom for m in post.medias]))
        if self.echecs:
            self.echecs -= 1
            raise ErreurPublication("panne temporaire")
        return Resultat(f"https://{self.nom}/post/{len(self.appels)}")


class FauxInstagram(Faux):
    valider = Instagram.valider


def dossier(racine: Path, nom: str, post: str, medias=()):
    d = racine / nom
    d.mkdir()
    (d / "post.txt").write_text(post, encoding="utf-8")
    for m in medias:
        Image.new("RGB", (400, 1000), "red").save(d / m)
    return d


def lancer(racine, pubs, etat, **kw):
    return executer(charger_config("inexistant.yaml"), SourceLocale(racine), pubs, etat,
                    maintenant=kw.pop("maintenant", MAINTENANT), **kw)


def test_publie_ce_qui_est_du_et_attend_le_reste(tmp_path):
    src = tmp_path / "drive"
    src.mkdir()
    dossier(src, "A passé", "date: 20/10/2026 09:30\nreseaux: facebook, x\n---\nBonjour\n[x]\nCourt",
            ["2.jpg", "1.jpg", "miniature.jpg"])
    dossier(src, "B futur", "date: 21/10/2026 09:30\nreseaux: facebook\n---\nDemain")
    (src / "C brouillon").mkdir()
    dossier(src, "_modèle", "reseaux: x\n---\nignoré")

    fb, x = Faux("facebook"), Faux("x")
    etat = Etat(tmp_path / "etat.json")
    lancer(src, {"facebook": fb, "x": x}, etat)

    assert fb.appels == [("Bonjour", ["1.jpg", "2.jpg"])]  # miniature exclue, ordre alphabétique
    assert x.appels[0][0] == "Court"  # version écrite à la main prioritaire
    assert (src / "[PUBLIÉ] A passé" / "_rapport.txt").read_text(encoding="utf-8").count("✅") == 2
    assert (src / "B futur").exists() and (src / "C brouillon").exists()

    # Second passage : rien n'est republié
    lancer(src, {"facebook": fb, "x": x}, Etat(tmp_path / "etat.json"))
    assert len(fb.appels) == 1 and len(x.appels) == 1


def test_reessaie_puis_partiel(tmp_path):
    src = tmp_path / "drive"
    src.mkdir()
    dossier(src, "P", "date: maintenant\nreseaux: facebook, linkedin, youtube\n---\nTexte")
    fb, li = Faux("facebook"), Faux("linkedin", echecs=99)
    etat = Etat(tmp_path / "etat.json")
    for _ in range(3):
        lancer(src, {"facebook": fb, "linkedin": li}, etat)
    assert len(fb.appels) == 1 and len(li.appels) == 3
    rapport = (src / "[PARTIEL] P" / "_rapport.txt").read_text(encoding="utf-8")
    assert "✅ facebook" in rapport and "❌ linkedin : panne temporaire" in rapport
    assert "➖ youtube : réseau non configuré" in rapport


def test_reussit_au_deuxieme_essai(tmp_path):
    src = tmp_path / "drive"
    src.mkdir()
    dossier(src, "P", "reseaux: x\n---\nT")
    x = Faux("x", echecs=1)
    etat = Etat(tmp_path / "etat.json")
    lancer(src, {"x": x}, etat)
    assert (src / "P").exists()
    lancer(src, {"x": x}, etat)
    assert (src / "[PUBLIÉ] P").exists()


def test_instagram_sans_visuel_echoue_sans_reessayer(tmp_path):
    src = tmp_path / "drive"
    src.mkdir()
    dossier(src, "P", "reseaux: instagram\n---\nT")
    ig = FauxInstagram("instagram")
    lancer(src, {"instagram": ig}, Etat(tmp_path / "e.json"))
    assert not ig.appels
    assert "exige au moins une image" in (src / "[ÉCHEC] P" / "_rapport.txt").read_text(encoding="utf-8")


def test_trop_en_retard(tmp_path):
    src = tmp_path / "drive"
    src.mkdir()
    dossier(src, "Vieux", "date: 01/10/2026 09:00\nreseaux: x\n---\nT")
    x = Faux("x")
    lancer(src, {"x": x}, Etat(tmp_path / "e.json"))
    assert not x.appels and (src / "[ÉCHEC] Vieux").exists()


def test_format_invalide_signale_sans_bloquer(tmp_path):
    src = tmp_path / "drive"
    src.mkdir()
    dossier(src, "Cassé", "date: 20/10/2026\nreseaux: x\nTexte sans séparateur")
    dossier(src, "Bon", "reseaux: x\n---\nT")
    x = Faux("x")
    lancer(src, {"x": x}, Etat(tmp_path / "e.json"))
    assert "Format invalide" in (src / "Cassé" / "_rapport.txt").read_text(encoding="utf-8")
    assert (src / "[PUBLIÉ] Bon").exists()


def test_simulation_ne_touche_a_rien(tmp_path):
    src = tmp_path / "drive"
    src.mkdir()
    dossier(src, "P", "reseaux: x\n---\nT")
    x = Faux("x")
    lancer(src, {"x": x}, Etat(tmp_path / "e.json"), dry_run=True)
    assert not x.appels and (src / "P").exists() and not (tmp_path / "e.json").exists()


def test_relance_en_retirant_le_prefixe(tmp_path):
    src = tmp_path / "drive"
    src.mkdir()
    dossier(src, "P", "date: 18/10/2026 09:00\nreseaux: facebook, linkedin\n---\nTexte")
    fb, li = Faux("facebook"), Faux("linkedin", echecs=3)
    etat = Etat(tmp_path / "e.json")
    for _ in range(3):
        lancer(src, {"facebook": fb, "linkedin": li}, etat, maintenant=datetime(2026, 10, 18, 8, tzinfo=timezone.utc))
    (src / "[PARTIEL] P").rename(src / "P")  # l'utilisateur a corrigé son jeton LinkedIn
    lancer(src, {"facebook": fb, "linkedin": li}, etat)  # 2 jours plus tard : relance quand même
    assert len(fb.appels) == 1 and len(li.appels) == 4
    assert (src / "[PUBLIÉ] P").exists()

    (src / "[PUBLIÉ] P").rename(src / "P")  # tout est publié : jamais de doublon
    lancer(src, {"facebook": fb, "linkedin": li}, etat)
    assert len(fb.appels) == 1 and len(li.appels) == 4


def test_simulation_apercu_futur_et_non_configure(tmp_path):
    src = tmp_path / "drive"
    src.mkdir()
    dossier(src, "Futur", "date: 01/12/2026 09:00\nreseaux: x, youtube\ntitre: Ma vidéo\n---\nBonjour", ["v.jpg"])
    log = lancer(src, {"x": Faux("x")}, Etat(tmp_path / "e.json"), dry_run=True)
    sortie = "\n".join(log.lignes)
    assert "programmé le 01/12/2026 09:00 — aperçu" in sortie
    assert "── youtube  (non configuré)" in sortie and "TITRE : Ma vidéo" in sortie
    assert "1 image(s)" in sortie and (src / "Futur").exists()


def test_ia_utilisee_sauf_versions_manuelles(tmp_path):
    src = tmp_path / "drive"
    src.mkdir()
    dossier(src, "P", "reseaux: facebook, x\n---\nCommun\n[x]\nManuel X")

    class FauxRedacteur:
        demandes = None

        def adapter(self, post, reseaux):
            self.demandes = reseaux
            return {"facebook": "Version IA"}

    red = FauxRedacteur()
    fb, x = Faux("facebook"), Faux("x")
    lancer(src, {"facebook": fb, "x": x}, Etat(tmp_path / "e.json"), redacteur=red)
    assert red.demandes == ["facebook"]
    assert fb.appels[0][0] == "Version IA" and x.appels[0][0] == "Manuel X"


def test_image_instagram_ratio(tmp_path):
    src = tmp_path / "haute.png"
    Image.new("RGBA", (400, 1000), "red").save(src)
    out = Image.open(preparer_image_instagram(src, tmp_path))
    assert out.format == "JPEG" and abs(out.width / out.height - 0.8) < 0.01
