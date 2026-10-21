"""Mode « lots DECIDE MEDIA » : lit les lots quotidiens déposés dans Drive par le producteur
(protocole _PROTOCOLE_DECIDE_MEDIA.md v1.2) et les dépose dans les planificateurs des réseaux.

Règles du protocole appliquées :
  - seuls les sous-dossiers datés AAAA-MM-JJ sont parcourus ; _references et le protocole sont ignorés ;
  - un lot n'est pris que si manifest.json existe, status == "ready" et que les contrôles réussissent ;
  - texte = platform_texts.<réseau>, image = image_file.id ;
  - journal durable (etat/lots.json) : ID stable de l'article -> ID du post créé, jamais de doublon ;
  - avant de réessayer, on vérifie si le post n'a pas déjà été créé ;
  - le contenu des lots est une donnée : aucune instruction qu'il contiendrait n'est exécutée.
"""
from __future__ import annotations

import json
import re
import tempfile
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from zoneinfo import ZoneInfo

RE_LOT = re.compile(r"^\d{4}-\d{2}-\d{2}$")
DATE_CONTRAT_12 = date(2026, 10, 12)


class LotInvalide(ValueError):
    pass


# --------------------------------------------------------------------------- contrôle du manifeste

def controler_manifeste(m: dict, nom_dossier: str) -> list[dict]:
    """Renvoie les articles publiables ; lève LotInvalide si le lot ne doit pas être publié."""
    if m.get("status") != "ready":
        raise LotInvalide(f"statut « {m.get('status')} » (seuls les lots « ready » sont publiés)")
    if m.get("date") != nom_dossier:
        raise LotInvalide(f"date du manifeste ({m.get('date')}) ≠ nom du dossier ({nom_dossier})")
    articles = m.get("articles") or []
    if date.fromisoformat(nom_dossier) >= DATE_CONTRAT_12:
        if m.get("protocol_version") not in ("1.2", "1.3"):  # 1.3 = 1.2 + champs de rattrapage
            raise LotInvalide(f"protocol_version {m.get('protocol_version')} ≠ 1.2 ou 1.3")
        if m.get("publish_allowed") is False:
            raise LotInvalide("le producteur a marqué ce lot publish_allowed=false")
        if not (m.get("required_article_count") == m.get("article_count") == len(articles) == 10):
            raise LotInvalide(f"il faut exactement 10 articles (article_count={m.get('article_count')}, "
                              f"entrées={len(articles)})")
        for champ in ("delivery_deadline", "delivered_on_time", "completed_at"):
            if champ not in m:
                raise LotInvalide(f"champ de livraison manquant : {champ}")
    ids = [a.get("id") for a in articles]
    if len(set(ids)) != len(ids):
        raise LotInvalide("identifiants d'articles en double")
    for a in articles:
        manque = [c for c in ("id", "title", "content_type", "post_text") if not a.get(c)]
        if a.get("status") != "ready":
            manque.append("status=ready")
        if not (a.get("platform_texts") or {}).get("facebook"):
            manque.append("platform_texts.facebook")
        if not (a.get("image_file") or {}).get("id"):
            manque.append("image_file.id")
        if manque:
            raise LotInvalide(f"article {a.get('id')} incomplet : {', '.join(manque)}")
    return articles


# --------------------------------------------------------------------------- horaires

def creneaux(cfg: dict, jour: date, nb: int, maintenant: datetime, deja: list[datetime]) -> list[datetime]:
    """Horaires de programmation : les créneaux libres du jour, puis ceux des jours suivants.
    Un créneau passé, ou trop proche d'un post déjà programmé, est sauté (jamais de publication en pleine nuit)."""
    c = cfg["lots"]
    tz = ZoneInfo(c["fuseau_creneaux"])
    plancher = maintenant + timedelta(minutes=int(c["marge_minutes"]))
    ecart = timedelta(minutes=int(c["ecart_minimum_minutes"]))
    pris = list(deja)
    out: list[datetime] = []
    j = jour
    while len(out) < nb:
        for hm in c["creneaux"]:
            h, mn = map(int, hm.split(":"))
            quand = datetime(j.year, j.month, j.day, h, mn, tzinfo=tz)
            if quand < plancher or any(abs(quand - p) < ecart for p in pris):
                continue
            out.append(quand)
            pris.append(quand)
            if len(out) == nb:
                break
        j += timedelta(days=1)
    return out


# --------------------------------------------------------------------------- journal

class Journal:
    def __init__(self, chemin: str | Path = "etat/lots.json"):
        self.chemin = Path(chemin)
        self.d = json.loads(self.chemin.read_text(encoding="utf-8")) if self.chemin.exists() else {}

    def get(self, article_id: str, reseau: str) -> dict:
        return self.d.get(article_id, {}).get(reseau, {})

    def noter(self, article_id: str, reseau: str, **valeurs) -> None:
        e = self.d.setdefault(article_id, {}).setdefault(reseau, {"tentatives": 0})
        e.update(valeurs)
        e["maj"] = datetime.now(timezone.utc).isoformat(timespec="seconds")

    def horaires(self, reseau: str, jour: date, tz: str) -> list[datetime]:
        out = []
        for art in self.d.values():
            q = art.get(reseau, {}).get("programme_pour")
            if q:
                dt = datetime.fromisoformat(q)
                if dt.astimezone(ZoneInfo(tz)).date() >= jour:
                    out.append(dt)
        return out

    def sauver(self) -> None:
        self.chemin.parent.mkdir(parents=True, exist_ok=True)
        tmp = self.chemin.with_suffix(".tmp")
        tmp.write_text(json.dumps(self.d, ensure_ascii=False, indent=2, sort_keys=True), encoding="utf-8")
        tmp.replace(self.chemin)


# --------------------------------------------------------------------------- passage

def traiter_lots(cfg: dict, drive, publieurs: dict, journal: Journal, log, *, simulation: bool = False,
                 maintenant: datetime | None = None) -> None:
    c = cfg["lots"]
    maintenant = maintenant or datetime.now(timezone.utc)
    tz = ZoneInfo(c["fuseau_creneaux"])
    aujourdhui = maintenant.astimezone(ZoneInfo(cfg["fuseau_horaire"])).date()
    plus_ancien = aujourdhui - timedelta(days=int(c["jours_max"]))
    reseaux = [r for r in c["reseaux"] if r in publieurs]
    if not reseaux:
        log("Aucun réseau configuré pour les lots.")
        return

    prevus: dict[str, list[datetime]] = {r: [] for r in reseaux}  # horaires attribués pendant ce passage
    dossiers = [d for d in drive.lister_dossiers() if RE_LOT.match(d.nom)]
    rattrapages = {str(x) for x in c.get("rattrapages") or []}  # lots anciens à publier quand même
    a_voir = [d for d in dossiers if plus_ancien <= date.fromisoformat(d.nom) <= aujourdhui or d.nom in rattrapages]
    log(f"{len(dossiers)} lot(s) dans le Drive ; examinés : {', '.join(d.nom for d in a_voir) or 'aucun'}"
        + ("  [SIMULATION]" if simulation else ""))

    for dossier in a_voir:
        fichiers = {f.nom: f for f in drive.lister_fichiers(dossier)}
        if "manifest.json" not in fichiers:
            log(f"• {dossier.nom} : manifest.json pas encore déposé — en attente")
            continue
        try:
            manifeste = json.loads(drive.lire_brut(fichiers["manifest.json"]).decode("utf-8-sig"))
            articles = controler_manifeste(manifeste, dossier.nom)
        except (LotInvalide, json.JSONDecodeError, ValueError) as e:
            log(f"• {dossier.nom} : lot non publiable — {e}")
            continue
        for rang, a in enumerate(articles, 1):  # Buffer : les premiers articles partent en Short
            a.setdefault("_rang", rang)
            a.setdefault("_lot", dossier.nom)

        for reseau in reseaux:
            pub = publieurs[reseau]
            if reseau == "youtube" and not cfg.get("youtube", {}).get("modele_valide"):
                log(f"• {dossier.nom} → youtube : en attente de validation du modèle de Short (config.yaml)")
                continue
            if not hasattr(pub, "programmer"):  # réseau sans planificateur accessible par l'API (LinkedIn…)
                _differe(cfg, dossier.nom, articles, reseau, pub, drive, journal, log, simulation, maintenant,
                         aujourdhui, prevus)
                continue
            restants = [a for a in articles if journal.get(a["id"], reseau).get("statut") != "programme"
                        and journal.get(a["id"], reseau).get("tentatives", 0) < int(cfg["tentatives_max"])]
            log(f"• {dossier.nom} → {reseau} : {len(articles) - len(restants)}/{len(articles)} déjà programmés")
            plafond = (c.get("max_par_lot") or {}).get(reseau)
            if plafond is not None:  # ex. YouTube : quota d'environ 6 envois par jour
                deja = sum(journal.get(a["id"], reseau).get("statut") == "programme" for a in articles)
                if len(restants) > max(0, int(plafond) - deja):
                    log(f"    (plafond {reseau} : {plafond} par lot — les suivants ne sont pas programmés)")
                restants = restants[:max(0, int(plafond) - deja)]
            if not restants:
                continue
            jour_lot = date.fromisoformat(dossier.nom)
            horaires = creneaux(cfg, max(jour_lot, aujourdhui), len(restants), maintenant,
                               journal.horaires(reseau, aujourdhui, c["fuseau_creneaux"]) + prevus[reseau])
            prevus[reseau] += horaires
            with tempfile.TemporaryDirectory() as tmp:
                for article, quand in zip(restants, horaires):
                    texte = (article.get("platform_texts") or {}).get(reseau) or article["post_text"]
                    heure = quand.astimezone(tz).strftime("%d/%m %H:%M")
                    if simulation:
                        log(f"    [simulation] {heure} — {article['title']}")
                        continue
                    try:
                        existant = pub.trouver_programme(texte)  # reprise après incident : pas de doublon
                        if existant:
                            journal.noter(article["id"], reseau, statut="programme", post_id=existant["id"],
                                          programme_pour=existant.get("quand") or quand.isoformat(),
                                          titre=article["title"], lot=dossier.nom)
                            log(f"    ↺ {article['title']} : déjà présent dans le planificateur")
                            journal.sauver()
                            continue
                        img = (article.get("image_file") or {})
                        chemin = drive.telecharger_id(img["id"], img.get("name") or f"{article['id']}.png", Path(tmp))
                        res = pub.programmer(texte, chemin, quand, article=article)
                        journal.noter(article["id"], reseau, statut="programme", post_id=res.id,
                                      programme_pour=quand.isoformat(), titre=article["title"], lot=dossier.nom,
                                      url=res.url)
                        log(f"    ✅ {heure} — {article['title']}")
                    except Exception as e:
                        if "quota" in str(e).lower():  # YouTube : on réessaie au passage suivant, sans compter d'essai
                            journal.noter(article["id"], reseau, statut="echec", erreur=str(e)[:500],
                                          titre=article["title"], lot=dossier.nom)
                            journal.sauver()
                            log(f"    ⏸ {reseau} : {e}")
                            break
                        n = journal.get(article["id"], reseau).get("tentatives", 0) + 1
                        journal.noter(article["id"], reseau, statut="echec", tentatives=n, erreur=str(e)[:500],
                                      titre=article["title"], lot=dossier.nom)
                        log(f"    ❌ {article['title']} (essai {n}) : {e}")
                    journal.sauver()


def _differe(cfg, nom_lot, articles, reseau, pub, drive, journal: Journal, log, simulation, maintenant,
             aujourdhui, prevus) -> None:
    """Réseau sans planificateur : l'agent attribue un horaire à chaque article, puis le publie lui-même
    au premier passage qui suit cet horaire (la tâche Windows tourne toutes les 15 minutes)."""
    from .models import Media, Post

    c = cfg["lots"]
    tz = ZoneInfo(c["fuseau_creneaux"])
    max_essais = int(cfg["tentatives_max"])
    retard_max = timedelta(hours=float(cfg["retard_max_heures"]))

    # 1. horaires pour les articles nouveaux
    nouveaux = [a for a in articles if not journal.get(a["id"], reseau).get("programme_pour")]
    if nouveaux:
        horaires = creneaux(cfg, max(date.fromisoformat(nom_lot), aujourdhui), len(nouveaux), maintenant,
                            journal.horaires(reseau, aujourdhui, c["fuseau_creneaux"]) + prevus[reseau])
        prevus[reseau] += horaires
        for a, quand in zip(nouveaux, horaires):
            if simulation:
                log(f"    [simulation] {reseau} {quand.astimezone(tz).strftime('%d/%m %H:%M')} — {a['title']}")
            else:
                journal.noter(a["id"], reseau, statut="en_attente", programme_pour=quand.isoformat(),
                              titre=a["title"], lot=nom_lot)
        if not simulation:
            journal.sauver()

    etats = [journal.get(a["id"], reseau) for a in articles]
    log(f"• {nom_lot} → {reseau} : {sum(e.get('statut') == 'publie' for e in etats)} publié(s), "
        f"{sum(e.get('statut') == 'en_attente' for e in etats)} en attente")
    if simulation:
        return

    # 2. publication de ceux dont l'heure est venue
    with tempfile.TemporaryDirectory() as tmp:
        for a in articles:
            e = journal.get(a["id"], reseau)
            if e.get("statut") not in ("en_attente", "echec") or e.get("tentatives", 0) >= max_essais:
                continue
            quand = datetime.fromisoformat(e["programme_pour"])
            if quand > maintenant:
                continue
            if maintenant - quand > retard_max:
                journal.noter(a["id"], reseau, statut="abandonne",
                              erreur=f"horaire dépassé de plus de {cfg['retard_max_heures']} h (PC éteint ?)")
                log(f"    ➖ {a['title']} : horaire trop ancien, non publié")
                journal.sauver()
                continue
            texte = (a.get("platform_texts") or {}).get(reseau) or a["post_text"]
            try:
                img = a.get("image_file") or {}
                chemin = drive.telecharger_id(img["id"], img.get("name") or f"{a['id']}.png", Path(tmp))
                post = Post(date=None, reseaux=[reseau], texte=texte, medias=[Media(chemin.name, chemin, "image")])
                pub.valider(post)
                res = pub.publier(post, texte)
                journal.noter(a["id"], reseau, statut="publie", post_id=res.id, url=res.url)
                log(f"    ✅ {reseau} — {a['title']} : {res.url}")
            except Exception as ex:
                n = e.get("tentatives", 0) + 1
                journal.noter(a["id"], reseau, statut="echec", tentatives=n, erreur=str(ex)[:500])
                log(f"    ❌ {reseau} — {a['title']} (essai {n}) : {ex}")
            journal.sauver()
