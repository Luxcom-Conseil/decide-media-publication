"""Où l'agent va chercher les publications : un dossier Google Drive (production) ou un dossier local (tests).

Chaque sous-dossier du dossier racine = une publication :
    📁 2026-10-20 Lancement offre/
        post.txt   (ou un Google Doc nommé « post »)
        visuel-1.jpg, visuel-2.jpg, video.mp4, miniature.jpg …

Une fois traité, le sous-dossier est renommé « [PUBLIÉ] … », « [PARTIEL] … » ou « [ÉCHEC] … »,
et le compte rendu (liens des posts, erreurs) est écrit dans sa description.
"""
from __future__ import annotations

import io
import json
import os
from dataclasses import dataclass
from pathlib import Path

from .models import est_miniature, type_media


@dataclass
class Dossier:
    id: str
    nom: str


@dataclass
class Fichier:
    id: str
    nom: str
    mime: str


class Source:
    def lister_dossiers(self) -> list[Dossier]: ...
    def lister_fichiers(self, dossier: Dossier) -> list[Fichier]: ...
    def lire_texte(self, fichier: Fichier) -> str: ...
    def telecharger(self, fichier: Fichier, destination: Path) -> Path: ...
    def marquer(self, dossier: Dossier, prefixe: str | None, rapport: str) -> None: ...

    def trouver_post(self, fichiers: list[Fichier], noms_acceptes: list[str]) -> Fichier | None:
        par_nom = {f.nom.lower(): f for f in fichiers}
        for nom in noms_acceptes:
            if nom.lower() in par_nom:
                return par_nom[nom.lower()]
        return None

    @staticmethod
    def medias(fichiers: list[Fichier]) -> list[Fichier]:
        return sorted((f for f in fichiers if type_media(f.nom)), key=lambda f: f.nom.lower())


# --------------------------------------------------------------------------- Google Drive

GDOC = "application/vnd.google-apps.document"
GFOLDER = "application/vnd.google-apps.folder"


class SourceDrive(Source):
    """Accès via un compte de service Google : partager le dossier racine avec son e-mail, en « Éditeur »."""

    def __init__(self, dossier_racine_id: str, identifiants_json: str):
        from google.oauth2 import service_account
        from googleapiclient.discovery import build

        creds = service_account.Credentials.from_service_account_info(
            json.loads(identifiants_json), scopes=["https://www.googleapis.com/auth/drive"]
        )
        self.svc = build("drive", "v3", credentials=creds, cache_discovery=False)
        self.racine = dossier_racine_id

    @classmethod
    def depuis_env(cls) -> "SourceDrive":
        identifiants = os.environ.get("GOOGLE_SERVICE_ACCOUNT_JSON", "")
        fichier = os.environ.get("GOOGLE_SERVICE_ACCOUNT_FILE", "") or cls._trouver_cle()
        if not identifiants and fichier and os.path.exists(fichier):
            with open(fichier, encoding="utf-8") as f:
                identifiants = f.read()
        if not os.environ.get("DRIVE_FOLDER_ID") or not identifiants:
            raise SystemExit("Accès Google Drive non configuré : DRIVE_FOLDER_ID et la clé du compte de service "
                             "(GOOGLE_SERVICE_ACCOUNT_FILE ou GOOGLE_SERVICE_ACCOUNT_JSON) sont nécessaires.")
        return cls(os.environ["DRIVE_FOLDER_ID"], identifiants)

    @staticmethod
    def _trouver_cle() -> str:
        """Clé du compte de service : cle-google.json dans le projet, sinon la plus récente
        decide-publication-*.json du dossier Téléchargements (là où Google Cloud la dépose)."""
        projet = Path(__file__).resolve().parent.parent / "cle-google.json"
        if projet.exists():
            return str(projet)
        telechargements = sorted((Path.home() / "Downloads").glob("decide-publication-*.json"),
                                 key=lambda p: p.stat().st_mtime, reverse=True)
        return str(telechargements[0]) if telechargements else ""

    def lire_brut(self, fichier: "Fichier") -> bytes:
        return self.svc.files().get_media(fileId=fichier.id, supportsAllDrives=True).execute()

    def telecharger_id(self, file_id: str, nom: str, destination: Path) -> Path:
        return self.telecharger(Fichier(file_id, Path(nom).name, ""), destination)

    def _enfants(self, parent_id: str) -> list[dict]:
        out, token = [], None
        while True:
            r = self.svc.files().list(
                q=f"'{parent_id}' in parents and trashed = false",
                fields="nextPageToken, files(id, name, mimeType)",
                pageSize=1000, pageToken=token,
                supportsAllDrives=True, includeItemsFromAllDrives=True,
            ).execute()
            out += r.get("files", [])
            token = r.get("nextPageToken")
            if not token:
                return out

    def lister_dossiers(self) -> list[Dossier]:
        return sorted(
            (Dossier(f["id"], f["name"]) for f in self._enfants(self.racine) if f["mimeType"] == GFOLDER),
            key=lambda d: d.nom.lower(),
        )

    def lister_fichiers(self, dossier: Dossier) -> list[Fichier]:
        return [Fichier(f["id"], f["name"], f["mimeType"]) for f in self._enfants(dossier.id)
                if f["mimeType"] != GFOLDER]

    def lire_texte(self, fichier: Fichier) -> str:
        if fichier.mime == GDOC:
            data = self.svc.files().export_media(fileId=fichier.id, mimeType="text/plain").execute()
        else:
            data = self.svc.files().get_media(fileId=fichier.id, supportsAllDrives=True).execute()
        return data.decode("utf-8-sig", errors="replace")

    def telecharger(self, fichier: Fichier, destination: Path) -> Path:
        from googleapiclient.http import MediaIoBaseDownload

        chemin = destination / fichier.nom
        requete = self.svc.files().get_media(fileId=fichier.id, supportsAllDrives=True)
        with io.FileIO(chemin, "wb") as fh:
            dl = MediaIoBaseDownload(fh, requete, chunksize=16 * 1024 * 1024)
            fini = False
            while not fini:
                _, fini = dl.next_chunk(num_retries=3)
        return chemin

    def marquer(self, dossier: Dossier, prefixe: str | None, rapport: str) -> None:
        # Renommer + description = métadonnées : aucun quota de stockage requis pour le compte de service.
        corps = {"description": rapport[:4000]}
        if prefixe:
            corps["name"] = f"{prefixe} {dossier.nom}"
        self.svc.files().update(fileId=dossier.id, body=corps, supportsAllDrives=True).execute()


# --------------------------------------------------------------------------- Dossier local

class SourceLocale(Source):
    def __init__(self, racine: str | Path):
        self.racine = Path(racine)
        if not self.racine.is_dir():
            raise SystemExit(f"Dossier introuvable : {self.racine}")

    def lister_dossiers(self) -> list[Dossier]:
        return sorted((Dossier(str(p), p.name) for p in self.racine.iterdir() if p.is_dir()),
                      key=lambda d: d.nom.lower())

    def lister_fichiers(self, dossier: Dossier) -> list[Fichier]:
        return [Fichier(str(p), p.name, "") for p in Path(dossier.id).iterdir() if p.is_file()]

    def lire_texte(self, fichier: Fichier) -> str:
        return Path(fichier.id).read_text(encoding="utf-8-sig")

    def telecharger(self, fichier: Fichier, destination: Path) -> Path:
        return Path(fichier.id)  # déjà sur le disque

    def marquer(self, dossier: Dossier, prefixe: str | None, rapport: str) -> None:
        p = Path(dossier.id)
        (p / "_rapport.txt").write_text(rapport, encoding="utf-8")
        if prefixe:
            p.rename(p.with_name(f"{prefixe} {p.name}"))


__all__ = ["Dossier", "Fichier", "Source", "SourceDrive", "SourceLocale", "est_miniature"]
