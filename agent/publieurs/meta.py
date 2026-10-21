"""Page Facebook et compte Instagram professionnel (même application Meta, même jeton de Page)."""
from __future__ import annotations

import json
import math
import os
import tempfile
from datetime import datetime, timezone
from pathlib import Path

import requests
from PIL import Image, ImageOps

from ..models import Media, Post
from .base import TIMEOUT, ErreurDefinitive, ErreurPublication, Publieur, Resultat, attendre, controler


class _Meta(Publieur):
    def __init__(self, cfg: dict):
        super().__init__(cfg)
        self.v = cfg["meta"]["version_api"]
        self.graph = f"https://graph.facebook.com/{self.v}"
        self.page = os.environ.get("META_PAGE_ID", "")
        self.jeton = os.environ.get("META_PAGE_TOKEN", "")

    def _get(self, chemin: str, **params):
        params["access_token"] = self.jeton
        return controler(requests.get(f"{self.graph}/{chemin}", params=params, timeout=TIMEOUT),
                         f"{self.nom} GET {chemin.split('?')[0]}").json()

    def _post(self, chemin: str, contexte: str, base: str | None = None, files=None, **data):
        data["access_token"] = self.jeton
        r = requests.post(f"{base or self.graph}/{chemin}", data=data, files=files, timeout=TIMEOUT)
        return controler(r, f"{self.nom} {contexte}").json()

    def _photo_non_publiee(self, chemin: Path) -> str:
        with chemin.open("rb") as f:
            return self._post(f"{self.page}/photos", "envoi photo", files={"source": f},
                              published="false")["id"]


class Facebook(_Meta):
    nom = "facebook"
    variables = ("META_PAGE_ID", "META_PAGE_TOKEN")

    def verifier(self) -> str:
        return "Page « " + self._get(self.page, fields="name")["name"] + " »"

    def publier(self, post: Post, texte: str) -> Resultat:
        if post.videos:
            v = post.videos[0]
            with v.chemin.open("rb") as f:
                r = self._post(f"{self.page}/videos", "envoi vidéo", base=f"https://graph-video.facebook.com/{self.v}",
                               files={"source": (v.nom, f, v.mime)}, description=texte)
            return Resultat(f"https://www.facebook.com/{self.page}/videos/{r['id']}", r["id"])

        images = post.images[:10]
        if len(images) == 1:
            with images[0].chemin.open("rb") as f:
                r = self._post(f"{self.page}/photos", "publication photo", files={"source": f}, message=texte)
            pid = r.get("post_id") or r["id"]
            return Resultat(f"https://www.facebook.com/{pid}", pid)

        data = {"message": texte}
        for i, img in enumerate(images):
            data[f"attached_media[{i}]"] = json.dumps({"media_fbid": self._photo_non_publiee(img.chemin)})
        r = self._post(f"{self.page}/feed", "publication", **data)
        return Resultat(f"https://www.facebook.com/{r['id']}", r["id"])

    # ---- programmation native : le post attend dans le planificateur de la Page (Meta Business Suite)

    def programmer(self, texte: str, image: Path, quand, article: dict | None = None) -> Resultat:
        """Photo + texte programmés ; Facebook publie lui-même à l'heure dite (entre 10 min et 30 jours)."""
        with image.open("rb") as f:
            r = self._post(f"{self.page}/photos", "programmation", files={"source": (image.name, f)},
                           message=texte, published="false", scheduled_publish_time=str(int(quand.timestamp())))
        pid = r.get("post_id") or r["id"]
        return Resultat(f"https://business.facebook.com/latest/posts/scheduled_posts?asset_id={self.page}", pid)

    def trouver_programme(self, texte: str) -> dict | None:
        """Cherche un post déjà programmé (ou publié récemment) au même texte, pour ne jamais doubler."""
        debut = texte.strip()[:120]
        for edge in ("scheduled_posts", "published_posts"):
            try:
                r = self._get(f"{self.page}/{edge}", fields="id,message,scheduled_publish_time,created_time",
                              limit=100)
            except ErreurPublication:
                continue
            for p in r.get("data", []):
                if (p.get("message") or "").strip()[:120] == debut:
                    quand = p.get("scheduled_publish_time") or p.get("created_time")
                    if isinstance(quand, int):
                        quand = datetime.fromtimestamp(quand, timezone.utc).isoformat()
                    return {"id": p["id"], "quand": str(quand)}
        return None


class FacebookShorts(Facebook):
    """Les Shorts du lot, en plus des visuels : vidéo programmée sur la Page, avec une légende courte
    (le texte complet est déjà sur le post visuel du même article)."""
    nom = "facebook_shorts"

    def programmer(self, texte: str, image: Path, quand, article: dict | None = None) -> Resultat:
        from ..scenario import _phrases, short_en_cache

        article = article or {}
        video = short_en_cache(article, image)
        accroche = ""
        for p in _phrases(article.get("body") or ""):
            if len(f"{accroche} {p}") > 300:
                break
            accroche = f"{accroche} {p}".strip()
        tags = " ".join(h if h.startswith("#") else f"#{h}" for h in article.get("hashtags") or [])
        legende = "\n\n".join(x for x in (article.get("title", ""), accroche, tags) if x)
        with video.open("rb") as f:
            r = self._post(f"{self.page}/videos", "programmation vidéo", base=f"https://graph-video.facebook.com/{self.v}",
                           files={"source": (video.name, f, "video/mp4")}, title=article.get("title", "")[:250],
                           description=legende, published="false", scheduled_publish_time=str(int(quand.timestamp())))
        return Resultat(f"https://business.facebook.com/latest/posts/scheduled_posts?asset_id={self.page}", r["id"])

    def trouver_programme(self, texte: str) -> dict | None:
        return None  # même texte que le post visuel : le journal (etat/lots.json) évite les doublons


def preparer_image_instagram(src: Path, dossier: Path) -> Path:
    """Instagram n'accepte que du JPEG, avec un ratio entre 4:5 et 1.91:1 → on convertit et on ajoute des marges blanches."""
    im = ImageOps.exif_transpose(Image.open(src)).convert("RGB")
    w, h = im.size
    ratio = w / h
    if ratio < 0.8:
        fond = Image.new("RGB", (math.ceil(h * 0.8), h), "white")
        fond.paste(im, ((fond.width - w) // 2, 0))
        im = fond
    elif ratio > 1.91:
        fond = Image.new("RGB", (w, math.ceil(w / 1.91)), "white")
        fond.paste(im, (0, (fond.height - h) // 2))
        im = fond
    if max(im.size) > 1440:
        im.thumbnail((1440, 1440))
    sortie = dossier / f"{src.stem}_ig.jpg"
    im.save(sortie, "JPEG", quality=92)
    return sortie


class Instagram(_Meta):
    nom = "instagram"
    variables = ("META_PAGE_ID", "META_PAGE_TOKEN", "INSTAGRAM_USER_ID")

    def __init__(self, cfg: dict):
        super().__init__(cfg)
        self.ig = os.environ.get("INSTAGRAM_USER_ID", "")

    def verifier(self) -> str:
        return "@" + self._get(self.ig, fields="username")["username"]

    def valider(self, post: Post) -> None:
        if not post.medias:
            raise ErreurDefinitive("Instagram exige au moins une image ou une vidéo dans le dossier")

    def _url_publique(self, img: Media, tmp: Path) -> tuple[str, str]:
        """Instagram télécharge l'image depuis une URL publique : on l'héberge en photo non publiée sur la Page."""
        photo_id = self._photo_non_publiee(preparer_image_instagram(img.chemin, tmp))
        images = self._get(photo_id, fields="images")["images"]
        return max(images, key=lambda i: i["width"])["source"], photo_id

    def _attendre_conteneur(self, cid: str, delai: int) -> None:
        def pret():
            s = self._get(cid, fields="status_code,status")
            if s.get("status_code") == "ERROR":
                raise ErreurPublication(f"Instagram a rejeté le média : {s.get('status')}")
            return s.get("status_code") == "FINISHED"
        attendre(pret, delai_max=delai, pas=5, contexte="Instagram traitement du média")

    def _reel(self, video: Media, texte: str) -> str:
        r = self._post(f"{self.ig}/media", "création conteneur Reel",
                       media_type="REELS", upload_type="resumable", caption=texte)
        with video.chemin.open("rb") as f:
            controler(requests.post(r["uri"], data=f, timeout=TIMEOUT, headers={
                "Authorization": f"OAuth {self.jeton}", "offset": "0", "file_size": str(video.taille),
            }), "instagram envoi vidéo")
        self._attendre_conteneur(r["id"], delai=900)
        return r["id"]

    def publier(self, post: Post, texte: str) -> Resultat:
        self.valider(post)
        temporaires: list[str] = []
        with tempfile.TemporaryDirectory() as d:
            tmp = Path(d)
            if post.videos:
                cid = self._reel(post.videos[0], texte)
            elif len(post.images) == 1:
                url, pid = self._url_publique(post.images[0], tmp)
                temporaires.append(pid)
                cid = self._post(f"{self.ig}/media", "création conteneur image", image_url=url, caption=texte)["id"]
                self._attendre_conteneur(cid, delai=120)
            else:
                enfants = []
                for img in post.images[:10]:
                    url, pid = self._url_publique(img, tmp)
                    temporaires.append(pid)
                    enfants.append(self._post(f"{self.ig}/media", "création image du carrousel",
                                              image_url=url, is_carousel_item="true")["id"])
                for e in enfants:
                    self._attendre_conteneur(e, delai=120)
                cid = self._post(f"{self.ig}/media", "création carrousel", media_type="CAROUSEL",
                                 children=",".join(enfants), caption=texte)["id"]
                self._attendre_conteneur(cid, delai=120)

            media_id = self._post(f"{self.ig}/media_publish", "publication", creation_id=cid)["id"]

        for pid in temporaires:  # ménage : supprime les photos d'hébergement temporaire de la Page
            try:
                requests.delete(f"{self.graph}/{pid}", params={"access_token": self.jeton}, timeout=TIMEOUT)
            except requests.RequestException:
                pass
        lien = self._get(media_id, fields="permalink").get("permalink", "")
        return Resultat(lien or f"instagram media {media_id}", media_id)
