"""Obtenir l'accès LinkedIn et l'enregistrer dans .env (rien n'est affiché).

    python scripts/jeton_linkedin.py page     -> publier sur une Page entreprise (produit « Community Management API »)
    python scripts/jeton_linkedin.py profil   -> publier sur votre profil (produits « Share on LinkedIn » + « Sign In with
                                                 LinkedIn using OpenID Connect »)

Prérequis : application sur https://www.linkedin.com/developers avec l'URL de redirection
http://localhost:8765/callback (onglet « Auth »).
"""
import getpass
import http.server
import secrets
import sys
import urllib.parse
import webbrowser
from pathlib import Path

import requests

ENV = Path(__file__).resolve().parent.parent / ".env"
REDIRECT = "http://localhost:8765/callback"
MODE = (sys.argv[1] if len(sys.argv) > 1 else "page").lower()
SCOPES = {"page": "w_organization_social r_organization_social rw_organization_admin",
          "profil": "openid profile w_member_social"}[MODE]


def ecrire_env(valeurs: dict) -> None:
    lignes = ENV.read_text(encoding="utf-8").splitlines() if ENV.exists() else []
    lignes = [l for l in lignes if l.split("=", 1)[0].strip() not in valeurs]
    lignes += [f"{k}={v}" for k, v in valeurs.items() if v]
    ENV.write_text("\n".join(lignes) + "\n", encoding="utf-8")


client_id = sys.argv[2] if len(sys.argv) > 2 else input("Client ID LinkedIn : ").strip()
client_secret = getpass.getpass("Collez le « Client Secret » LinkedIn (Ctrl+V), puis Entrée — rien ne s'affiche : ").strip()
print(f"→ {len(client_secret)} caractères reçus")
etat = secrets.token_urlsafe(16)
code = {}


class Rappel(http.server.BaseHTTPRequestHandler):
    def do_GET(self):
        q = urllib.parse.parse_qs(urllib.parse.urlparse(self.path).query)
        if q.get("state", [""])[0] == etat:
            code["valeur"] = q.get("code", [""])[0]
            code["erreur"] = q.get("error_description", [""])[0]
        self.send_response(200)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.end_headers()
        self.wfile.write("<h2>C'est bon, vous pouvez fermer cet onglet et revenir au terminal.</h2>".encode())

    def log_message(self, *a):
        pass


url = "https://www.linkedin.com/oauth/v2/authorization?" + urllib.parse.urlencode({
    "response_type": "code", "client_id": client_id, "redirect_uri": REDIRECT, "scope": SCOPES, "state": etat,
})
print("Une page LinkedIn s'ouvre dans votre navigateur : cliquez sur « Autoriser ».")
webbrowser.open(url)
serveur = http.server.HTTPServer(("localhost", 8765), Rappel)
while "valeur" not in code:
    serveur.handle_request()
if not code["valeur"]:
    raise SystemExit(f"Autorisation refusée : {code.get('erreur')}")

jeton = requests.post("https://www.linkedin.com/oauth/v2/accessToken", data={
    "grant_type": "authorization_code", "code": code["valeur"], "redirect_uri": REDIRECT,
    "client_id": client_id, "client_secret": client_secret,
}, timeout=30).json()
if "access_token" not in jeton:
    raise SystemExit(f"Échec : {jeton.get('error_description', jeton)}")

valeurs = {"LINKEDIN_ACCESS_TOKEN": jeton["access_token"], "LINKEDIN_REFRESH_TOKEN": jeton.get("refresh_token", "")}
if valeurs["LINKEDIN_REFRESH_TOKEN"]:
    valeurs.update({"LINKEDIN_CLIENT_ID": client_id, "LINKEDIN_CLIENT_SECRET": client_secret})
entetes = {"Authorization": f"Bearer {jeton['access_token']}", "LinkedIn-Version": "202608",
           "X-Restli-Protocol-Version": "2.0.0"}

if MODE == "profil":
    moi = requests.get("https://api.linkedin.com/v2/userinfo", headers=entetes, timeout=30).json()
    valeurs["LINKEDIN_PERSON_ID"] = moi["sub"]
    nom = f"profil « {moi.get('name', '?')} »"
else:
    acl = requests.get("https://api.linkedin.com/rest/organizationAcls", params={"q": "roleAssignee"},
                       headers=entetes, timeout=30).json().get("elements", [])
    orgs = [e["organization"].rsplit(":", 1)[1] for e in acl if e.get("role") == "ADMINISTRATOR"]
    if not orgs:
        raise SystemExit("Aucune Page LinkedIn dont vous êtes administrateur n'a été trouvée.")
    noms = []
    for oid in orgs:
        r = requests.get(f"https://api.linkedin.com/rest/organizations/{oid}", headers=entetes, timeout=30)
        noms.append(r.json().get("localizedName", oid) if r.ok else oid)
    for i, n in enumerate(noms, 1):
        print(f"  {i}. {n}")
    choix = int(input("Numéro de la Page à utiliser : ").strip() or 1) if len(orgs) > 1 else 1
    valeurs["LINKEDIN_ORG_ID"] = orgs[choix - 1]
    nom = f"Page « {noms[choix - 1]} »"

ecrire_env(valeurs)
duree = jeton.get("refresh_token_expires_in", jeton.get("expires_in", 0)) // 86400
print(f"\n✅ LinkedIn {nom} enregistré dans {ENV} (accès valable {duree} jours"
      + (", renouvelé automatiquement)" if valeurs["LINKEDIN_REFRESH_TOKEN"] else ")"))
