"""Point d'entrée : python -m agent [publier|verifier] [--simulation] [--source-locale DOSSIER] [--sans-ia]"""
from __future__ import annotations

import argparse
import os
import sys

from .config import charger_config
from .etat import Etat
from .ia import Redacteur
from .orchestrateur import Journal, executer
from .publieurs import TOUS
from .sources import SourceDrive, SourceLocale


def _publieurs(cfg: dict, log) -> dict:
    actifs = {}
    for nom, classe in TOUS.items():
        if classe.est_configure():
            actifs[nom] = classe(cfg)
        else:
            log(f"  (réseau {nom} non configuré — manque : {', '.join(classe.manquantes())})")
    return actifs


def _charger_env(chemin: str = ".env") -> None:
    """Sur un ordinateur : lit les secrets dans .env (CLE=valeur). Sur GitHub, ce sont les Secrets du dépôt."""
    if not os.path.exists(chemin):
        return
    with open(chemin, encoding="utf-8-sig") as f:
        for ligne in f:
            ligne = ligne.strip()
            if ligne and not ligne.startswith("#") and "=" in ligne:
                cle, valeur = ligne.split("=", 1)
                os.environ.setdefault(cle.strip(), valeur.strip().strip('"').strip("'"))


def _resume_github(log: Journal) -> None:
    chemin = os.environ.get("GITHUB_STEP_SUMMARY")
    if chemin:
        with open(chemin, "a", encoding="utf-8") as f:
            f.write("## Passage de l'agent de publication\n\n```\n" + "\n".join(log.lignes) + "\n```\n")


def main(argv: list[str] | None = None) -> int:
    for flux in (sys.stdout, sys.stderr):  # emojis lisibles même dans une console Windows
        if hasattr(flux, "reconfigure"):
            flux.reconfigure(encoding="utf-8")
    _charger_env()

    p = argparse.ArgumentParser(prog="agent", description="Publie sur les réseaux sociaux le contenu d'un dossier Drive.")
    p.add_argument("commande", nargs="?", default="publier",
                   choices=["publier", "verifier", "lots", "essai-video", "perso", "perso-essai", "perso-planifier",
                            "perso-rendre", "perso-heberger", "perso-publier"],
                   help="publier = dossiers « post » ; lots = lots quotidiens DECIDE MEDIA ; verifier = tester les accès ; "
                        "essai-video = fabriquer un Short d'essai dans sortie/, sans publier ; perso-essai = fabriquer un "
                        "Reel Instagram perso dans sortie/, sans publier ; perso-planifier / perso-rendre / "
                        "perso-heberger = production de la semaine (sortie/perso/) ; perso-publier = publier les Reels "
                        "dont l'heure est venue")
    p.add_argument("--lot", type=int, default=0, help="perso-rendre : numéro du lot à fabriquer (0, 1, …)")
    p.add_argument("--lots", type=int, default=1, help="perso-rendre : nombre de lots fabriqués en parallèle")
    p.add_argument("--simulation", action="store_true", help="montre ce qui serait publié, sans rien publier")
    p.add_argument("--source-locale", metavar="DOSSIER", help="lire un dossier local au lieu de Google Drive")
    p.add_argument("--sans-ia", action="store_true", help="ne pas appeler Claude (texte d'origine)")
    p.add_argument("--jours", type=int, help="lots : examiner aussi les N jours précédents (sinon config.yaml)")
    p.add_argument("--config", default="config.yaml")
    p.add_argument("--etat", default="etat/etat.json")
    a = p.parse_args(argv)

    simulation = a.simulation or os.environ.get("SIMULATION", "").lower() in ("1", "true", "oui")
    cfg = charger_config(a.config)
    os.environ.setdefault("DRIVE_FOLDER_ID", cfg["lots"]["dossier_drive"])
    if a.jours is not None:
        cfg["lots"]["jours_max"] = a.jours
    log = Journal()
    publieurs = _publieurs(cfg, log)

    if a.commande == "verifier":
        ok = True
        for nom, pub in publieurs.items():
            try:
                log(f"✅ {nom} : {pub.verifier()}")
            except Exception as e:
                ok = False
                log(f"❌ {nom} : {e}")
        if not a.source_locale:
            try:
                n = len(SourceDrive.depuis_env().lister_dossiers())
                log(f"✅ Google Drive : dossier accessible ({n} sous-dossier(s))")
            except BaseException as e:
                ok = False
                log(f"❌ Google Drive : {e}")
        log("✅ IA : clé Anthropic présente" if Redacteur.disponible(cfg) else "➖ IA : désactivée ou clé absente")
        from .publieurs.instagram_perso import InstagramPerso
        if InstagramPerso.est_configure():
            try:
                log(f"✅ instagram_perso : {InstagramPerso(cfg, log).verifier()}")
            except Exception as e:
                ok = False
                log(f"❌ instagram_perso : {e}")
        else:
            log("➖ instagram_perso : jeton pas encore enregistré (INSTAGRAM_PERSO_TOKEN)")
        _resume_github(log)
        return 0 if ok else 1

    if a.commande == "essai-video":
        from pathlib import Path

        from .essai_video import essai_video

        ok = essai_video(SourceDrive.depuis_env(), Path("sortie"), log)
        _resume_github(log)
        return 0 if ok else 1

    if a.commande.startswith("perso"):
        import json
        from pathlib import Path

        from . import perso

        plan_json = Path("sortie/perso/plan.json")
        if a.commande == "perso-planifier":
            ok = bool(perso.planifier(cfg, log, chemin=plan_json)) or True
        elif a.commande == "perso-rendre":  # les Reels du lot a.lot sur a.lots (un Reel sur a.lots, en alternance)
            plan = json.loads(plan_json.read_text(encoding="utf-8"))[a.lot::a.lots]
            ok = perso.produire(cfg, plan, log, Path(f"sortie/perso/lot{a.lot}"))
        elif a.commande == "perso-heberger":
            ok = perso.heberger(cfg, log, Path("sortie/perso")) >= 0
        elif a.commande == "perso-publier":
            ok = perso.publier_dus(cfg, log)
        else:
            ok = perso.traiter_perso(cfg, log, simulation=simulation, essai=a.commande == "perso-essai")
        _resume_github(log)
        return 0 if ok else 1

    if a.commande == "lots":
        from .lots import Journal as JournalLots, traiter_lots

        os.environ.setdefault("DRIVE_FOLDER_ID", cfg["lots"]["dossier_drive"])
        traiter_lots(cfg, SourceDrive.depuis_env(), publieurs, JournalLots(), log, simulation=simulation)
        _resume_github(log)
        # point de contrôle : un vrai échec rend le passage « rouge » sur GitHub, qui prévient alors par e-mail
        return 1 if any("❌" in ligne for ligne in log.lignes) else 0

    source = SourceLocale(a.source_locale) if a.source_locale else SourceDrive.depuis_env()
    redacteur = None
    if not a.sans_ia and Redacteur.disponible(cfg):
        redacteur = Redacteur(cfg)
    executer(cfg, source, publieurs, Etat(a.etat), redacteur=redacteur, dry_run=simulation, journal=log)
    _resume_github(log)
    return 0


if __name__ == "__main__":
    sys.exit(main())
