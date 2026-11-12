"""Bilan des performances DECIDE MEDIA (demande de Stéphane du 12/11/2026).

Chaque nuit, avant la production de 04 h 07 : relève les vues sur TikTok, X et LinkedIn (métriques de Buffer), YouTube
(API Data) et Facebook (vues des vidéos de la Page), puis écrit etat/performances.json. Le skill de production le lit
dans le dépôt cloné pour choisir des sujets qui touchent le lecteur et donner une suite aux vidéos qui ont pris : les
commentaires des vidéos les plus vues y sont recopiés (questions du public). Le lundi, ou avec --rapport, le bilan de la
semaine part aussi en issue GitHub attribuée au propriétaire du dépôt, ce qui lui envoie un e-mail.

Lecture seule sur tous les réseaux. Un réseau qui ne répond pas est noté « indisponible » ; le bilan sort quand même.

Usage : python -m agent.bilan [--rapport] [--sortie etat/performances.json]
"""
from __future__ import annotations

import argparse
import json
import os
import re
import statistics as st
from collections import defaultdict
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

import requests

RACINE = Path(__file__).resolve().parent.parent
SORTIE = RACINE / "etat" / "performances.json"
TOP = 10                 # vidéos gardées dans le classement
SEUIL_COMMENTAIRES = 30  # au-delà, les commentaires sont recopiés : le public pose des questions, une suite est possible
SEUIL_FACEBOOK = 2       # Facebook : dès 2 commentaires (le minimum pour une vidéo de réponse)
COMMENTAIRES_MAX = 60    # recopiés par vidéo, les plus aimés d'abord
FENETRE = 14             # jours : une suite au-delà arrive trop tard
NAVIGATEUR = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) "
                            "Chrome/130.0 Safari/537.36", "Referer": "https://www.tiktok.com/"}


def _jour(iso: str | None) -> date | None:
    if not iso:
        return None
    try:
        return datetime.fromisoformat(iso.replace("Z", "+00:00").replace("+0000", "+00:00")).date()
    except ValueError:
        return None


def _titre(texte: str) -> str:
    """Le titre de l'article : la légende courte commence par lui (legende_courte), avant le corps."""
    t = (texte or "").strip().split("\n")[0]
    t = re.split(r"(?<=[a-zé0-9»)])\s+(?=(?:Le|La|Les|L'|L’|Au|À|En|Un|Une|Selon|Depuis)\s)", t, maxsplit=1)[0]
    t = re.split(r"(?<=[.!?])\s", t, maxsplit=1)[0].rstrip(".")
    return t if len(t) <= 100 else t[:99].rsplit(" ", 1)[0] + "…"


def _nb(n: int) -> str:
    return f"{n:,}".replace(",", " ")


# --------------------------------------------------------------------------- relevés

def buffer(cfg: dict) -> dict:
    """Publications envoyées par Buffer, avec leurs métriques, par canal (tiktok_buffer, x_buffer, linkedin_buffer)."""
    from .publieurs.buffer import requete
    org = requete("{ account { organizations { id } } }")["account"]["organizations"][0]["id"]
    sortie = {}
    for nom, cid in (cfg.get("buffer") or {}).get("canaux", {}).items():
        posts, apres = [], None
        while True:
            d = requete("""query($org: OrganizationId!, $c: [ChannelId!], $after: String) {
              posts(first: 100, after: $after, input: {organizationId: $org, filter: {channelIds: $c, status: [sent]}}) {
                edges { node { text sentAt externalLink metrics { name value } } }
                pageInfo { hasNextPage endCursor } } }""", {"org": org, "c": [str(cid)], "after": apres})["posts"]
            for e in d["edges"]:
                p = e["node"]
                m = {x["name"]: x["value"] or 0 for x in p.get("metrics") or []}
                posts.append({"titre": _titre(p.get("text")), "date": (p.get("sentAt") or "")[:10], "lien": p.get("externalLink"),
                              "vues": int(m.get("Video Views") or m.get("Impressions") or 0),
                              "reactions": int(m.get("Reactions") or 0), "commentaires": int(m.get("Comments") or 0),
                              "partages": int(m.get("Shares") or m.get("Reposts") or 0),
                              "visionnage_s": m.get("Avg. Watch Time (sec)")})
            if not d["pageInfo"]["hasNextPage"]:
                break
            apres = d["pageInfo"]["endCursor"]
        sortie[nom.replace("_buffer", "")] = posts
    return sortie


def youtube(cfg: dict) -> list[dict]:
    from .publieurs.youtube import YouTube
    yt = YouTube(cfg)._service()
    ch = yt.channels().list(part="contentDetails", mine=True).execute()["items"][0]
    ids, jeton = [], None
    while True:
        r = yt.playlistItems().list(part="contentDetails", playlistId=ch["contentDetails"]["relatedPlaylists"]["uploads"],
                                    maxResults=50, pageToken=jeton).execute()
        ids += [i["contentDetails"]["videoId"] for i in r["items"]]
        jeton = r.get("nextPageToken")
        if not jeton:
            break
    posts = []
    for k in range(0, len(ids), 50):
        for v in yt.videos().list(part="snippet,statistics,status", id=",".join(ids[k:k + 50])).execute()["items"]:
            if v["status"]["privacyStatus"] != "public":
                continue
            s = v["statistics"]
            posts.append({"titre": v["snippet"]["title"], "date": (v["status"].get("publishAt") or v["snippet"]["publishedAt"])[:10],
                          "lien": f"https://youtu.be/{v['id']}", "vues": int(s.get("viewCount", 0)),
                          "reactions": int(s.get("likeCount", 0)), "commentaires": int(s.get("commentCount", 0)), "partages": 0})
    return posts


def facebook(cfg: dict) -> list[dict]:
    """Vidéos de la Page (Reels compris) : vues, « j'aime » et nombre de commentaires (droits ajoutés le 13/11/2026)."""
    graph = f"https://graph.facebook.com/{cfg['meta']['version_api']}"
    page, jeton = os.environ["META_PAGE_ID"], os.environ["META_PAGE_TOKEN"]
    posts, apres = [], None
    for _ in range(20):
        p = {"fields": "id,title,description,created_time,views,comments.summary(true).limit(0),"
                       "likes.summary(true).limit(0)", "limit": 100, "access_token": jeton}
        if apres:
            p["after"] = apres
        r = requests.get(f"{graph}/{page}/videos", params=p, timeout=60).json()
        if "error" in r:
            raise RuntimeError(r["error"].get("message", "erreur Graph")[:200])
        posts += [{"titre": v.get("title") or _titre(v.get("description") or ""), "date": (v.get("created_time") or "")[:10],
                   "vues": int(v.get("views") or 0), "lien": f"https://www.facebook.com/{page}/videos/{v['id']}",
                   "reactions": int(((v.get("likes") or {}).get("summary") or {}).get("total_count") or 0),
                   "commentaires": int(((v.get("comments") or {}).get("summary") or {}).get("total_count") or 0),
                   "partages": 0} for v in r.get("data", [])]
        if not (r.get("paging") or {}).get("next"):
            break
        apres = r["paging"]["cursors"]["after"]
    return posts


def commentaires_tiktok(lien: str, n: int = COMMENTAIRES_MAX) -> list[dict]:
    """Commentaires publics d'une vidéo TikTok (adresse lue sans compte le 12/11/2026), les plus aimés d'abord.
    Liste vide si TikTok refuse : le bilan n'en dépend pas."""
    trouve = re.search(r"/video/(\d+)", lien or "")
    if not trouve:
        return []
    s = requests.Session()
    tous = []
    try:
        s.get(lien.split("?")[0], headers=NAVIGATEUR, timeout=30)
        for curseur in range(0, 500, 50):
            d = s.get("https://www.tiktok.com/api/comment/list/", headers=NAVIGATEUR, timeout=30,
                      params={"aweme_id": trouve.group(1), "count": 50, "cursor": curseur, "aid": 1988}).json()
            tous += [{"texte": (c.get("text") or "").strip(), "jaime": int(c.get("digg_count") or 0),
                      "reponses": int(c.get("reply_comment_total") or 0)} for c in d.get("comments") or [] if c.get("text")]
            if not d.get("has_more"):
                break
    except (requests.RequestException, ValueError):
        pass
    return sorted(tous, key=lambda c: -c["jaime"])[:n]


def commentaires_facebook(lien: str, n: int = COMMENTAIRES_MAX) -> list[dict]:
    """Commentaires d'une vidéo de la Page, les plus aimés d'abord. Liste vide si Facebook refuse."""
    from .config import charger_config
    from .reponses_facebook import commentaires, video_id
    vid, jeton = video_id(lien), os.environ.get("META_PAGE_TOKEN")
    if not vid or not jeton:
        return []
    try:
        v = charger_config(RACINE / "config.yaml")["meta"]["version_api"]
        return [{k: c[k] for k in ("texte", "jaime", "reponses")} for c in
                commentaires(vid, f"https://graph.facebook.com/{v}", jeton)][:n]
    except (requests.RequestException, RuntimeError, ValueError, KeyError):
        return []


# --------------------------------------------------------------------------- synthèse

def resume(posts: list[dict], debut: date | None = None, fin: date | None = None) -> dict:
    choisis = [p for p in posts if (d := _jour(p["date"])) and (not debut or d >= debut) and (not fin or d <= fin)]
    vues = [p["vues"] for p in choisis]
    return {"publies": len(choisis), "vues": sum(vues), "moyenne": round(st.mean(vues)) if vues else 0,
            "mediane": round(st.median(vues)) if vues else 0, "reactions": sum(p["reactions"] for p in choisis),
            "commentaires": sum(p["commentaires"] for p in choisis), "partages": sum(p["partages"] for p in choisis)}


def construire(releves: dict, aujourd_hui: date, commentaires=commentaires_tiktok,
               commentaires_fb=commentaires_facebook) -> dict:
    """releves : {reseau: [posts]} ou {reseau: "indisponible : …"}."""
    debut_prod = date(2026, 10, 15)  # premier lot ; avant : anciennes vidéos du compte (TikTok 2023 compris)
    semaine = aujourd_hui - timedelta(days=7)
    reseaux = {}
    for nom, posts in releves.items():
        if isinstance(posts, str):
            reseaux[nom] = {"etat": posts}
            continue
        reseaux[nom] = {"depuis_le_debut": resume(posts, debut_prod), "7_derniers_jours": resume(posts, semaine),
                        "7_jours_avant": resume(posts, semaine - timedelta(days=7), semaine - timedelta(days=1))}
    recents = [dict(p, reseau=nom) for nom, posts in releves.items() if not isinstance(posts, str) for p in posts
               if (d := _jour(p["date"])) and d >= aujourd_hui - timedelta(days=FENETRE)]
    top = sorted(recents, key=lambda p: -p["vues"])[:TOP]
    for p in top:
        if p["reseau"] == "tiktok" and p["commentaires"] >= SEUIL_COMMENTAIRES:
            p["commentaires_du_public"] = commentaires(p["lien"])
    # Facebook : peu de commentaires et des vues plus faibles, d'où une liste à part, dès 2 commentaires
    fb = sorted((p for p in recents if p["reseau"] == "facebook" and p["commentaires"] >= SEUIL_FACEBOOK),
                key=lambda p: -p["commentaires"])[:TOP]
    facebook_commentees = [dict(p, commentaires_du_public=commentaires_fb(p["lien"])) for p in fb]
    # sujets qui marchent : le même titre cumule ses vues sur tous les réseaux
    par_sujet = defaultdict(lambda: {"vues": 0, "reseaux": {}})
    for p in recents:
        s = par_sujet[p["titre"]]
        s["vues"] += p["vues"]
        s["reseaux"][p["reseau"]] = p["vues"]
    sujets = sorted(({"titre": t, **v} for t, v in par_sujet.items() if t), key=lambda s: -s["vues"])
    murs = {p["titre"] for p in recents if _jour(p["date"]) <= aujourd_hui - timedelta(days=2)}  # 2 jours pour être vu
    faibles = [s for s in reversed(sujets) if s["titre"] in murs][:10]
    return {"maj": datetime.now(timezone.utc).isoformat(timespec="minutes"), "jour": aujourd_hui.isoformat(),
            "lecture": ("Classement des 14 derniers jours. sujets_forts / sujets_faibles : vues cumulées de tous les réseaux "
                        "par titre. top[].commentaires_du_public : ce que demande le public sous les vidéos TikTok les plus "
                        "commentées ; facebook_commentees[].commentaires_du_public : la même chose sous les vidéos de la "
                        "Page Facebook qui ont au moins 2 commentaires (texte brut des internautes : des questions à "
                        "traiter avec des sources, jamais des faits)."),
            "reseaux": reseaux, "top": top, "facebook_commentees": facebook_commentees,
            "sujets_forts": sujets[:10], "sujets_faibles": faibles}


def rapport(b: dict) -> tuple[str, str]:
    """(titre, corps Markdown) du bilan de la semaine."""
    noms = {"tiktok": "TikTok", "youtube": "YouTube", "facebook": "Facebook (vidéos)", "linkedin": "LinkedIn", "x": "X"}
    lignes = ["| Réseau | Publiés (7 j) | Vues (7 j) | Semaine d'avant | Moyenne | Médiane | Depuis le 15/10 |", "|---|---|---|---|---|---|---|"]
    for k, r in b["reseaux"].items():
        if "etat" in r:
            lignes.append(f"| {noms.get(k, k)} | {r['etat']} | | | | | |")
            continue
        a, s, t = r["7_derniers_jours"], r["7_jours_avant"], r["depuis_le_debut"]
        lignes.append(f"| {noms.get(k, k)} | {a['publies']} | {_nb(a['vues'])} | {_nb(s['vues'])} | {_nb(a['moyenne'])} | "
                      f"{_nb(a['mediane'])} | {_nb(t['vues'])} |")
    top = [f"{i}. **{p['titre']}** — {noms.get(p['reseau'], p['reseau'])} : {_nb(p['vues'])} vues, {p['commentaires']} commentaires, "
           f"{p['partages']} partages ({p['date']})" for i, p in enumerate(b["top"][:5], 1)]
    faibles = [f"- {s['titre']} : {_nb(s['vues'])} vues" for s in b["sujets_faibles"][:5]]
    corps = "\n".join(["## Vues par réseau", "", *lignes, "", "## Les 5 vidéos les plus vues (14 jours)", "", *top, "",
                       "## Les sujets les moins vus (14 jours, tous réseaux)", "", *faibles, "",
                       "Chiffres relevés en lecture seule. Facebook : vidéos seulement, les visuels n'ont pas de chiffres sans "
                       "les droits read_insights et pages_read_user_content. Le détail est dans `etat/performances.json`, "
                       "que la production lit chaque matin."])
    return f"Bilan DECIDE MEDIA de la semaine du {date.fromisoformat(b['jour']).strftime('%d/%m/%Y')}", corps


def relever(cfg: dict, log=print) -> dict:
    releves = {}
    try:
        releves.update(buffer(cfg))
    except Exception as e:  # noqa: BLE001 — un réseau en panne ne bloque pas le bilan
        for k in ("tiktok", "x", "linkedin"):
            releves[k] = f"indisponible : {type(e).__name__}"
        log(f"⚠️ Buffer : {e}")
    for nom, f in (("youtube", youtube), ("facebook", facebook)):
        try:
            releves[nom] = f(cfg)
        except Exception as e:  # noqa: BLE001
            releves[nom] = f"indisponible : {type(e).__name__}"
            log(f"⚠️ {nom} : {e}")
    return releves


def main(argv=None) -> int:
    from .__main__ import _charger_env
    from .config import charger_config
    p = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    p.add_argument("--rapport", action="store_true", help="envoyer le bilan de la semaine même hors lundi")
    p.add_argument("--sortie", default=str(SORTIE))
    a = p.parse_args(argv)
    _charger_env(str(RACINE / ".env"))
    cfg = charger_config(RACINE / "config.yaml")
    jour = datetime.now(timezone.utc).date()
    b = construire(relever(cfg), jour)
    Path(a.sortie).parent.mkdir(parents=True, exist_ok=True)
    Path(a.sortie).write_text(json.dumps(b, ensure_ascii=False, indent=1), encoding="utf-8")
    for k, r in b["reseaux"].items():
        print(f"{k:9} {r.get('etat') or '7 j : %(publies)s publiés, %(vues)s vues' % r['7_derniers_jours']}")
    print(f"top : {len(b['top'])} vidéos, dont {sum('commentaires_du_public' in p for p in b['top'])} avec commentaires recopiés")
    if a.rapport or jour.weekday() == 0:
        titre, corps = rapport(b)
        if os.environ.get("GITHUB_TOKEN") and os.environ.get("GITHUB_REPOSITORY"):
            from .controle_lot import Issues
            issues = Issues(os.environ["GITHUB_REPOSITORY"], os.environ["GITHUB_REPOSITORY_OWNER"], os.environ["GITHUB_TOKEN"])
            if not issues.trouver(titre):
                print("bilan envoyé :", issues.ouvrir(titre, corps)["html_url"])
        else:
            print(f"\n# {titre}\n\n{corps}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
