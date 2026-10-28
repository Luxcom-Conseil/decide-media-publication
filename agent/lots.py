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

from .publieurs.base import ErreurLimite

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

def creneaux(cfg: dict, jour: date, nb: int, maintenant: datetime, deja: list[datetime],
             reseau: str | None = None) -> list[datetime]:
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
        for hm in (c.get("creneaux_par_reseau") or {}).get(reseau) or c["creneaux"]:
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

    def horaires(self, reseau: str, jour: date, tz: str, piste: str = "principale",
                 lot: str | None = None) -> list[datetime]:
        """Horaires déjà pris sur ce réseau à partir de `jour`, pour une piste (principale ou rattrapage Facebook) ;
        avec `lot`, seulement ceux de ce lot."""
        out = []
        for art in self.d.values():
            e = art.get(reseau, {})
            q = e.get("programme_pour")
            if q and e.get("piste", "principale") == piste and (lot is None or e.get("lot") == lot):
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
    # le passage dure (rendu des Shorts V3 : 1 h et plus) : l'heure de départ ne suffit plus pour juger un créneau
    depart = datetime.now(timezone.utc)
    horloge = lambda: maintenant + (datetime.now(timezone.utc) - depart)
    marge = timedelta(minutes=int(c["marge_minutes"]))
    tz = ZoneInfo(c["fuseau_creneaux"])
    aujourdhui = maintenant.astimezone(ZoneInfo(cfg["fuseau_horaire"])).date()
    plus_ancien = aujourdhui - timedelta(days=int(c["jours_max"]))
    reseaux = [r for r in c["reseaux"] if r in publieurs]
    if not reseaux:
        log("Aucun réseau configuré pour les lots.")
        return

    prevus: dict[tuple, list[datetime]] = {}  # horaires attribués pendant ce passage, par (réseau, piste)
    dossiers = sorted((d for d in drive.lister_dossiers() if RE_LOT.match(d.nom)), key=lambda d: d.nom)
    log(f"{len(dossiers)} lot(s) dans le Drive" + ("  [SIMULATION]" if simulation else ""))

    def lire(dossier, bavard: bool = True):
        fichiers = {f.nom: f for f in drive.lister_fichiers(dossier)}
        if "manifest.json" not in fichiers:
            if bavard:
                log(f"• {dossier.nom} : manifest.json pas encore déposé — en attente")
            return None, None
        try:
            manifeste = json.loads(drive.lire_brut(fichiers["manifest.json"]).decode("utf-8-sig"))
            articles = controler_manifeste(manifeste, dossier.nom)
        except (LotInvalide, json.JSONDecodeError, ValueError) as e:
            if bavard:
                log(f"• {dossier.nom} : lot non publiable — {e}")
            return None, None
        for rang, a in enumerate(articles, 1):  # Buffer : les premiers articles partent en Short
            a.setdefault("_rang", rang)
            a.setdefault("_lot", dossier.nom)
        return manifeste, articles

    # 1. le lot du jour, en priorité, sur tous les réseaux
    travaux = []  # (dossier, articles, réseaux, piste)
    du_jour = False
    for d in dossiers:
        if plus_ancien <= date.fromisoformat(d.nom) <= aujourdhui:
            _, articles = lire(d)
            if articles:
                travaux.append((d, articles, reseaux, "principale"))
                du_jour = du_jour or d.nom == aujourdhui.isoformat()

    # 2. un lot de rattrapage par jour (lots marqués « backfill » par le producteur), du plus ancien au plus récent :
    #    s'il y a un lot du jour, le rattrapage ne passe que sur Facebook (visuels, créneaux intercalés) ;
    #    sinon il prend la place du lot du jour sur tous les réseaux.
    r = c.get("rattrapage") or {}
    if r.get("actif"):
        piste = "rattrapage" if du_jour else "principale"
        portee = [x for x in (r.get("reseaux_avec_lot_du_jour") or []) if x in reseaux] if du_jour else reseaux
        memo = journal.d.setdefault("_rattrapage", {})
        choisi = None
        if memo.get("jour") == aujourdhui.isoformat():  # déjà choisi aujourd'hui : on le termine, on n'en prend pas d'autre
            choisi = next((d for d in dossiers if d.nom == memo.get("lot")), None)
            manif, articles = lire(choisi, bavard=False) if choisi else (None, None)
        else:
            for d in dossiers:
                if date.fromisoformat(d.nom) >= plus_ancien or d.nom < str(r.get("depuis", "")):
                    continue
                manif, articles = lire(d, bavard=False)
                if not articles or not manif.get("backfill"):
                    continue
                if _incomplet(cfg, journal, articles, portee):
                    choisi = d
                    break
        if choisi and articles:
            if not simulation:
                memo.update(jour=aujourdhui.isoformat(), lot=choisi.nom)
                journal.sauver()
            log(f"• rattrapage du jour : lot {choisi.nom} → {', '.join(portee)}")
            travaux.append((choisi, articles, portee, piste))
        else:
            log("• rattrapage : plus aucun lot en attente pour " + ", ".join(portee))

    for dossier, articles, portee, piste in travaux:
        for reseau in portee:
            pub = publieurs[reseau]
            if reseau == "youtube" and not cfg.get("youtube", {}).get("modele_valide"):
                log(f"• {dossier.nom} → youtube : en attente de validation du modèle de Short (config.yaml)")
                continue
            if not hasattr(pub, "programmer"):  # réseau sans planificateur accessible par l'API (LinkedIn…)
                _differe(cfg, dossier.nom, articles, reseau, pub, drive, journal, log, simulation, maintenant,
                         aujourdhui, {reseau: prevus.setdefault((reseau, piste), [])})
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
            cle = (reseau, piste)
            prevus.setdefault(cle, [])
            # le lot du jour est prioritaire : il prend les créneaux du jour même si des posts
            # d'anciens lots y débordent encore (sinon chaque lot glisse au lendemain)
            pris = journal.horaires(reseau, aujourdhui, c["fuseau_creneaux"], piste,
                                    lot=dossier.nom if dossier.nom == aujourdhui.isoformat() else None)
            nom_creneaux = reseau if piste == "principale" else f"{reseau}_rattrapage"
            horaires = creneaux(cfg, max(jour_lot, aujourdhui), len(restants), horloge(), pris + prevus[cle],
                                nom_creneaux)
            prevus[cle] += horaires
            with tempfile.TemporaryDirectory() as tmp:
                for article, quand in zip(restants, horaires):
                    if not simulation and quand < horloge() + marge:
                        # créneau dépassé pendant le passage (Shorts précédents longs à rendre) : le suivant libre
                        quand = creneaux(cfg, max(jour_lot, aujourdhui), 1, horloge(), pris + prevus[cle],
                                         nom_creneaux)[0]
                        prevus[cle].append(quand)
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
                                          titre=article["title"], lot=dossier.nom, piste=piste)
                            log(f"    ↺ {article['title']} : déjà présent dans le planificateur")
                            journal.sauver()
                            continue
                        img = (article.get("image_file") or {})
                        chemin = drive.telecharger_id(img["id"], img.get("name") or f"{article['id']}.png", Path(tmp))
                        res = pub.programmer(texte, chemin, quand, article=article)
                        journal.noter(article["id"], reseau, statut="programme", post_id=res.id,
                                      programme_pour=quand.isoformat(), titre=article["title"], lot=dossier.nom,
                                      url=res.url, piste=piste)
                        log(f"    ✅ {heure} — {article['title']}")
                    except Exception as e:
                        if isinstance(e, ErreurLimite):  # YouTube : on réessaie au passage suivant, sans compter d'essai
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


def _incomplet(cfg: dict, journal: Journal, articles: list[dict], reseaux: list[str]) -> bool:
    """Reste-t-il quelque chose à programmer sur ces réseaux (dans la limite du plafond et des essais) ?"""
    for reseau in reseaux:
        plafond = (cfg["lots"].get("max_par_lot") or {}).get(reseau)
        attendus = articles[:int(plafond)] if plafond is not None else articles
        for a in attendus:
            e = journal.get(a["id"], reseau)
            if e.get("statut") != "programme" and e.get("tentatives", 0) < int(cfg["tentatives_max"]):
                return True
    return False


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
