"""Adaptation du texte à chaque réseau avec Claude.

Si l'IA est désactivée, sans clé, ou en erreur, l'agent publie le texte d'origine (jamais bloquant).
"""
from __future__ import annotations

import json
import os

from .models import Post

LIMITES = {
    "facebook": "2 000 caractères maximum, aéré, 1 à 3 emojis maximum",
    "instagram": "2 200 caractères maximum, accroche dans la première ligne, hashtags regroupés à la fin",
    "linkedin": "3 000 caractères maximum, ton expert, accroche forte sur les 2 premières lignes, paragraphes courts",
    "x": "270 caractères MAXIMUM au total, hashtags et liens compris — c'est une contrainte stricte",
}


class Redacteur:
    def __init__(self, cfg: dict):
        import anthropic

        self.cfg = cfg["ia"]
        self.client = anthropic.Anthropic()

    @staticmethod
    def disponible(cfg: dict) -> bool:
        return bool(cfg["ia"].get("active")) and bool(os.environ.get("ANTHROPIC_API_KEY"))

    def _systeme(self) -> str:
        c = self.cfg
        lignes = [
            "Tu es le community manager" + (f" de {c['marque']}" if c.get("marque") else "") + ".",
            f"Ton à adopter : {c['ton']}",
            "Tu adaptes un texte source à plusieurs réseaux sociaux.",
            "Règles impératives :",
            "- N'invente aucun fait, chiffre, prix, date, promesse, témoignage ou coordonnée absents du texte source.",
            "- Conserve à l'identique les liens, numéros de téléphone, adresses, mentions (@) et noms propres.",
            "- Écris en français, sans fautes, sans formules creuses ni jargon d'IA.",
            "- Respecte la limite de longueur et le nombre de hashtags indiqués pour chaque réseau.",
        ]
        if c.get("consignes"):
            lignes.append(f"Consignes supplémentaires : {c['consignes']}")
        return "\n".join(lignes)

    def adapter(self, post: Post, reseaux: list[str]) -> dict[str, str]:
        """Renvoie {reseau: texte} et, pour YouTube, les clés youtube_titre / youtube_description."""
        hashtags = self.cfg.get("hashtags_max", {})
        props, consignes = {}, []
        for r in reseaux:
            if r == "youtube":
                props["youtube_titre"] = {"type": "string"}
                props["youtube_description"] = {"type": "string"}
                consignes.append("- youtube_titre : 100 caractères maximum, clair et recherché (SEO), sans hashtag.")
                consignes.append("- youtube_description : 2 à 3 paragraphes, mots-clés naturels, liens conservés, "
                                 "3 hashtags maximum à la fin.")
            else:
                props[r] = {"type": "string"}
                consignes.append(f"- {r} : {LIMITES[r]}, {hashtags.get(r, 3)} hashtags maximum.")
        if not props:
            return {}

        medias = []
        if post.images:
            medias.append(f"{len(post.images)} image(s)")
        if post.videos:
            medias.append(f"{len(post.videos)} vidéo(s)")
        message = (
            f"<texte_source>\n{post.texte}\n</texte_source>\n\n"
            f"Médias joints : {', '.join(medias) or 'aucun'}.\n"
            + (f"Titre fourni pour YouTube : {post.titre}\n" if post.titre else "")
            + "Rédige une version pour chacun de ces champs :\n" + "\n".join(consignes)
        )

        reponse = self.client.beta.messages.create(
            model=self.cfg["modele"],
            max_tokens=16000,
            betas=["server-side-fallback-2026-07-01"],
            extra_body={"fallbacks": "default"},  # bascule automatique si le modèle décline la demande
            output_config={
                "effort": self.cfg.get("effort", "medium"),
                "format": {
                    "type": "json_schema",
                    "schema": {"type": "object", "properties": props,
                               "required": list(props), "additionalProperties": False},
                },
            },
            system=self._systeme(),
            messages=[{"role": "user", "content": message}],
        )
        if reponse.stop_reason in ("refusal", "max_tokens"):
            raise RuntimeError(f"réponse IA inutilisable (stop_reason={reponse.stop_reason})")
        texte = next(b.text for b in reponse.content if b.type == "text")
        return {k: v.strip() for k, v in json.loads(texte).items() if isinstance(v, str) and v.strip()}
