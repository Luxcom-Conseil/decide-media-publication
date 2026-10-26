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

ILLUSTRATIONS = {
    "banque": "bâtiment de banque d'où sortent des pièces (prêt, crédit, épargne, banque)",
    "rembourser": "deux barres : « prêté » et « rendu » plus haute (rendre plus que reçu, intérêts, prix du crédit)",
    "pays": "un cercle CEMAC et six repères (moyenne régionale, plusieurs pays)",
    "pourcent": "deux barres avant / après avec une flèche ; paramètres sens (baisse|hausse), avant, apres (ex. « 11,53 % »)",
    "personne": "une personne (habitant, commerçant, artisan, parent, salarié…) ; paramètre texte = qui (ex. « Commerçante »)",
    "couturiere": "une couturière à sa machine à coudre (seulement si l'article parle d'une couturière ou d'un atelier de couture)",
    "contrats": "deux contrats A et B avec un point d'interrogation (choisir entre deux offres)",
    "calendrier": "un calendrier qui compte les mois et des pièces qui s'empilent ; paramètre montant (ex. « 90 000 ») = paiement par mois",
    "pile": "une pile de billets qui monte ; paramètre montant (ex. « 1 080 000 ») = total en FCFA",
    "frais": "un ticket « FRAIS » qui tombe ; paramètre montant (ex. « + 40 000 »)",
    "balance": "une balance qui penche vers B ; paramètres a et b = montants comparés (b le plus lourd)",
    "loupe": "une loupe qui s'arrête sur la ligne TOTAL d'un document (bien vérifier, regarder le total)",
    "liste": "un tableau des paiements avec trois cases cochées (ce qu'il faut demander ou vérifier)",
}

_PARAM = {"anyOf": [{"type": "string"}, {"type": "null"}]}
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
                                   "sens": {"anyOf": [{"type": "string", "enum": ["baisse", "hausse"]}, {"type": "null"}]},
                                   "avant": _PARAM, "apres": _PARAM, "montant": _PARAM, "a": _PARAM, "b": _PARAM, "texte": _PARAM},
                    "required": ["type", "sens", "avant", "apres", "montant", "a", "b", "texte"],
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
- Si l'exemple de l'article est inventé ou fictif, dis-le (« exemple inventé »).
- Ne nomme aucune personne qui n'est pas nommée dans l'article ; ne donne pas de prénom au personnage de l'exemple.
- Ne donne pas de conseil que l'article ne donne pas.

Format de chaque scène :
- « dit » : ce que dit la voix, 110 caractères au plus (environ 6 secondes).
- « ecran » : l'idée clé affichée en grand, 32 caractères au plus, chiffres compris (vide pour la scène « visuel »).
- « etiquette » : 1 à 3 mots en majuscules (C'EST QUOI ?, LE FAIT, EXEMPLE, CONTRAT A, RÉSULTAT, LA LEÇON, \
CE QU'IL FAUT FAIRE…). Vide pour la scène « visuel ».
- « illustration » : le dessin animé qui montre l'idée, choisi dans la liste ; null pour la scène « visuel ». \
Remplis seulement les paramètres utiles au dessin choisi, les autres à null.
Entre 10 et 16 scènes en tout. « titre » : le titre affiché en haut pendant toute la vidéo, 45 caractères au plus.

Dessins disponibles :
""" + "\n".join(f"- {k} : {v}" for k, v in ILLUSTRATIONS.items())


def _nombres(texte: str) -> set[str]:
    """« 1 080 000 », « 10,99 » → {"1080000", "10.99"} (espaces et séparateurs de milliers retirés)."""
    t = re.sub(r"(?<=\d)[   .](?=\d{3}\b)", "", texte)
    return {n.replace(",", ".") for n in re.findall(r"\d+(?:,\d+)?", t)}


def controler(script: dict, article: dict) -> list[str]:
    """Problèmes qui interdisent d'utiliser le script (liste vide = bon pour la vidéo)."""
    source = " ".join(str(article.get(k) or "") for k in ("title", "body", "post_text", "value_added"))
    permis = _nombres(source) | {str(n) for n in range(1, 13)}
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
    """Gemini (offre gratuite de Google AI Studio), clé GEMINI_API_KEY."""
    import requests

    modele = (cfg.get("video") or {}).get("modele_gemini", "gemini-3.8-flash")
    r = requests.post(f"https://generativelanguage.googleapis.com/v1beta/models/{modele}:generateContent", timeout=180,
                      headers={"x-goog-api-key": os.environ["GEMINI_API_KEY"]},
                      json={"systemInstruction": {"parts": [{"text": SYSTEME}]},
                            "contents": [{"role": "user", "parts": [{"text": _message(article, remarques)}]}],
                            "generationConfig": {"responseMimeType": "application/json", "responseJsonSchema": SCHEMA}})
    if r.status_code != 200:
        raise RuntimeError(f"Gemini {r.status_code} : {r.text[:300]}")
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
    if not os.environ.get("GEMINI_API_KEY" if ia == "gemini" else "ANTHROPIC_API_KEY"):
        return None
    remarques: list[str] = []
    for _ in range(2):  # une seconde chance, avec les remarques du contrôle
        try:
            ecrit = _demander(article, cfg, remarques)
        except Exception as e:  # l'IA ne bloque jamais la publication
            journal(f"⚠️ Script vidéo IA indisponible ({type(e).__name__}) : Short construit sans IA")
            return None
        remarques = controler(ecrit, article)
        if not remarques:
            script = _en_scenes(ecrit)
            SCRIPTS.mkdir(parents=True, exist_ok=True)
            modele = (cfg.get("video") or {}).get("modele_gemini", "gemini-3.8-flash") if ia == "gemini" else cfg["ia"]["modele"]
            fichier.write_text(json.dumps({**script, "_article": article.get("id"), "_modele": modele},
                                          ensure_ascii=False, indent=2), encoding="utf-8")
            return script
    journal("⚠️ Script vidéo IA refusé au contrôle (" + " ; ".join(remarques)[:300] + ") : Short construit sans IA")
    return None
