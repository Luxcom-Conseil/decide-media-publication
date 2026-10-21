"""Obtenir l'accès YouTube (une seule fois) et l'enregistrer dans .env — rien n'est affiché.

Prérequis : identifiant OAuth « Application de bureau » du projet Google Cloud, téléchargé (fichier
client_secret_….json, laissé dans Téléchargements ou passé en argument).

    python scripts/jeton_youtube.py [chemin/vers/client_secret.json]

Une page Google s'ouvre : choisissez le compte, puis la chaîne DECIDE MEDIA, et autorisez.
"""
import sys
from pathlib import Path

from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build

SCOPES = ["https://www.googleapis.com/auth/youtube.upload", "https://www.googleapis.com/auth/youtube.readonly"]
ENV = Path(__file__).resolve().parent.parent / ".env"


def ecrire_env(valeurs: dict) -> None:
    lignes = ENV.read_text(encoding="utf-8").splitlines() if ENV.exists() else []
    lignes = [l for l in lignes if l.split("=", 1)[0].strip() not in valeurs]
    lignes += [f"{k}={v}" for k, v in valeurs.items()]
    ENV.write_text("\n".join(lignes) + "\n", encoding="utf-8")


if len(sys.argv) > 1:
    fichier = Path(sys.argv[1])
else:
    candidats = sorted((Path.home() / "Downloads").glob("client_secret*.json"), key=lambda p: p.stat().st_mtime,
                       reverse=True)
    if not candidats:
        raise SystemExit("Fichier client_secret….json introuvable dans Téléchargements.")
    fichier = candidats[0]
print(f"Identifiant utilisé : {fichier.name}")
print("Une page Google s'ouvre : choisissez votre compte, puis la chaîne DECIDE MEDIA, et cliquez sur « Autoriser ».")

flow = InstalledAppFlow.from_client_secrets_file(str(fichier), SCOPES)
creds = flow.run_local_server(port=0, access_type="offline", prompt="consent",
                              success_message="C'est bon, vous pouvez fermer cet onglet et revenir au terminal.")
if not creds.refresh_token:
    raise SystemExit("Google n'a pas fourni de jeton durable : relancez le script.")

ecrire_env({"YOUTUBE_CLIENT_ID": creds.client_id, "YOUTUBE_CLIENT_SECRET": creds.client_secret,
            "YOUTUBE_REFRESH_TOKEN": creds.refresh_token})  # enregistré d'abord : une erreur ensuite ne fait rien perdre
try:
    chaine = build("youtube", "v3", credentials=creds, cache_discovery=False).channels().list(
        part="snippet", mine=True).execute().get("items", [])
    nom = chaine[0]["snippet"]["title"] if chaine else "?"
except Exception as e:
    raise SystemExit(f"Accès enregistré, mais lecture de la chaîne impossible : {e}")
print(f"\n✅ Chaîne YouTube « {nom} » enregistrée dans {ENV}")
if "decide" not in nom.lower():
    print("⚠ Ce n'est pas la chaîne DECIDE MEDIA : relancez le script et choisissez la bonne chaîne.")
