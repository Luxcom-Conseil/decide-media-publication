"""Chaîne YouTube — API Data v3, envoi « resumable » (gros fichiers OK)."""
from __future__ import annotations

import os
from datetime import timezone
from pathlib import Path

from ..models import Post
from .base import ErreurDefinitive, ErreurPublication, Publieur, Resultat

SCOPES = ["https://www.googleapis.com/auth/youtube.upload", "https://www.googleapis.com/auth/youtube.readonly"]


class YouTube(Publieur):
    nom = "youtube"
    variables = ("YOUTUBE_CLIENT_ID", "YOUTUBE_CLIENT_SECRET", "YOUTUBE_REFRESH_TOKEN")

    def _service(self):
        from google.oauth2.credentials import Credentials
        from googleapiclient.discovery import build

        creds = Credentials(
            None,
            refresh_token=os.environ["YOUTUBE_REFRESH_TOKEN"],
            token_uri="https://oauth2.googleapis.com/token",
            client_id=os.environ["YOUTUBE_CLIENT_ID"],
            client_secret=os.environ["YOUTUBE_CLIENT_SECRET"],
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
        import tempfile

        from googleapiclient.errors import HttpError
        from googleapiclient.http import MediaFileUpload

        from ..scenario import rendre_video

        article = article or {}
        titre = _titre_youtube(article.get("title") or texte.split("\n")[0])
        hashtags = [h.lstrip("#") for h in article.get("hashtags", [])]
        description = (texte + "\n\n#Shorts").replace("<", "").replace(">", "")[:5000]
        # ignore_cleanup_errors : sous Windows, le module d'envoi garde parfois le fichier ouvert un instant
        with tempfile.TemporaryDirectory(ignore_cleanup_errors=True) as d:
            # motion design explicatif (Remotion), sans voix, avec mélodie de fond à 10 %
            video = rendre_video({**article, "title": article.get("title") or titre}, image, Path(d) / "short.mp4")
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
                if e.status_code == 403 and "quota" in str(e).lower():
                    raise ErreurPublication("youtube : quota du jour épuisé (≈ 6 vidéos/jour) — réessai demain") from None
                raise ErreurPublication(f"youtube : HTTP {e.status_code} — {e.reason}") from None
            finally:
                fd = getattr(media, "_fd", None)  # libère le fichier avant la suppression du dossier temporaire
                if fd:
                    fd.close()
        vid = reponse["id"]
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
                return {"id": it["snippet"]["resourceId"]["videoId"], "quand": it["snippet"].get("publishedAt", "")}
        return None


def _titre_youtube(titre: str) -> str:
    titre = titre.replace("<", "").replace(">", "").strip()
    return titre if len(titre) <= 100 else titre[:99].rstrip() + "…"
