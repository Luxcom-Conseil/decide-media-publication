# Agent de publication réseaux sociaux (Google Drive → Facebook, Instagram, LinkedIn, X, YouTube)

Vous déposez vos textes, visuels et vidéos dans un dossier Google Drive. L'agent, hébergé gratuitement sur
GitHub Actions, passe toutes les 2 heures et :

1. **lit** chaque sous-dossier du Drive (= une publication) ;
2. **attend** la date et l'heure de programmation indiquées ;
3. **adapte** le texte à chaque réseau avec Claude (longueur, ton, hashtags), sauf si vous avez écrit une version vous-même ;
4. **publie** sur les réseaux demandés, avec les médias ;
5. **renomme** le dossier `[PUBLIÉ]`, `[PARTIEL]` ou `[ÉCHEC]` et écrit dans sa **description** les liens des posts ou les erreurs.

Il ne publie jamais deux fois la même chose : sa mémoire est le fichier `etat/etat.json`, enregistré dans le dépôt après chaque passage.

---

## 1. Préparer une publication dans le Drive

```
📁 Réseaux sociaux            ← dossier racine (son ID va dans DRIVE_FOLDER_ID)
   📁 2026-10-20 Audit SEO offert
      📄 post.txt              ← ou un Google Doc nommé « post »
      🖼 1-visuel.jpg
      🖼 2-visuel.jpg
      🎬 video.mp4
      🖼 miniature.jpg         ← facultatif : miniature YouTube
   📁 _modèles                 ← dossiers commençant par _ ou [ : ignorés
```

Contenu du fichier **post** :

```
date: 20/10/2026 09:30
reseaux: facebook, linkedin, instagram, x, youtube
titre: Comment apparaître sur Google Maps à Angoulême
tags: seo local, google maps, angoulême
ia: oui
---
Le texte commun, écrit une fois pour tous les réseaux.
Les liens, emojis et #hashtags sont conservés.

[x]
(facultatif) Version écrite à la main pour X. Elle remplace celle de l'IA.

[linkedin]
(facultatif) Version écrite à la main pour LinkedIn.
```

| Champ | Valeurs | Obligatoire |
|---|---|---|
| `date` | `20/10/2026 09:30`, `2026-10-20 09:30`, `20/10/2026 9h30` ou `maintenant` (heure de Paris) | non (absent = dès que possible) |
| `reseaux` | `facebook, instagram, linkedin, x, youtube` ou `tous` (`twitter`, `insta` acceptés) | **oui** |
| `titre` | titre de la vidéo YouTube (sinon proposé par l'IA) | non |
| `tags` | mots-clés YouTube, séparés par des virgules | non |
| `ia` | `oui` / `non` : adapter le texte avec Claude | non (oui) |
| `youtube_visibilite` | `public`, `unlisted`, `private` | non |

**Médias, réseau par réseau** (ordre = ordre alphabétique des noms de fichiers) :

| Réseau | Ce qui est publié |
|---|---|
| Facebook | 1 vidéo, sinon jusqu'à 10 images, sinon texte seul |
| Instagram | 1 vidéo en Reel, sinon 1 image, ou un carrousel de 2 à 10 images. **Média obligatoire.** Les images sont converties en JPEG et recadrées avec des marges blanches si leur format sort de 4:5 – 1.91:1 |
| LinkedIn | 1 vidéo, sinon 1 à 20 images, sinon texte seul |
| X | 1 vidéo ou jusqu'à 4 images, texte coupé proprement à 280 caractères |
| YouTube | la vidéo (**obligatoire**) + miniature si `miniature.jpg` est présent |

> 💡 Écrivez d'abord le texte et déposez les médias, puis créez le fichier `post` en dernier : l'agent ignore un dossier tant qu'il n'a pas de fichier `post`.

**Après publication**, ouvrez « Détails » du dossier dans Drive : la description contient les liens.
**Pour relancer** un réseau en échec (jeton corrigé, par exemple), retirez simplement le préfixe `[PARTIEL]` / `[ÉCHEC]`
du nom du dossier : seuls les réseaux non publiés sont retentés.

---

## 2. Mettre l'outil sur GitHub

1. Créez un dépôt **privé** sur github.com (ex. `agent-reseaux-sociaux`) et envoyez-y ce dossier :
   ```bash
   git init && git add . && git commit -m "Agent de publication" && git branch -M main
   ```
   ```bash
   git remote add origin https://github.com/VOTRE-COMPTE/agent-reseaux-sociaux.git && git push -u origin main
   ```
2. Dans le dépôt : **Settings → Secrets and variables → Actions → New repository secret**, ajoutez les secrets
   ci-dessous (seulement pour les réseaux que vous utilisez : un réseau sans secrets est simplement ignoré).
3. Onglet **Actions** → « Publication réseaux sociaux » → **Run workflow** avec `commande = verifier` :
   chaque accès est testé sans rien publier.
4. Puis **Run workflow** avec `simulation` coché : l'agent affiche, dans le résumé du passage, les textes exacts
   qu'il publierait (y compris les versions de l'IA) pour tous les dossiers, même programmés plus tard.

> **Fréquence** : un passage toutes les 2 heures, à l'heure paire UTC (soit 9h, 11h, 13h… en heure de Paris l'hiver,
> 10h, 12h, 14h… l'été). Un post programmé à 9h30 part donc au passage suivant. Pour publier à l'heure exacte,
> choisissez une heure de passage dans `date:`. Consommation ≈ 360 à 500 min/mois, largement dans les 2 000 min
> gratuites d'un dépôt privé. Fréquence modifiable dans `.github/workflows/publier.yml` (ligne `cron`).

### Secrets à créer

| Secret | Où le trouver |
|---|---|
| `ANTHROPIC_API_KEY` | console.anthropic.com → API Keys (facultatif : sans clé, le texte d'origine est publié) |
| `DRIVE_FOLDER_ID` | l'URL du dossier racine : `drive.google.com/drive/folders/`**`CET_ID`** |
| `GOOGLE_SERVICE_ACCOUNT_JSON` | contenu complet du fichier JSON du compte de service (voir ci-dessous) |
| `META_PAGE_ID`, `META_PAGE_TOKEN` | `python scripts/jeton_meta.py` |
| `INSTAGRAM_USER_ID` | idem (affiché par le même script) |
| `LINKEDIN_ORG_ID` + `LINKEDIN_ACCESS_TOKEN` | `python scripts/jeton_linkedin.py` |
| `LINKEDIN_REFRESH_TOKEN`, `LINKEDIN_CLIENT_ID`, `LINKEDIN_CLIENT_SECRET` | idem, si LinkedIn vous délivre un refresh token (recommandé) |
| `X_API_KEY`, `X_API_SECRET`, `X_ACCESS_TOKEN`, `X_ACCESS_TOKEN_SECRET` | developer.x.com → votre app → Keys and tokens |
| `YOUTUBE_CLIENT_ID`, `YOUTUBE_CLIENT_SECRET`, `YOUTUBE_REFRESH_TOKEN` | `python scripts/jeton_youtube.py` |

Les scripts s'exécutent **une fois, sur votre ordinateur** (`pip install -r requirements.txt` d'abord).

---

## 3. Créer les accès, réseau par réseau

### Google Drive (compte de service)
1. console.cloud.google.com → créez un projet → **API et services → Bibliothèque** → activez **Google Drive API**.
2. **IAM → Comptes de service → Créer**, puis onglet **Clés → Ajouter une clé → JSON** : un fichier est téléchargé.
3. Copiez l'e-mail du compte de service (`…@….iam.gserviceaccount.com`) et **partagez le dossier racine Drive avec lui en Éditeur**
   (Éditeur est nécessaire pour renommer les dossiers et écrire le compte rendu).
4. Collez tout le contenu du fichier JSON dans le secret `GOOGLE_SERVICE_ACCOUNT_JSON`, puis supprimez le fichier.

### Facebook + Instagram (une seule application Meta)
1. Le compte Instagram doit être **professionnel** et **relié à la Page Facebook** (Paramètres de la Page → Comptes liés).
2. developers.facebook.com → **Créer une app** (type « Entreprise ») → ajoutez les cas d'usage *Gérer une Page* et *Instagram (API avec connexion Facebook)*.
3. Ouvrez l'**Explorateur de l'API Graph**, choisissez l'app, générez un jeton avec : `pages_show_list`,
   `pages_read_engagement`, `pages_manage_posts`, `instagram_basic`, `instagram_content_publish`, `business_management`.
4. `python scripts/jeton_meta.py` → collez l'ID de l'app, sa clé secrète et ce jeton : le script affiche
   `META_PAGE_ID`, un `META_PAGE_TOKEN` **sans expiration** et `INSTAGRAM_USER_ID`.

Tant que l'app reste en mode développement, elle ne fonctionne que pour ses administrateurs, ce qui suffit pour
publier sur vos propres comptes.

### LinkedIn (Page entreprise)
1. linkedin.com/developers → **Create app**, associée à votre Page entreprise.
2. Onglet **Products** → demandez **Community Management API** : c'est le seul produit qui permet de publier au nom
   d'une Page. LinkedIn vérifie la demande (entreprise enregistrée, parfois plusieurs jours).
3. Onglet **Auth** → ajoutez l'URL de redirection `http://localhost:8765/callback`.
4. `python scripts/jeton_linkedin.py` → affiche le jeton, le refresh token éventuel et l'ID de votre Page.

Le jeton d'accès LinkedIn **expire au bout de 60 jours**. Avec le refresh token (valable 365 jours), l'agent le
renouvelle seul à chaque passage. Sans refresh token, relancez le script tous les ~55 jours.

### X (Twitter)
1. developer.x.com → créez un projet et une app.
2. **User authentication settings** → permissions **Read and write** (à régler *avant* de générer les jetons).
3. **Keys and tokens** → copiez l'API Key/Secret, puis générez l'**Access Token and Secret**.
4. ⚠ L'API X est payante au-delà d'un petit volume, et ses offres changent souvent : vérifiez sur developer.x.com
   que votre formule autorise l'envoi de médias et le nombre de posts voulu.

### YouTube
1. Dans le même projet Google Cloud : activez **YouTube Data API v3**.
2. **Écran de consentement OAuth** : type *Externe*, ajoutez votre adresse comme utilisateur test, puis
   **publiez l'application en production**. En mode « Test », le refresh token expire au bout de 7 jours.
3. **Identifiants → Créer → ID client OAuth → Application de bureau** → téléchargez le JSON sous le nom `client_secret.json`.
4. `python scripts/jeton_youtube.py` → connectez-vous avec le compte qui gère la chaîne.

⚠ Tant que le projet Google n'a pas passé l'**audit YouTube API** (formulaire « YouTube API Services – Audit and Quota
Extension »), les vidéos envoyées par l'API restent **verrouillées en privé**. Demandez l'audit dès le départ.
Quota par défaut : environ 6 envois de vidéo par jour.

---

## 4. Réglages (`config.yaml`)

Fuseau horaire, nombre d'essais, retard maximal toléré, ton de marque et consignes pour l'IA, versions des API.
Le ton est pré-rempli pour Luxcom Conseil : adaptez-le.

## 5. Tester sur votre ordinateur

```bash
pip install -r requirements.txt
```
```bash
python -m agent --source-locale exemple --simulation
```
```bash
python -m pytest
```

`--source-locale` lit un dossier du disque au lieu du Drive ; `--simulation` n'envoie rien ; `--sans-ia` n'appelle pas Claude.

## 6. Dépannage

| Symptôme | Cause probable |
|---|---|
| Description du dossier : « ⚠ Format invalide » | ligne `---` absente, date mal écrite, réseau mal orthographié : le message dit quoi corriger |
| « accès refusé (HTTP 401/403) » | jeton expiré ou permission manquante : relancez le script du réseau concerné |
| `[ÉCHEC]` « date dépassée » | l'agent n'a pas tourné à temps (plus de 24 h de retard) : changez la date, retirez le préfixe |
| Vidéo YouTube privée alors que `public` demandé | projet Google pas encore audité (voir YouTube) |
| Plus aucun passage automatique | GitHub met en pause les tâches planifiées des dépôts **publics** inactifs depuis 60 jours : onglet Actions → réactiver |

Le résumé de chaque passage est visible dans **Actions → (le passage) → Summary**.
