"""Un passage de l'agent : parcourt les dossiers, publie ce qui est dû, consigne le résultat."""
from __future__ import annotations

import tempfile
from datetime import datetime, timedelta, timezone
from pathlib import Path

from .etat import Etat
from .models import Media, Post, est_miniature, type_media
from .parser import ErreurFormat, parser_post
from .publieurs import TOUS, ErreurDefinitive, Publieur
from .publieurs.x import couper_pour_x
from .sources import Dossier, Source

PREFIXES_IGNORES = ("[", "_", ".")


class Journal:
    def __init__(self):
        self.lignes: list[str] = []

    def __call__(self, msg: str) -> None:
        print(msg, flush=True)
        self.lignes.append(msg)


def _rapport(entree: dict) -> str:
    lignes = []
    for reseau, r in sorted(entree["reseaux"].items()):
        if r.get("statut") == "ok":
            lignes.append(f"✅ {reseau} : {r['url']}")
        elif r.get("statut") == "ignore":
            lignes.append(f"➖ {reseau} : {r['erreur']}")
        else:
            lignes.append(f"❌ {reseau} : {r.get('erreur', '')}")
    return "\n".join(lignes)


def executer(cfg: dict, source: Source, publieurs: dict[str, Publieur], etat: Etat, *,
             redacteur=None, dry_run: bool = False, maintenant: datetime | None = None,
             journal: Journal | None = None) -> Journal:
    log = journal or Journal()
    maintenant = maintenant or datetime.now(timezone.utc)
    max_essais = int(cfg["tentatives_max"])
    retard_max = timedelta(hours=float(cfg["retard_max_heures"]))

    dossiers = source.lister_dossiers()
    log(f"{len(dossiers)} dossier(s) trouvé(s) — {maintenant.astimezone().strftime('%d/%m/%Y %H:%M')}"
        + ("  [SIMULATION : rien ne sera publié]" if dry_run else ""))

    for dossier in dossiers:
        if dossier.nom.startswith(PREFIXES_IGNORES):
            continue
        if etat.est_termine(dossier.id) and not _relancer(etat, dossier, log):
            continue
        try:
            _traiter(cfg, source, publieurs, etat, dossier, redacteur, dry_run, maintenant,
                     max_essais, retard_max, log)
        except Exception as e:  # un dossier en erreur ne doit jamais bloquer les suivants
            log(f"  ❌ erreur inattendue sur « {dossier.nom} » : {e}")
    return log


def _traiter(cfg, source: Source, publieurs, etat: Etat, dossier: Dossier, redacteur, dry_run,
             maintenant, max_essais, retard_max, log) -> None:
    fichiers = source.lister_fichiers(dossier)
    f_post = source.trouver_post(fichiers, cfg["fichiers_post"])
    if not f_post:
        log(f"• {dossier.nom} : pas encore de fichier « post » — ignoré")
        return

    try:
        post = parser_post(source.lire_texte(f_post), cfg["fuseau_horaire"])
    except ErreurFormat as e:
        log(f"• {dossier.nom} : ⚠ format invalide — {e}")
        entree = etat.post(dossier.id, dossier.nom)
        message = f"⚠ Format invalide : {e}"
        if entree.get("derniere_alerte") != message and not dry_run:
            source.marquer(dossier, None, message)  # alerte visible dans la description du dossier Drive
            entree["derniere_alerte"] = message
            etat.sauver()
        return

    quand = post.date.strftime("%d/%m/%Y %H:%M") if post.date else "dès que possible"
    futur = bool(post.date and post.date > maintenant)
    if futur and not dry_run:
        log(f"• {dossier.nom} : programmé le {quand} — en attente")
        return

    entree = etat.post(dossier.id, dossier.nom)
    entree.pop("derniere_alerte", None)
    if dry_run:
        # Simulation : aperçu de tous les réseaux demandés, même futurs ou pas encore configurés.
        log(f"• {dossier.nom} : {'programmé le ' if futur else 'à publier '}{quand} — aperçu")
        with tempfile.TemporaryDirectory() as tmp:
            _charger_medias(source, fichiers, post, Path(tmp))
            log(f"    médias : {len(post.images)} image(s), {len(post.videos)} vidéo(s)"
                + (", 1 miniature" if post.miniature else ""))
            textes = _rediger(post, post.reseaux, redacteur, log)
        for r in post.reseaux:
            texte = textes.get(r, post.texte)
            statut = "" if r in publieurs else "  (non configuré)"
            if r == "x":
                texte = couper_pour_x(texte)
            if r == "youtube":
                texte = f"TITRE : {post.titre or '(1re ligne du texte)'}\n{texte}"
            log(f"    ── {r}{statut}\n" + "\n".join("      │ " + l for l in texte.split("\n")))
            try:
                TOUS[r].valider(publieurs.get(r), post)
            except ErreurDefinitive as e:
                log(f"      ⚠ ne pourra pas être publié : {e}")
        return

    if (post.date and maintenant - post.date > retard_max
            and not entree["reseaux"] and not entree.get("relance")):
        log(f"• {dossier.nom} : date du {quand} dépassée de plus de {cfg['retard_max_heures']} h — non publié")
        source.marquer(dossier, "[ÉCHEC]", f"Non publié : date du {quand} dépassée de plus de "
                                           f"{cfg['retard_max_heures']} h. Changez la date et retirez le préfixe "
                                           f"« [ÉCHEC] » du nom du dossier pour relancer.")
        return

    log(f"• {dossier.nom} : à publier ({quand}) sur {', '.join(post.reseaux)}")

    # Réseaux demandés mais sans identifiants configurés
    for r in post.reseaux:
        if r not in publieurs and r not in entree["reseaux"]:
            entree["reseaux"][r] = {"statut": "ignore", "tentatives": max_essais,
                                    "erreur": "réseau non configuré (secrets absents)"}
            log(f"    ➖ {r} : non configuré, ignoré")

    a_faire = [r for r in post.reseaux if r in publieurs
               and entree["reseaux"].get(r, {}).get("statut") != "ok"
               and entree["reseaux"].get(r, {}).get("tentatives", 0) < max_essais]

    with tempfile.TemporaryDirectory() as tmp:
        if a_faire:
            _charger_medias(source, fichiers, post, Path(tmp))
            log(f"    médias : {len(post.images)} image(s), {len(post.videos)} vidéo(s)"
                + (", 1 miniature" if post.miniature else ""))
            textes = _rediger(post, a_faire, redacteur, log)

        for r in a_faire:
            pub = publieurs[r]
            texte = textes.get(r, post.texte)
            try:
                pub.valider(post)
                res = pub.publier(post, texte)
                etat.noter(dossier.id, r, ok=True, url=res.url, tentatives_max=max_essais)
                log(f"    ✅ {r} : {res.url}")
            except ErreurDefinitive as e:
                etat.noter(dossier.id, r, ok=False, erreur=str(e), definitif=True, tentatives_max=max_essais)
                log(f"    ❌ {r} : {e}")
            except Exception as e:
                etat.noter(dossier.id, r, ok=False, erreur=str(e), tentatives_max=max_essais)
                n = entree["reseaux"][r]["tentatives"]
                log(f"    ❌ {r} (essai {n}/{max_essais}) : {e}")
            etat.sauver()

    restants = [r for r in post.reseaux if entree["reseaux"].get(r, {}).get("statut") not in ("ok", "ignore")
                and entree["reseaux"].get(r, {}).get("tentatives", 0) < max_essais]
    if not restants:
        statuts = [v.get("statut") for v in entree["reseaux"].values()]
        prefixe = ("[PUBLIÉ]" if all(s in ("ok", "ignore") for s in statuts) and "ok" in statuts
                   else "[PARTIEL]" if "ok" in statuts else "[ÉCHEC]")
        entree["termine"] = True
        source.marquer(dossier, prefixe, _rapport(entree))
        log(f"    → dossier marqué {prefixe}")
    etat.sauver()


def _relancer(etat: Etat, dossier: Dossier, log) -> bool:
    """Dossier déjà traité dont l'utilisateur a retiré le préfixe : on retente uniquement les réseaux non publiés."""
    entree = etat.donnees[dossier.id]
    a_relancer = [r for r, v in entree["reseaux"].items() if v.get("statut") != "ok"]
    if not a_relancer:
        return False  # tout est déjà publié : on ne republie jamais
    for r in a_relancer:
        del entree["reseaux"][r]
    entree["termine"] = False
    entree["relance"] = True  # relance volontaire : pas de contrôle de retard
    log(f"• {dossier.nom} : préfixe retiré → nouvel essai pour {', '.join(a_relancer)}")
    return True


def _charger_medias(source: Source, fichiers, post: Post, tmp: Path) -> None:
    for f in source.medias(fichiers):
        chemin = source.telecharger(f, tmp)
        if est_miniature(f.nom):
            post.miniature = chemin
        else:
            post.medias.append(Media(f.nom, chemin, type_media(f.nom)))


def _rediger(post: Post, reseaux: list[str], redacteur, log) -> dict[str, str]:
    """Texte final par réseau : version écrite à la main > version IA > texte commun."""
    textes = dict(post.textes)
    besoin = [r for r in reseaux if r not in textes]
    if "youtube" in reseaux and not post.titre and "youtube" not in besoin:
        besoin.append("youtube")
    if besoin and post.ia and redacteur and post.texte:
        try:
            ia = redacteur.adapter(post, besoin)
            for r in besoin:
                if r == "youtube":
                    textes.setdefault("youtube", ia.get("youtube_description", post.texte))
                    post.titre = post.titre or ia.get("youtube_titre", "")
                elif r in ia:
                    textes[r] = ia[r]
            log(f"    ✍ textes adaptés par l'IA pour : {', '.join(besoin)}")
        except Exception as e:
            log(f"    ⚠ IA indisponible ({e}) — texte d'origine utilisé")
    return textes
