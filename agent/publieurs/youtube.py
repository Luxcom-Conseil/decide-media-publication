"""Chaîne YouTube — API Data v3, envoi « resumable » (gros fichiers OK)."""
from __future__ import annotations

import os
from datetime import timezone
from pathlib import Path

from ..models import Post
from .base import ErreurDefinitive, ErreurLimite, ErreurPublication, Publieur, Resultat

SCOPES = ["https://www.googleapis.com/auth/youtube.upload", "https://www.googleapis.com/auth/youtube.readonly"]


class YouTube(Publieur):
    nom = "youtube"
    suffixe = ""  # YouTubeBurkina : variables YOUTUBE_…_BURKINA (autre chaîne, autre projet Google Cloud, autre quota)
    variables = ("YOUTUBE_CLIENT_ID", "YOUTUBE_CLIENT_SECRET", "YOUTUBE_REFRESH_TOKEN")

    def _service(self):
        from google.oauth2.credentials import Credentials
        from googleapiclient.discovery import build

        s = self.suffixe
        creds = Credentials(
            None,
            refresh_token=os.environ["YOUTUBE_REFRESH_TOKEN" + s],
            token_uri="https://oauth2.googleapis.com/token",
            client_id=os.environ["YOUTUBE_CLIENT_ID" + s],
            client_secret=os.environ["YOUTUBE_CLIENT_SECRET" + s],
            scopes=SCOPES,
        )
        return build("youtube", "v3", credentials=creds, cache_discovery=False)

    def verifier(self) -> str:
        items = self._service().channels().list(part="snippet", mine=True).execute().get("items", [])
        if not items:
            raise ErreurPublication("aucune chaîne YouTube liée à ce compte Google")
        return "Chaîne « " + items[0]["snippet"]["title"] + " »"

    def valider(self, post: Post) -> None:
        if not post.videos:
            raise ErreurDefinitive("YouTube exige une vidéo dans le dossier")

    def publier(self, post: Post, texte: str) -> Resultat:
        from googleapiclient.errors import HttpError
        from googleapiclient.http import MediaFileUpload

        self.valider(post)
        video = post.videos[0]
        titre = (post.titre or texte.strip().split("\n")[0])[:100].replace("<", "").replace(">", "")
        corps = {
            "snippet": {
                "title": titre,
                "description": texte[:5000].replace("<", "").replace(">", ""),
                "tags": post.tags[:30],
                "categoryId": str(self.cfg["youtube"]["categorie"]),
                "defaultLanguage": "fr",
            },
            "status": {
                "privacyStatus": post.youtube_visibilite or self.cfg["youtube"]["visibilite_defaut"],
                "selfDeclaredMadeForKids": False,
            },
        }
        svc = self._service()
        try:
            req = svc.videos().insert(part="snippet,status", body=corps, media_body=MediaFileUpload(
                str(video.chemin), mimetype=video.mime, chunksize=16 * 1024 * 1024, resumable=True))
            reponse = None
            while reponse is None:
                _, reponse = req.next_chunk(num_retries=3)
            vid = reponse["id"]
            if post.miniature:
                try:
                    svc.thumbnails().set(videoId=vid, media_body=MediaFileUpload(str(post.miniature))).execute()
                except HttpError as e:  # chaîne non vérifiée : la vidéo est publiée quand même
                    print(f"    ⚠ miniature refusée par YouTube : {e.reason}")
        except HttpError as e:
            raise ErreurPublication(f"youtube : HTTP {e.status_code} — {e.reason}") from None
        return Resultat(f"https://youtu.be/{vid}", vid)

    # ---- lots : un Short fabriqué à partir du visuel, programmé dans le planificateur YouTube

    def programmer(self, texte: str, image: Path, quand, article: dict | None = None) -> Resultat:
        """Fabrique le Short (visuel + voix off) puis l'envoie en privé avec publishAt :
        YouTube le rend public lui-même à l'heure dite."""
        from googleapiclient.errors import HttpError
        from googleapiclient.http import MediaFileUpload

        from ..scenario import short_en_cache

        article = article or {}
        titre = _titre_youtube(article.get("title") or texte.split("\n")[0])
        hashtags = [h.lstrip("#") for h in article.get("hashtags", [])]
        description = (texte + "\n\n#Shorts").replace("<", "").replace(">", "")[:5000]
        # motion design explicatif (Remotion), sans voix, avec mélodie de fond à 10 % ; gardé pour X et LinkedIn
        video = short_en_cache({**article, "title": article.get("title") or titre}, image)
        corps = {
            "snippet": {"title": titre, "description": description, "tags": hashtags[:15] + ["DECIDE MEDIA"],
                        "categoryId": str(self.cfg["youtube"].get("categorie_lots", "25")),
                        "defaultLanguage": "fr", "defaultAudioLanguage": "fr"},
            "status": {"privacyStatus": "private",
                       "publishAt": quand.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.000Z"),
                       "selfDeclaredMadeForKids": False,
                       "containsSyntheticMedia": True},  # illustrations générées
        }
        media = MediaFileUpload(str(video), mimetype="video/mp4", chunksize=8 * 1024 * 1024, resumable=True)
        try:
            req = self._service().videos().insert(part="snippet,status", body=corps, media_body=media)
            reponse = None
            while reponse is None:
                _, reponse = req.next_chunk(num_retries=3)
        except HttpError as e:
            if "quota" in str(e).lower() or "uploadlimitexceeded" in str(e).lower() or "number of videos" in str(e):
                raise ErreurLimite("youtube : limite d'envoi du jour atteinte (≈ 10 vidéos/jour) — réessai au prochain passage") from None
            raise ErreurPublication(f"youtube : HTTP {e.status_code} — {e.reason}") from None
        finally:
            fd = getattr(media, "_fd", None)  # sous Windows, le module d'envoi garde sinon le fichier ouvert
            if fd:
                fd.close()
        vid = reponse["id"]
        from ..gabarit_v3 import couverture
        jpg = couverture(video)
        if jpg.exists():  # miniature personnalisée : la chaîne doit être vérifiée, sinon refus sans effet sur le Short
            try:
                self._service().thumbnails().set(videoId=vid, media_body=MediaFileUpload(str(jpg), mimetype="image/jpeg")).execute()
            except HttpError as e:
                print(f"    ⚠ miniature refusée par YouTube : {e.reason}")
        return Resultat(f"https://youtu.be/{vid}", vid)

    def trouver_programme(self, texte: str) -> dict | None:
        """Cherche parmi les 50 dernières vidéos de la chaîne (programmées comprises) une vidéo au même titre."""
        titre = _titre_youtube(texte.split("\n")[0])
        try:
            svc = self._service()
            chaine = svc.channels().list(part="contentDetails", mine=True).execute()["items"][0]
            uploads = chaine["contentDetails"]["relatedPlaylists"]["uploads"]
            items = svc.playlistItems().list(part="snippet,status", playlistId=uploads, maxResults=50).execute()
        except Exception:
            return None
        for it in items.get("items", []):
            if it["snippet"].get("title", "").strip() == titre:
                vid = it["snippet"]["resourceId"]["videoId"]
                statut = svc.videos().list(part="status", id=vid).execute()["items"][0]["status"]
                return {"id": vid, "quand": statut.get("publishAt", "").replace("Z", "+00:00")}  # heure de diffusion
        return None


def _titre_youtube(titre: str) -> str:
    titre = titre.replace("<", "").replace(">", "").strip()
    return titre if len(titre) <= 100 else titre[:99].rstrip() + "…"


class YouTubeBurkina(YouTube):
    """Chaîne « Actu Burkina - Decide Media » par l'API directe (23/11/2026) : Buffer n'y programme que 2 Shorts par jour.
    Son propre projet Google Cloud, donc son propre quota d'envoi, séparé de celui du Cameroun."""
    nom = "youtube_bf"
    suffixe = "_BURKINA"
    variables = ("YOUTUBE_CLIENT_ID_BURKINA", "YOUTUBE_CLIENT_SECRET_BURKINA", "YOUTUBE_REFRESH_TOKEN_BURKINA")


class YouTubeHistoires(YouTube):
    """Chaîne « Histoires vraies d'argent » par l'API directe (24/11/2026) : Buffer gratuit n'y programmait que 2 Shorts
    par jour. Son propre projet Google Cloud (10 000 unités par jour, 1 600 par envoi : 6 vidéos par jour au plus)."""
    nom = "youtube_hv"
    suffixe = "_HISTOIRES"
    variables = ("YOUTUBE_CLIENT_ID_HISTOIRES", "YOUTUBE_CLIENT_SECRET_HISTOIRES", "YOUTUBE_REFRESH_TOKEN_HISTOIRES")

    def __init__(self, cfg: dict | None = None):  # utilisé hors de l'orchestrateur (agent/histoires.py)
        self.cfg = cfg or {}

    def programmer_fichier(self, video: Path, titre: str, description: str, quand, categorie: str = "27") -> str:
        """Envoie le MP4 en privé avec publishAt : YouTube le rend public lui-même à l'heure dite. Renvoie l'ID."""
        from googleapiclient.errors import HttpError
        from googleapiclient.http import MediaFileUpload

        corps = {"snippet": {"title": _titre_youtube(titre), "categoryId": str(categorie), "defaultLanguage": "fr",
                             "defaultAudioLanguage": "fr",
                             "description": (description + "\n\n#Shorts").replace("<", "").replace(">", "")[:5000]},
                 "status": {"privacyStatus": "private", "selfDeclaredMadeForKids": False, "containsSyntheticMedia": True,
                            "publishAt": quand.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.000Z")}}
        media = MediaFileUpload(str(video), mimetype="video/mp4", chunksize=8 * 1024 * 1024, resumable=True)
        try:
            req = self._service().videos().insert(part="snippet,status", body=corps, media_body=media)
            reponse = None
            while reponse is None:
                _, reponse = req.next_chunk(num_retries=3)
        except HttpError as e:
            if "quota" in str(e).lower() or "uploadlimitexceeded" in str(e).lower():
                raise ErreurLimite("youtube : limite d'envoi du jour atteinte") from None
            raise ErreurPublication(f"youtube : HTTP {e.status_code} — {e.reason}") from None
        finally:
            fd = getattr(media, "_fd", None)
            if fd:
                fd.close()
        return reponse["id"]


class YouTubeAfrique(YouTube):
    """Chaîne « DECIDE MEDIA Afrique » par l'API directe, avec son propre projet Google Cloud (préparé le 23/11/2026,
    à activer dans antennes.afrique.lots.reseaux une fois les secrets YOUTUBE_*_AFRIQUE en place)."""
    nom = "youtube_af"
    suffixe = "_AFRIQUE"
    variables = ("YOUTUBE_CLIENT_ID_AFRIQUE", "YOUTUBE_CLIENT_SECRET_AFRIQUE", "YOUTUBE_REFRESH_TOKEN_AFRIQUE")


class YouTubeBenin(YouTube):
    """Chaîne « Actu Bénin - DECIDE MEDIA » par l'API directe, avec son propre projet Google Cloud (son propre quota),
    préparée le 27/11/2026 ; secrets YOUTUBE_*_BENIN."""
    nom = "youtube_bj"
    suffixe = "_BENIN"
    variables = ("YOUTUBE_CLIENT_ID_BENIN", "YOUTUBE_CLIENT_SECRET_BENIN", "YOUTUBE_REFRESH_TOKEN_BENIN")
