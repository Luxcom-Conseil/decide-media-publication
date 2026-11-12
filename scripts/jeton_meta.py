"""Obtenir un jeton de Page Facebook permanent + l'identifiant Instagram, et les enregistrer dans .env.

1. Sur https://developers.facebook.com/tools/explorer : choisir votre application, cliquer « Generate Access Token »
   avec les permissions : pages_show_list, pages_read_engagement, pages_manage_posts, pages_read_user_content
   (lire les commentaires), pages_manage_engagement (y répondre), read_insights (statistiques des posts)
   (+ instagram_basic, instagram_content_publish pour Instagram, + business_management si la Page est dans un
   Business Manager).
2. Lancer :  python scripts/jeton_meta.py
   et coller l'ID de l'application, sa clé secrète et le jeton obtenu (la saisie est masquée).

Les jetons ne sont jamais affichés : ils sont écrits dans le fichier .env du projet (ignoré par git), puis, si la
commande gh est connectée, dans les secrets GitHub du dépôt (META_PAGE_ID, META_PAGE_TOKEN), lus par les workflows.
"""
import getpass
import shutil
import subprocess
from pathlib import Path

import requests

V = "v25.0"
DEPOT = "Luxcom-Conseil/decide-media-publication"
ATTENDUES = ("pages_manage_posts", "pages_read_user_content", "pages_manage_engagement", "read_insights")
ENV = Path(__file__).resolve().parent.parent / ".env"


def ecrire_env(valeurs: dict) -> None:
    lignes = ENV.read_text(encoding="utf-8").splitlines() if ENV.exists() else []
    lignes = [l for l in lignes if l.split("=", 1)[0].strip() not in valeurs]
    lignes += [f"{k}={v}" for k, v in valeurs.items()]
    ENV.write_text("\n".join(lignes) + "\n", encoding="utf-8")


import sys


def secrets_github(valeurs: dict) -> None:
    """Copie META_PAGE_ID et META_PAGE_TOKEN dans les secrets du dépôt, sans les afficher."""
    gh = shutil.which("gh") or shutil.which("gh.exe") or next(
        (str(p) for p in (Path(r"C:\Program Files\GitHub CLI\gh.exe"),) if p.exists()), None)
    if not gh:
        print("✗ Commande gh introuvable : secrets GitHub non mis à jour.")
        return
    for nom in ("META_PAGE_ID", "META_PAGE_TOKEN"):
        r = subprocess.run([gh, "secret", "set", nom, "-R", DEPOT], input=valeurs[nom], text=True,
                           capture_output=True)
        print(f"    {'✓' if r.returncode == 0 else '✗'} {nom} dans GitHub" + ("" if r.returncode == 0 else " : refusé"))


if "--secrets" in sys.argv:  # recopier dans GitHub le jeton déjà écrit dans .env
    lu = dict(l.split("=", 1) for l in ENV.read_text(encoding="utf-8").splitlines() if "=" in l)
    secrets_github({k: lu[k].strip() for k in ("META_PAGE_ID", "META_PAGE_TOKEN")})
    raise SystemExit

app_id = sys.argv[1] if len(sys.argv) > 1 else input("ID de l'application Meta : ").strip()
court = getpass.getpass("Collez le jeton de l'Explorateur (Ctrl+V ou clic droit), puis Entrée — rien ne s'affiche, c'est normal : ").strip()
print(f"→ {len(court)} caractères reçus" + (" (un jeton Meta en compte en général plus de 150)" if len(court) < 100 else ""))
if not court:
    raise SystemExit("Rien n'a été collé : relancez le script et essayez Ctrl+V.")
secret = getpass.getpass("Clé secrète de l'application (facultatif : Entrée pour passer) : ").strip()

if secret:
    r = requests.get(f"https://graph.facebook.com/{V}/oauth/access_token", params={
        "grant_type": "fb_exchange_token", "client_id": app_id, "client_secret": secret, "fb_exchange_token": court,
    }, timeout=30)
    if r.status_code != 200:
        raise SystemExit(f"Échec de l'échange du jeton : {r.json().get('error', {}).get('message', r.text)}")
    long = r.json()["access_token"]
else:
    long = court  # mode test : le jeton de Page obtenu expire avec le jeton de l'Explorateur (~1 h)
    print("ℹ Sans clé secrète : accès temporaire (~1 h), suffisant pour un test.")

reponse = requests.get(f"https://graph.facebook.com/{V}/me/accounts", params={
    "access_token": long, "fields": "id,name,access_token,instagram_business_account{id,username}",
}, timeout=30).json()
if "error" in reponse:
    raise SystemExit(f"Facebook a refusé le jeton : {reponse['error'].get('message')}")
pages = reponse.get("data", [])

if not pages:
    raise SystemExit("Aucune Page trouvée : vérifiez que vous êtes administrateur de la Page et que les "
                     "permissions pages_show_list et pages_manage_posts sont cochées.")

for i, p in enumerate(pages, 1):
    ig = p.get("instagram_business_account") or {}
    print(f"  {i}. {p['name']}" + (f"   (Instagram @{ig.get('username', '?')})" if ig else ""))
choix = input("Numéro de la Page à utiliser : ").strip() if len(pages) > 1 else "1"
page = pages[int(choix) - 1]

valeurs = {"META_PAGE_ID": page["id"], "META_PAGE_TOKEN": page["access_token"]}
ig = page.get("instagram_business_account") or {}
if ig:
    valeurs["INSTAGRAM_USER_ID"] = ig["id"]
ecrire_env(valeurs)
print(f"\n✅ Page « {page['name']} » enregistrée dans {ENV}"
      + (f" (Instagram @{ig.get('username', '?')} aussi)" if ig else ""))
if secret:
    print("Ce jeton de Page n'expire pas tant que vous ne changez pas de mot de passe ni ne retirez l'application.")
else:
    print("⚠ Jeton temporaire (~1 h) : relancez ce script avec la clé secrète pour un accès permanent.")

# droits réellement accordés par Facebook (une case décochée dans la fenêtre de connexion ne donne pas d'erreur)
droits = requests.get(f"https://graph.facebook.com/{V}/me/permissions", params={"access_token": long}, timeout=30).json()
accordes = {d["permission"] for d in droits.get("data", []) if d.get("status") == "granted"}
manquants = [d for d in ATTENDUES if d not in accordes]
print("Droits accordés : " + ", ".join(sorted(accordes)))
if manquants:
    print("⚠ Manquent : " + ", ".join(manquants) + " — relancez l'Explorateur en les cochant.")

if input("Enregistrer aussi dans les secrets GitHub ? (o/N) ").strip().lower().startswith("o"):
    secrets_github(valeurs)
