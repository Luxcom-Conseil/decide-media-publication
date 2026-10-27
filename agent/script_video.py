"""Script pédagogique d'un Short (gabarit V2), écrit par une IA à partir de l'article du lot : Gemini (offre gratuite
de Google, clé GEMINI_API_KEY) par défaut, ou Claude (clé ANTHROPIC_API_KEY) si config video.ia = claude.

Le script est contrôlé avant usage : aucun chiffre absent de l'article, longueurs tenues, dessins connus.
Il est conservé dans etat/scripts/<id>.json : même script pour tous les réseaux et tous les passages, et trace de
ce qui a été dit. Sans clé, en erreur ou au contrôle raté : None, et le Short est construit sans IA (gabarit_v2).
"""
from __future__ import annotations

import json
import os
import re
from pathlib import Path

RACINE = Path(__file__).resolve().parent.parent
SCRIPTS = RACINE / "etat" / "scripts"
_IA_HORS_SERVICE = False  # passe à True pour la fin du passage si Gemini est saturé sur tous ses modèles

ILLUSTRATIONS = {
    "banque": "bâtiment de banque d'où sortent des pièces : prêt, crédit, épargne, banque, argent public",
    "rembourser": "deux barres « prêté » et « rendu » (plus haute) : rendre plus que ce qu'on a reçu, intérêts d'un crédit",
    "pays": "un cercle et six repères : une région ou plusieurs pays ; texte = nom de la région (« CEMAC », « UEMOA »…)",
    "carte": "une carte de l'Afrique qui zoome et des repères qui tombent sur les lieux cités : où ça se passe (ville, pays, "
             "trajet) ; texte = 1 à 4 lieux nommés dans l'article, séparés par « | » (« Yaoundé | Douala », « Togo »)",
    "pourcent": "deux barres avant / après et une flèche : un chiffre qui monte ou baisse ; sens (baisse|hausse), avant, apres",
    "personnage": "un des personnages récurrents de DECIDE, avec son expression et son geste : chaque fois que la scène parle "
                  "d'une personne ou de ce que vit le spectateur. personnage (commercante|artisan|salarie|etudiante), "
                  "expression (contente|inquiete|surprise|pensive), geste (salue|montre|reflechit|tient_billet|"
                  "tient_document|repos), texte = qui c'est (« Commerçante ») ou null",
    "couturiere": "la commerçante à sa machine à coudre : seulement si l'article parle de couture",
    "contrats": "deux contrats A et B et un « ? » : seulement pour choisir entre deux offres ou deux contrats",
    "calendrier": "un calendrier. Avec montant (« 90 000 ») : paiements mensuels qui s'empilent. Sans montant : une date ou "
                  "une durée en texte (« 28 mai 2027 », « 15 mois »)",
    "pile": "une pile de billets qui monte ; montant = somme en FCFA (« 1 080 000 »)",
    "frais": "un ticket « FRAIS » qui tombe ; montant (« + 40 000 ») : frais, taxe, coût en plus",
    "balance": "une balance qui penche vers B ; a et b = les deux choses comparées (b la plus lourde)",
    "loupe": "une loupe sur un document : vérifier, lire les détails, regarder le total",
    "liste": "une liste de trois points cochés ; texte = « Titre : point 1 | point 2 | point 3 » (mots courts)",
    "petrole": "un derrick et une pompe à pétrole : pétrole, gaz, mines, exploration",
    "solaire": "un soleil et des panneaux solaires avec un éclair : énergie solaire, centrale électrique",
    "chantier": "une grue et un bâtiment qui monte : travaux, construction, route, infrastructure",
    "maison": "une maison dont la lumière s'allume : électricité à la maison, logement, ménage ; texte facultatif",
    "marche": "un étal de marché avec panier et étiquette de prix ; montant = le prix : prix, consommation, commerce",
    "photo": "la photo de l'article : quand aucun autre dessin ne montre vraiment l'idée",
}

_PARAM = {"anyOf": [{"type": "string"}, {"type": "null"}]}


def _choix(*valeurs: str) -> dict:
    return {"anyOf": [{"type": "string", "enum": list(valeurs)}, {"type": "null"}]}
SCHEMA = {
    "type": "object",
    "properties": {
        "titre": {"type": "string"},
        "scenes": {"type": "array", "items": {
            "type": "object",
            "properties": {
                "type": {"type": "string", "enum": ["visuel", "explication"]},
                "etiquette": {"type": "string"},
                "illustration": {"anyOf": [{"type": "null"}, {
                    "type": "object",
                    "properties": {"type": {"type": "string", "enum": list(ILLUSTRATIONS)},
                                   "sens": _choix("baisse", "hausse"),
                                   "avant": _PARAM, "apres": _PARAM, "montant": _PARAM, "a": _PARAM, "b": _PARAM, "texte": _PARAM,
                                   "personnage": _choix("commercante", "artisan", "salarie", "etudiante"),
                                   "expression": _choix("contente", "inquiete", "surprise", "pensive"),
                                   "geste": _choix("salue", "montre", "reflechit", "tient_billet", "tient_document", "repos")},
                    "required": ["type", "sens", "avant", "apres", "montant", "a", "b", "texte", "personnage", "expression", "geste"],
                    "additionalProperties": False}]},
                "ecran": {"type": "string"},
                "dit": {"type": "string"},
            },
            "required": ["type", "etiquette", "illustration", "ecran", "dit"],
            "additionalProperties": False,
        }},
        "question": {"type": "string"},
    },
    "required": ["titre", "scenes", "question"],
    "additionalProperties": False,
}

SYSTEME = """Tu écris le script d'une courte vidéo verticale (Short) de DECIDE média, qui explique l'actualité économique \
à des gens ordinaires d'Afrique centrale : commerçants, artisans, parents, étudiants. Ils n'ont pas de culture financière.

But : qu'une couturière ou un vendeur du marché comprenne entièrement ce qui est dit, et sache quoi en faire.

Déroulé (une idée par scène) :
1. Scène « visuel » : une accroche qui donne envie de rester (la photo de l'article s'affiche).
2. Explique d'abord le mot clé, comme à un ami (« Un crédit, c'est de l'argent que la banque te prête. »).
3. Le fait, avec les chiffres de l'article.
4. Un cas concret : reprends l'exemple de l'article s'il y en a un, étape par étape, avec ses chiffres. S'il n'y en a pas, \
montre ce que le fait change pour une personne ordinaire, sans ajouter de chiffre.
5. La leçon, en une phrase.
6. Ce qu'il faut faire, concrètement.
Puis une question au spectateur (champ « question »), qui l'invite à donner son avis ou son expérience.

Langue : français simple et correct, phrases courtes, tutoiement, mots de tous les jours. Pas de jargon ; si un sigle \
est utile (CEMAC, BEAC), dis une fois ce qu'il désigne. Pas de ton publicitaire, pas d'exclamations en série.

Exactitude (impératif) :
- N'invente aucun fait. Chaque chiffre que tu écris doit figurer dans l'article, recopié à l'identique \
(« 10,99 % », « 90 000 FCFA »). Seul « 12 mois » peut s'écrire en chiffres si l'article dit « douze ».
- Introduis le cas concret simplement par « Prenons un exemple. » N'écris jamais qu'il est « fictif » ou « inventé », \
ni dans la voix, ni à l'écran, ni dans l'étiquette (étiquette « EXEMPLE »).
- Ne nomme aucune personne qui n'est pas nommée dans l'article ; ne donne pas de prénom au personnage de l'exemple.
- Ne donne pas de conseil que l'article ne donne pas.

Format de chaque scène :
- « dit » : ce que dit la voix, 110 caractères au plus (environ 6 secondes).
- « ecran » : l'idée clé affichée en grand, 32 caractères au plus, chiffres compris (vide pour la scène « visuel »).
- « etiquette » : 1 à 3 mots en majuscules (C'EST QUOI ?, LE FAIT, EXEMPLE, CONTRAT A, RÉSULTAT, LA LEÇON, \
CE QU'IL FAUT FAIRE…). Vide pour la scène « visuel ».
- « illustration » : le dessin animé qui montre l'idée de la scène, choisi dans la liste ; null pour la scène \
« visuel ». Le dessin doit correspondre au sens de la scène : pas de banque pour parler de pétrole, pas de contrats A et B \
s'il n'y a pas deux offres à comparer. Si aucun dessin ne convient, choisis « photo ». Varie les dessins d'une scène à \
l'autre. Remplis seulement les paramètres utiles au dessin choisi, les autres à null.
- Personnages récurrents : utilise-les dès qu'une scène parle d'une personne, du spectateur ou de ce qu'il ressent \
(au moins deux scènes par vidéo). Garde le même personnage pour toute l'histoire d'un exemple. L'expression suit le sens \
de la phrase : contente (bonne nouvelle, solution), inquiete (coût, risque, piège), surprise (chiffre inattendu), \
pensive (choix, question). Le geste aussi : tient_billet pour une somme, tient_document pour un contrat ou un papier, \
reflechit pour hésiter, montre pour attirer l'attention, salue pour l'accueil. Qui est qui : commercante = une femme \
(commerçante, vendeuse, couturière, ouvrière, mère), artisan = un homme (artisan, ouvrier, agriculteur, soudeur), \
salarie = un homme en veste (salarié, employé, fonctionnaire, père, chef d'entreprise), etudiante = une jeune femme \
(étudiante, élève, jeune). Le « texte » sous le personnage doit correspondre à ce dessin.
Entre 10 et 16 scènes en tout. « titre » : le titre affiché en haut pendant toute la vidéo, 45 caractères au plus.

Dessins disponibles :
""" + "\n".join(f"- {k} : {v}" for k, v in ILLUSTRATIONS.items())


def _nombres(texte: str) -> set[str]:
    """« 1 080 000 », « 10,99 » → {"1080000", "10.99"} (espaces et séparateurs de milliers retirés)."""
    t = re.sub(r"(?<=\d)[   .](?=\d{3}\b)", "", texte)
    nombres = {n.replace(",", ".") for n in re.findall(r"\d+(?:,\d+)?", t)}
    # « 1 million », « 25,289 milliards » valent aussi 1000000, 25289000000
    for n, unite in re.findall(r"(\d+(?:,\d+)?)\s*(million|milliard)", t, re.I):
        valeur = float(n.replace(",", ".")) * (1e6 if unite.lower() == "million" else 1e9)
        nombres.add(str(int(valeur)) if valeur == int(valeur) else str(valeur))
    return nombres


def controler(script: dict, article: dict) -> list[str]:
    """Problèmes qui interdisent d'utiliser le script (liste vide = bon pour la vidéo)."""
    source = " ".join(str(article.get(k) or "") for k in ("title", "body", "post_text", "value_added"))
    from num2words import num2words
    en_lettres = {str(n) for n in range(1, 101) if re.search(rf"\b{num2words(n, lang='fr')}\b", source, re.I)}  # « quinze mois »
    permis = _nombres(source) | {str(n) for n in range(0, 13)} | en_lettres  # « 0 frais », « 12 mois »
    problemes = []
    if not 8 <= len(script.get("scenes") or []) <= 18:
        problemes.append(f"{len(script.get('scenes') or [])} scènes (8 à 18 attendues)")
    textes = [script.get("titre", ""), script.get("question", "")]
    for k, sc in enumerate(script.get("scenes") or []):
        textes += [sc.get("dit", ""), sc.get("ecran", "")]
        il = sc.get("illustration") or {}
        textes += [str(v) for c, v in il.items() if c != "type" and v]
        if len(sc.get("dit", "")) > 140:
            problemes.append(f"scène {k + 1} : voix trop longue ({len(sc['dit'])} caractères)")
        if len(sc.get("ecran", "")) > 45:
            problemes.append(f"scène {k + 1} : texte écran trop long ({len(sc['ecran'])} caractères)")
        if sc.get("type") == "explication" and not il:
            problemes.append(f"scène {k + 1} : explication sans dessin")
        if il.get("type") == "liste" and len([p for p in str(il.get("texte") or "").split("|") if p.strip()]) < 2:
            problemes.append(f"scène {k + 1} : liste sans ses points (texte « Titre : point 1 | point 2 | point 3 »)")
    if re.search(r"\b(fictif|fictive|invent[ée]e?s?)\b", " ".join(textes + [sc.get("etiquette", "") for sc in script.get("scenes") or []]), re.I):
        problemes.append("le mot « fictif » ou « inventé » apparaît : dire simplement « Prenons un exemple. »")
    if re.search(r"\b(vous|vos|votre)\b", " ".join(textes), re.I):
        problemes.append("vouvoiement : tutoie le spectateur (tu, ton, ta, tes)")
    inventes = sorted(_nombres(" ".join(textes)) - permis)
    if inventes:
        problemes.append("chiffres absents de l'article : " + ", ".join(inventes))
    return problemes


def _message(article: dict, remarques: list[str]) -> str:
    corps = article.get("body") or article.get("post_text", "")
    message = (f"<article>\nTitre : {article.get('title', '')}\nPays : {article.get('country') or ''}\n\n{corps}\n</article>\n\n"
               "Écris le script de la vidéo pour cet article.")
    if remarques:
        message += "\n\nTa version précédente a été refusée pour ces raisons, corrige-les :\n- " + "\n- ".join(remarques)
    return message


def _demander_gemini(article: dict, cfg: dict, remarques: list[str]) -> dict:
    """Gemini (offre gratuite de Google AI Studio), clé GEMINI_API_KEY, réflexion réduite (réponse en quelques secondes).
    L'offre gratuite passe après les clients payants : surchargé (503), limité (429) ou trop lent, on réessaie après
    une pause, puis on passe au modèle suivant de la liste."""
    import time

    import requests

    v = cfg.get("video") or {}
    modeles = v.get("modeles_gemini") or ["gemini-3.6-flash", "gemini-3.5-flash", "gemini-3.5-flash-lite", "gemini-flash-latest"]
    erreur = "aucun modèle Gemini configuré"
    for modele in modeles:
        for pause in (0, 20):
            time.sleep(pause)
            try:
                r = requests.post(f"https://generativelanguage.googleapis.com/v1beta/models/{modele}:generateContent",
                                  timeout=120, headers={"x-goog-api-key": os.environ["GEMINI_API_KEY"]},
                                  json={"systemInstruction": {"parts": [{"text": SYSTEME}]},
                                        "contents": [{"role": "user", "parts": [{"text": _message(article, remarques)}]}],
                                        "generationConfig": {"responseMimeType": "application/json", "responseJsonSchema": SCHEMA,
                                                             "thinkingConfig": {"thinkingLevel": "low"}}})
            except requests.RequestException as e:
                erreur = f"{modele} : {type(e).__name__}"
                continue
            if r.status_code == 200:
                break
            erreur = f"{modele} : HTTP {r.status_code} {r.text[:200]}"
            if r.status_code not in (429, 500, 503):
                break
        else:
            continue
        if r.status_code == 200:
            break
    else:
        global _IA_HORS_SERVICE
        _IA_HORS_SERVICE = True  # tous les modèles saturés : les articles suivants de ce passage n'attendent pas
        raise RuntimeError(f"Gemini indisponible ({erreur})")
    candidat = (r.json().get("candidates") or [{}])[0]
    if candidat.get("finishReason") not in (None, "STOP"):
        raise RuntimeError(f"réponse Gemini inutilisable (finishReason={candidat.get('finishReason')})")
    return json.loads("".join(p.get("text", "") for p in candidat["content"]["parts"]))


def _demander(article: dict, cfg: dict, remarques: list[str]) -> dict:
    if (cfg.get("video") or {}).get("ia", "gemini") == "gemini":
        return _demander_gemini(article, cfg, remarques)
    import anthropic

    reponse = anthropic.Anthropic().beta.messages.create(
        model=cfg["ia"]["modele"],
        max_tokens=16000,
        betas=["server-side-fallback-2026-07-01"],
        extra_body={"fallbacks": "default"},  # bascule automatique si le modèle décline la demande
        output_config={"effort": cfg["ia"].get("effort", "medium"), "format": {"type": "json_schema", "schema": SCHEMA}},
        system=SYSTEME,
        messages=[{"role": "user", "content": _message(article, remarques)}],
    )
    if reponse.stop_reason in ("refusal", "max_tokens"):
        raise RuntimeError(f"réponse IA inutilisable (stop_reason={reponse.stop_reason})")
    return json.loads(next(b.text for b in reponse.content if b.type == "text"))


def _en_scenes(ecrit: dict) -> dict:
    """Script de Claude → format de gabarit_v2.depuis_script (fin en question + outro)."""
    scenes = []
    for sc in ecrit["scenes"]:
        s = {"type": sc["type"], "dit": sc["dit"]}
        if sc["type"] == "explication":
            il = {k: v for k, v in (sc.get("illustration") or {}).items() if v is not None}
            s.update({"etiquette": sc.get("etiquette") or None, "illustration": il, "ecran": sc.get("ecran") or None})
        scenes.append(s)
    q = ecrit["question"].strip()
    scenes += [{"type": "question", "texte": q, "dit": f"{q} Dis-le en commentaire."},
               {"type": "outro", "dit": "Décide média. Abonne-toi."}]
    return {"titre": ecrit["titre"], "scenes": scenes}


def script_pour(article: dict, cfg: dict, journal=print) -> dict | None:
    """Script prêt pour le gabarit V2, ou None (pas de clé, erreur, ou contrôle raté deux fois)."""
    fichier = SCRIPTS / f"{article.get('id', 'article')}.json"
    if fichier.exists():
        return json.loads(fichier.read_text(encoding="utf-8"))
    ia = (cfg.get("video") or {}).get("ia", "gemini")
    if _IA_HORS_SERVICE or not os.environ.get("GEMINI_API_KEY" if ia == "gemini" else "ANTHROPIC_API_KEY"):
        return None
    remarques: list[str] = []
    for _ in range(2):  # une seconde chance, avec les remarques du contrôle
        try:
            ecrit = _demander(article, cfg, remarques)
        except Exception as e:  # l'IA ne bloque jamais la publication
            journal(f"⚠️ Script vidéo IA indisponible ({type(e).__name__} : {str(e)[:200]}) : Short construit sans IA")
            return None
        remarques = controler(ecrit, article)
        if not remarques:
            script = _en_scenes(ecrit)
            SCRIPTS.mkdir(parents=True, exist_ok=True)
            modele = "gemini" if ia == "gemini" else cfg["ia"]["modele"]
            fichier.write_text(json.dumps({**script, "_article": article.get("id"), "_modele": modele},
                                          ensure_ascii=False, indent=2), encoding="utf-8")
            return script
    journal("⚠️ Script vidéo IA refusé au contrôle (" + " ; ".join(remarques)[:300] + ") : Short construit sans IA")
    return None
