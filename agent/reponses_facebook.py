"""Réponses écrites sous les commentaires Facebook (demande de Stéphane du 12/11/2026, droits ajoutés le 13/11).

Quand une vidéo de réponse (editorial_type « reponse », plateforme facebook) est en ligne sur la Page, l'agent répond
sous chacun des commentaires qui posaient la question, sur la vidéo d'origine : une phrase sourcée tirée de l'article
(reponse.reponse, copiée du corps par le producteur) et le lien de la vidéo de réponse.

Règles : on ne répond qu'aux commentaires recopiés par le producteur comme posant la question (donc ni aux insultes ni
aux débats) ; jamais à un commentaire qui contient un lien ; aucun lien ni chiffre venu des commentaires ; une seule
réponse par commentaire ; 5 commentaires au plus par vidéo de réponse. Lecture et écriture avec le jeton de Page
(pages_read_user_content, pages_manage_engagement).
"""
from __future__ import annotations

import os
import re
import unicodedata
from datetime import datetime, timedelta, timezone

import requests

RESEAU = "facebook_shorts"
PAR_VIDEO = 5          # commentaires au plus sous une même vidéo d'origine
ESSAIS = 3
LIEN = re.compile(r"https?://|www\.|\.com\b|\.cm\b|wa\.me", re.I)


def video_id(lien: str) -> str | None:
    """Identifiant d'une vidéo Facebook depuis son adresse (/videos/ID, /reel/ID, ?v=ID)."""
    m = re.search(r"/(?:videos|reel|reels)/(?:[^/?]+/)?(\d{6,})", lien or "") or re.search(r"[?&]v=(\d{6,})", lien or "")
    return m.group(1) if m else None


def _norme(t: str) -> str:
    t = unicodedata.normalize("NFKC", t or "").replace("’", "'").lower()
    return re.sub(r"\s+", " ", t).strip(" .!?…\"'«»")


def commentaires(vid: str, graph: str, jeton: str, pages: int = 5) -> list[dict]:
    """Commentaires de premier niveau d'une vidéo de la Page : [{id, texte, jaime, reponses}], les plus aimés d'abord."""
    tous, apres = [], None
    for _ in range(pages):
        p = {"fields": "id,message,like_count,comment_count", "filter": "toplevel", "limit": 100, "access_token": jeton}
        if apres:
            p["after"] = apres
        r = requests.get(f"{graph}/{vid}/comments", params=p, timeout=60).json()
        if "error" in r:
            raise RuntimeError(r["error"].get("message", "erreur Graph")[:200])
        tous += [{"id": c["id"], "texte": (c.get("message") or "").strip(), "jaime": int(c.get("like_count") or 0),
                  "reponses": int(c.get("comment_count") or 0)} for c in r.get("data", []) if c.get("message")]
        apres = ((r.get("paging") or {}).get("cursors") or {}).get("after")
        if not (r.get("paging") or {}).get("next"):
            break
    return sorted(tous, key=lambda c: -c["jaime"])


def choisir(copies: list[str], publics: list[dict], deja: set[str] = frozenset()) -> list[dict]:
    """Les commentaires de la vidéo d'origine qui sont ceux recopiés par le producteur (au mot près, casse et
    ponctuation finale ignorées), sans lien, pas encore traités."""
    voulus = {_norme(c) for c in copies if c and c.strip()}
    out = [c for c in publics if _norme(c["texte"]) in voulus and not LIEN.search(c["texte"]) and c["id"] not in deja]
    return out[:PAR_VIDEO]


def message(phrase: str, permalien: str) -> str:
    lien = permalien if permalien.startswith("http") else "https://www.facebook.com" + permalien
    return f"{phrase.strip()}\n\nLa réponse en vidéo : {lien}"


def a_suivre(article: dict) -> dict | None:
    """Ce que le journal garde d'un article réponse publié sur Facebook, pour y revenir quand la vidéo est en ligne."""
    r = article.get("reponse") or {}
    if article.get("editorial_type") != "reponse" or "facebook" not in (r.get("plateformes") or []):
        return None
    return {"origine": r.get("video_origine"), "commentaires": list(r.get("commentaires") or []),
            "phrase": r.get("reponse"), "faits": []}


def repondre(cfg: dict, journal, log=print, maintenant: datetime | None = None, simulation: bool = False) -> int:
    """Répond sous les commentaires pour chaque vidéo de réponse Facebook en ligne. Renvoie le nombre de réponses."""
    maintenant = maintenant or datetime.now(timezone.utc)
    graph = f"https://graph.facebook.com/{cfg['meta']['version_api']}"
    jeton = os.environ.get("META_PAGE_TOKEN")
    total = 0
    for art_id, reseaux in journal.d.items():
        e = reseaux.get(RESEAU) if isinstance(reseaux, dict) else None
        suivi = (e or {}).get("reponse_fb")
        if not suivi or suivi.get("termine") or e.get("statut") != "programme" or not e.get("post_id"):
            continue
        if datetime.fromisoformat(e["programme_pour"]) > maintenant - timedelta(minutes=5):
            continue
        if not jeton:
            log("• réponses Facebook : META_PAGE_TOKEN absent")
            return total
        titre = e.get("titre") or art_id
        try:
            reel = requests.get(f"{graph}/{e['post_id']}", timeout=60,
                                params={"fields": "published,permalink_url", "access_token": jeton}).json()
            if "error" in reel:
                raise RuntimeError(reel["error"].get("message", "erreur Graph")[:200])
            if not reel.get("published"):
                log(f"• réponses Facebook — {titre} : vidéo pas encore en ligne")
                continue
            vid = video_id(suivi.get("origine"))
            if not vid:
                suivi["termine"] = "vidéo d'origine illisible"
                log(f"    ⚠ réponses Facebook — {titre} : adresse de la vidéo d'origine illisible")
                continue
            cibles = choisir(suivi.get("commentaires") or [], commentaires(vid, graph, jeton), set(suivi.get("faits") or []))
            texte = message(suivi.get("phrase") or "", reel.get("permalink_url") or f"/reel/{e['post_id']}/")
            for c in cibles:
                if simulation:
                    log(f"    [simulation] réponse sous « {c['texte'][:60]} »")
                    continue
                r = requests.post(f"{graph}/{c['id']}/comments", timeout=60,
                                  data={"message": texte, "access_token": jeton}).json()
                if "error" in r:
                    raise RuntimeError(r["error"].get("message", "erreur Graph")[:200])
                suivi.setdefault("faits", []).append(c["id"])
                total += 1
            if not simulation:
                suivi["termine"] = maintenant.isoformat(timespec="minutes")
            log(f"    💬 réponses Facebook — {titre} : {len(cibles)} commentaire(s) "
                f"(sur {len(suivi.get('commentaires') or [])} recopiés)")
        except (requests.RequestException, RuntimeError, ValueError) as ex:
            suivi["essais"] = suivi.get("essais", 0) + 1
            if suivi["essais"] >= ESSAIS:
                suivi["termine"] = f"abandon : {ex}"[:200]
            log(f"    ⚠ réponses Facebook — {titre} (essai {suivi['essais']}) : {ex}")
        if not simulation:
            journal.sauver()
    return total
