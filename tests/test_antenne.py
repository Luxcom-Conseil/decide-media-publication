"""Antenne DECIDE MEDIA Burkina : réglages superposés, identifiants séparés, créneaux à l'heure de Ouagadougou,
YouTube par Buffer. Le Cameroun (sans antenne) ne doit pas changer."""
from datetime import date, datetime, timezone
from pathlib import Path
from zoneinfo import ZoneInfo

import pytest

from agent.config import appliquer_antenne, charger_config
from agent.lots import creneaux
from agent.publieurs.buffer import BufferYouTube

RACINE = Path(__file__).parent.parent


@pytest.fixture
def cfg():
    return charger_config(RACINE / "config.yaml")


def test_le_cameroun_ne_change_pas(cfg):
    assert cfg["lots"]["dossier_drive"] == "1T_1QBeDbS1GIgHY2UsZsNnN3wJu5Cmwa"
    assert cfg["lots"]["fuseau_creneaux"] == "Africa/Douala"
    assert "youtube" in cfg["lots"]["reseaux"] and "youtube_buffer" not in cfg["lots"]["reseaux"]
    assert "antenne" not in cfg


def test_burkina_remplace_drive_reseaux_fuseau_et_chaines(cfg):
    b = appliquer_antenne(cfg, "burkina")
    assert b["lots"]["dossier_drive"] != cfg["lots"]["dossier_drive"]
    assert b["lots"]["reseaux"] == ["youtube_bf", "tiktok_buffer"]  # YouTube en direct depuis le 23/11/2026
    assert b["lots"]["fuseau_creneaux"] == "Africa/Ouagadougou"
    assert set(b["buffer"]["canaux"]) == {"youtube_buffer", "tiktok_buffer"}  # ni X ni LinkedIn du Cameroun
    assert b["buffer"]["canaux"]["tiktok_buffer"] != cfg["buffer"]["canaux"]["tiktok_buffer"]
    assert b["antenne"]["nom"] == "burkina" and b["antenne"]["prefixe_id"] == "decide-bf-"
    assert b["antenne"]["journal"] != "etat/lots.json"
    assert (RACINE / b["antenne"]["banque_photos"] / "index.json").exists()
    assert cfg["lots"]["fuseau_creneaux"] == "Africa/Douala"  # la config d'origine n'est pas modifiée


def test_antenne_inconnue(cfg):
    with pytest.raises(KeyError):
        appliquer_antenne(cfg, "gabon")


def test_creneaux_a_l_heure_de_ouagadougou(cfg):
    b = appliquer_antenne(cfg, "burkina")
    tot = datetime(2026, 11, 23, 0, 0, tzinfo=timezone.utc)
    h = creneaux(b, date(2026, 11, 23), 2, tot, [], "youtube_bf")
    assert [x.astimezone(ZoneInfo("UTC")).strftime("%H:%M") for x in h] == ["08:00", "11:00"]  # UTC+0
    t = creneaux(b, date(2026, 11, 23), 1, tot, [], "tiktok_buffer")
    assert t[0].astimezone(ZoneInfo("UTC")).strftime("%H:%M") == "08:15"


def test_youtube_par_buffer_titre_categorie_et_shorts(cfg):
    pub = BufferYouTube(appliquer_antenne(cfg, "burkina"))
    article = {"title": "Le prix du sac de riz baisse à Ouagadougou", "platform_texts": {"youtube": "Texte YouTube"}}
    texte = pub.texte(article, "texte commun")
    assert texte.startswith("Texte YouTube") and texte.endswith("#Shorts")
    meta = pub.metadonnees()["youtube"]
    assert meta["title"] == article["title"] and meta["categoryId"] == "25" and meta["privacy"] == "public"
    assert pub.en_video({"_rang": 99})


def test_youtube_direct_burkina_a_ses_propres_identifiants(monkeypatch):
    from agent.publieurs import TOUS
    from agent.publieurs.youtube import YouTube, YouTubeBurkina
    assert TOUS["youtube_bf"] is YouTubeBurkina
    for v in YouTube.variables:
        monkeypatch.setenv(v, "cameroun")
    for v in YouTubeBurkina.variables:
        monkeypatch.delenv(v, raising=False)
    assert YouTube.est_configure() and not YouTubeBurkina.est_configure()  # jamais les identifiants du Cameroun
    assert all(v.endswith("_BURKINA") for v in YouTubeBurkina.variables)


def test_afrique_remplace_drive_reseaux_fuseau_et_est_active(cfg):
    a = appliquer_antenne(cfg, "afrique")
    assert a["lots"]["dossier_drive"] == "1TPiTLFrUdYSG1KlO23FHsfXRTNXy6E4U"
    assert a["lots"]["dossier_drive"] not in (cfg["lots"]["dossier_drive"], appliquer_antenne(cfg, "burkina")["lots"]["dossier_drive"])
    assert a["lots"]["reseaux"] == ["youtube_af", "tiktok_buffer"]  # YouTube en direct depuis le 23/11/2026
    assert a["lots"]["fuseau_creneaux"] == "Africa/Lagos"
    # TikTok Afrique = 3e chaîne du compte Buffer du Burkina (23/11/2026) : même clé, jamais la même chaîne
    bf = appliquer_antenne(cfg, "burkina")
    assert set(a["buffer"]["canaux"]) == {"tiktok_buffer"}
    assert a["antenne"]["cle_buffer"] == bf["antenne"]["cle_buffer"] == "BUFFER_API_KEY_BURKINA"
    assert a["buffer"]["canaux"]["tiktok_buffer"] not in bf["buffer"]["canaux"].values()
    assert bf["buffer"]["canaux"]["tiktok_buffer"] == "6b03621f8541f09ecb6ab6aa"
    assert a["antenne"]["prefixe_id"] == "decide-af-" and a["antenne"]["journal"] == "etat/lots_af.json"
    assert a["antenne"]["actif"] is True  # activée le 23/11/2026 après le lot test
    assert cfg["lots"]["fuseau_creneaux"] == "Africa/Douala"


def test_carte_connait_les_54_pays():
    import json
    import unicodedata
    lieux = json.loads((RACINE / "motion" / "src" / "lieux.json").read_text(encoding="utf-8"))
    pays = ["Afrique du Sud", "Algérie", "Angola", "Bénin", "Botswana", "Burkina Faso", "Burundi", "Cabo Verde", "Cameroun",
            "Centrafrique", "Comores", "Congo", "Côte d'Ivoire", "Djibouti", "Égypte", "Érythrée", "Eswatini", "Éthiopie",
            "Gabon", "Gambie", "Ghana", "Guinée", "Guinée-Bissau", "Guinée équatoriale", "Kenya", "Lesotho", "Liberia",
            "Libye", "Madagascar", "Malawi", "Mali", "Maroc", "Maurice", "Mauritanie", "Mozambique", "Namibie", "Niger",
            "Nigeria", "Ouganda", "RD Congo", "Rwanda", "Sao Tomé-et-Principe", "Sénégal", "Seychelles", "Sierra Leone",
            "Somalie", "Soudan", "Soudan du Sud", "Tanzanie", "Tchad", "Togo", "Tunisie", "Zambie", "Zimbabwe"]
    cle = lambda n: unicodedata.normalize("NFKD", n).encode("ascii", "ignore").decode().lower()
    assert len(pays) == 54 and not [p for p in pays if cle(p) not in lieux]


def test_voix_feminine_pour_l_afrique_seulement(monkeypatch):
    """Demande de Stéphane du 23/11/2026 : voix féminine pour l'Afrique ; Cameroun et Burkina gardent Schedar."""
    from agent.voix import _reglages
    monkeypatch.delenv("DECIDE_ANTENNE", raising=False)
    assert _reglages()["nom"] == "fr-FR-Chirp3-HD-Schedar" and "gemini" not in _reglages()
    monkeypatch.setenv("DECIDE_ANTENNE", "burkina")
    assert _reglages()["nom"] == "fr-FR-Chirp3-HD-Schedar" and "gemini" not in _reglages()
    monkeypatch.setenv("DECIDE_ANTENNE", "afrique")
    r = _reglages()
    assert r["gemini"] == "Kore" and r["nom"] == "fr-FR-Chirp3-HD-Kore"
    assert r["journal_tv"] and r["active"]  # le reste du bloc voix ne change pas


def test_benin_youtube_seul_son_drive_sa_banque_et_active(cfg):
    """Antenne Bénin (27/11/2026) : YouTube en direct seulement, son dossier Drive, sa banque, son journal, active
    depuis le lot test du 27/11 ; les trois autres ne changent pas."""
    b = appliquer_antenne(cfg, "benin")
    assert b["lots"]["dossier_drive"] == "1l3I2bIFPtIiqd6WNLG01pVk8Z2hqa7cR"
    assert b["lots"]["reseaux"] == ["youtube_bj"]
    assert b["lots"]["max_par_jour"]["youtube_bj"] <= 6  # quota du projet Google : environ 6 envois par jour
    assert b["lots"]["fuseau_creneaux"] == "Africa/Porto-Novo"
    assert b["antenne"]["prefixe_id"] == "decide-bj-" and b["antenne"]["journal"] == "etat/lots_bj.json"
    assert (RACINE / b["antenne"]["banque_photos"] / "index.json").exists()
    assert b["antenne"]["actif"] is True
    for autre in ("burkina", "afrique"):
        assert appliquer_antenne(cfg, autre)["lots"]["dossier_drive"] != b["lots"]["dossier_drive"]


def test_carte_connait_les_villes_du_benin():
    from agent.gabarit_v3 import lieu_connu
    for v in ("Cotonou", "Porto-Novo", "Parakou", "Abomey-Calavi", "Bohicon", "Ouidah", "Ganvié", "Malanville",
              "Djougou", "Natitingou", "Sèmè-Kpodji", "Glo-Djigbé"):
        assert lieu_connu(v), v


def test_miniature_youtube_porte_le_titre_entier():
    """Demande de Stéphane du 27/11/2026 : la miniature annonce clairement le titre ; chiffre et unité restent d'un bloc."""
    from agent.gabarit_v3 import miniature_titre
    assert miniature_titre({"title": "PIB : +7,7 % sur un an"}) == "PIB : +7,7 % sur un an"
    assert miniature_titre({"title": "Le bidon passe à 18 000 FCFA"}).endswith("18 000 FCFA")
    assert miniature_titre({}, "Titre du script") == "Titre du script"
    assert "*" not in miniature_titre({"title": "Le *prix* <b>baisse</b>"})
