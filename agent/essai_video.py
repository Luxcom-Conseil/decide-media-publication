"""Essai du modèle de Short : fabrique la vidéo d'un article du dernier lot prêt, sans rien publier."""
from __future__ import annotations

import json
import tempfile
from pathlib import Path

from .lots import RE_LOT, LotInvalide, controler_manifeste
from .scenario import rendre_video


def essai_video(drive, sortie: Path, log, numero: int = 1) -> Path | None:
    sortie.mkdir(parents=True, exist_ok=True)
    for dossier in sorted((d for d in drive.lister_dossiers() if RE_LOT.match(d.nom)), key=lambda d: d.nom, reverse=True):
        fichiers = {f.nom: f for f in drive.lister_fichiers(dossier)}
        if "manifest.json" not in fichiers:
            continue
        try:
            articles = controler_manifeste(json.loads(drive.lire_brut(fichiers["manifest.json"]).decode("utf-8-sig")),
                                           dossier.nom)
        except (LotInvalide, ValueError):
            continue
        article = articles[min(numero, len(articles)) - 1]
        log(f"Essai sur le lot {dossier.nom}, article « {article.get('title')} »")
        with tempfile.TemporaryDirectory() as tmp:
            img = article["image_file"]
            image = drive.telecharger_id(img["id"], img.get("name") or f"{article['id']}.png", Path(tmp))
            video = rendre_video(article, image, sortie / f"essai-{article.get('id', 'article')}.mp4")
        log(f"✅ Short fabriqué : {video.name} ({video.stat().st_size // 1024} Ko)")
        return video
    log("❌ Aucun lot prêt dans le Drive pour l'essai.")
    return None
