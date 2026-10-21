"""Page entreprise LinkedIn (API Posts + Images + Videos, versionnée)."""
from __future__ import annotations

import os
import re
from urllib.parse import quote

import requests

from ..models import Post
from .base import TIMEOUT, ErreurPublication, Publieur, Resultat, attendre, controler

API = "https://api.linkedin.com/rest"

# Caractères réservés du format « little text » de LinkedIn : non échappés, ils tronquent le post.
_RESERVES = re.compile(r"([\\|{}@\[\]()<>*_~])")
_HASHTAG = re.compile(r"#(\w+)", re.UNICODE)


def formater_commentaire(texte: str) -> str:
    morceaux, pos = [], 0
    for m in _HASHTAG.finditer(texte):
        morceaux.append(_RESERVES.sub(r"\\\1", texte[pos:m.start()]).replace("#", "\\#"))
        morceaux.append("{hashtag|\\#|" + m.group(1) + "}")
        pos = m.end()
    morceaux.append(_RESERVES.sub(r"\\\1", texte[pos:]).replace("#", "\\#"))
    return "".join(morceaux)


class LinkedIn(Publieur):
    nom = "linkedin"
    variables = ()

    @classmethod
    def manquantes(cls) -> list[str]:
        m = super().manquantes()
        if not os.environ.get("LINKEDIN_ORG_ID") and not os.environ.get("LINKEDIN_PERSON_ID"):
            m.append("LINKEDIN_ORG_ID (Page entreprise) ou LINKEDIN_PERSON_ID (profil)")
        if not os.environ.get("LINKEDIN_ACCESS_TOKEN") and not all(
            os.environ.get(v) for v in ("LINKEDIN_REFRESH_TOKEN", "LINKEDIN_CLIENT_ID", "LINKEDIN_CLIENT_SECRET")
        ):
            m.append("LINKEDIN_ACCESS_TOKEN (ou LINKEDIN_REFRESH_TOKEN + LINKEDIN_CLIENT_ID + LINKEDIN_CLIENT_SECRET)")
        return m

    def __init__(self, cfg: dict):
        super().__init__(cfg)
        # « org » = auteur des posts : la Page entreprise si elle est configurée, sinon le profil personnel
        if os.environ.get("LINKEDIN_ORG_ID"):
            self.org = f"urn:li:organization:{os.environ['LINKEDIN_ORG_ID']}"
        else:
            self.org = f"urn:li:person:{os.environ.get('LINKEDIN_PERSON_ID', '')}"
        self._jeton: str | None = None

    @property
    def jeton(self) -> str:
        if self._jeton is None:
            if os.environ.get("LINKEDIN_REFRESH_TOKEN"):
                # Le jeton d'accès dure 60 jours ; le refresh token (365 jours) permet d'en obtenir un neuf à chaque passage.
                r = controler(requests.post("https://www.linkedin.com/oauth/v2/accessToken", data={
                    "grant_type": "refresh_token",
                    "refresh_token": os.environ["LINKEDIN_REFRESH_TOKEN"],
                    "client_id": os.environ["LINKEDIN_CLIENT_ID"],
                    "client_secret": os.environ["LINKEDIN_CLIENT_SECRET"],
                }, timeout=TIMEOUT), "linkedin renouvellement du jeton")
                self._jeton = r.json()["access_token"]
            else:
                self._jeton = os.environ["LINKEDIN_ACCESS_TOKEN"]
        return self._jeton

    def _entetes(self) -> dict:
        return {
            "Authorization": f"Bearer {self.jeton}",
            "LinkedIn-Version": str(self.cfg["linkedin"]["version_api"]),
            "X-Restli-Protocol-Version": "2.0.0",
        }

    def verifier(self) -> str:
        if self.org.startswith("urn:li:person:"):
            r = controler(requests.get("https://api.linkedin.com/v2/userinfo", headers=self._entetes(),
                                       timeout=TIMEOUT), "linkedin lecture du profil")
            return "profil « " + r.json().get("name", "?") + " »"
        org_id = self.org.rsplit(":", 1)[1]
        r = requests.get(f"{API}/organizations/{org_id}", headers=self._entetes(), timeout=TIMEOUT)
        if r.status_code == 403:
            return f"jeton accepté (organisation {org_id} — lecture du nom non autorisée, la publication peut fonctionner)"
        controler(r, "linkedin lecture organisation")
        return "Page « " + r.json().get("localizedName", org_id) + " »"

    def _image(self, chemin) -> str:
        r = controler(requests.post(f"{API}/images?action=initializeUpload", headers=self._entetes(),
                                    json={"initializeUploadRequest": {"owner": self.org}}, timeout=TIMEOUT),
                      "linkedin préparation image").json()["value"]
        with open(chemin, "rb") as f:
            controler(requests.put(r["uploadUrl"], data=f, timeout=TIMEOUT,
                                   headers={"Authorization": f"Bearer {self.jeton}"}), "linkedin envoi image")
        return r["image"]

    def _video(self, media) -> str:
        r = controler(requests.post(f"{API}/videos?action=initializeUpload", headers=self._entetes(), json={
            "initializeUploadRequest": {"owner": self.org, "fileSizeBytes": media.taille,
                                        "uploadCaptions": False, "uploadThumbnail": False}
        }, timeout=TIMEOUT), "linkedin préparation vidéo").json()["value"]
        etags = []
        with media.chemin.open("rb") as f:
            for part in r["uploadInstructions"]:
                f.seek(part["firstByte"])
                bloc = f.read(part["lastByte"] - part["firstByte"] + 1)
                rep = controler(requests.put(part["uploadUrl"], data=bloc, timeout=TIMEOUT,
                                             headers={"Content-Type": "application/octet-stream"}),
                                "linkedin envoi vidéo")
                etags.append(rep.headers.get("ETag", "").strip('"'))
        controler(requests.post(f"{API}/videos?action=finalizeUpload", headers=self._entetes(), json={
            "finalizeUploadRequest": {"video": r["video"], "uploadToken": r.get("uploadToken", ""),
                                      "uploadedPartIds": etags}
        }, timeout=TIMEOUT), "linkedin finalisation vidéo")

        def disponible():
            s = controler(requests.get(f"{API}/videos/{quote(r['video'], safe='')}", headers=self._entetes(),
                                       timeout=TIMEOUT), "linkedin statut vidéo").json().get("status")
            if s == "PROCESSING_FAILED":
                raise ErreurPublication("LinkedIn n'a pas pu traiter la vidéo")
            return s == "AVAILABLE"
        attendre(disponible, delai_max=900, pas=10, contexte="LinkedIn traitement vidéo")
        return r["video"]

    def publier(self, post: Post, texte: str) -> Resultat:
        corps = {
            "author": self.org,
            "commentary": formater_commentaire(texte),
            "visibility": "PUBLIC",
            "distribution": {"feedDistribution": "MAIN_FEED", "targetEntities": [],
                             "thirdPartyDistributionChannels": []},
            "lifecycleState": "PUBLISHED",
            "isReshareDisabledByAuthor": False,
        }
        if post.videos:
            corps["content"] = {"media": {"id": self._video(post.videos[0]), "title": post.titre or ""}}
        elif len(post.images) == 1:
            corps["content"] = {"media": {"id": self._image(post.images[0].chemin)}}
        elif post.images:
            corps["content"] = {"multiImage": {"images": [{"id": self._image(i.chemin)} for i in post.images[:20]]}}

        r = controler(requests.post(f"{API}/posts", headers=self._entetes(), json=corps, timeout=TIMEOUT),
                      "linkedin publication")
        urn = r.headers.get("x-restli-id", "")
        return Resultat(f"https://www.linkedin.com/feed/update/{urn}/" if urn else "publié (lien indisponible)", urn)
