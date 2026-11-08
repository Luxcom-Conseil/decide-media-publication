"""Identité sonore d'une production : bruitages calés sur les scènes, musique de la banque, volume final contrôlé.

La charte est le bloc `<production>.son` de config.yaml ; la banque (motion/public/<banque>/banque.json) est constituée
une fois en local par scripts/banque_sons.py. Ici, rien n'est téléchargé ni fabriqué : la production du jour pioche
dans la banque, de façon déterministe (même vidéo → mêmes sons), et le MP4 rendu est ramené au volume de la charte.
Toute erreur laisse la vidéo telle quelle : un son manquant ne doit jamais empêcher une publication.
"""
from __future__ import annotations

import hashlib
import json
import re
import subprocess
from pathlib import Path

MOTION = Path(__file__).resolve().parent.parent / "motion"


def charte(cfg: dict, production: str) -> dict | None:
    return (cfg.get(production) or {}).get("son")


def banque(ch: dict) -> dict | None:
    f = MOTION / "public" / ch["banque"] / "banque.json"
    return json.loads(f.read_text(encoding="utf-8")) if f.exists() else None


def _choix(cle: str, n: int) -> int:
    return int(hashlib.sha1(cle.encode("utf-8")).hexdigest(), 16) % n


def habiller(cfg: dict, production: str, scenes: list[dict], cle: str, format_: str | None = None,
             duree_scene=None, journal=print) -> dict:
    """Ajoute à chaque scène ses bruitages (`sc["sons"]`) et renvoie les réglages de musique pour les props Remotion :
    {"musique": src, "volume_musique": v, "credit_musique": texte} (vide si la production n'a pas de charte).
    `duree_scene(sc)` donne la durée d'une scène en secondes (pour l'écart minimal entre deux transitions)."""
    ch = charte(cfg, production)
    b = banque(ch) if ch else None
    if not b:
        return {}
    regles = (ch.get("formats") or {}).get(format_ or "", {})
    sans, gain_format = set(regles.get("sans", [])), float(regles.get("gain_db", 0))
    ecart = float(ch.get("transition_ecart_s", 6))
    moments = ch.get("moments", {})
    t, derniere_transition, image_precedente, poses = 0.0, -1e9, None, 0
    for k, sc in enumerate(scenes):
        sc.pop("sons", None)
        role = sc.get("type")
        image = (sc.get("image") or {}).get("src")
        if role not in moments and role == "recit" and image and image != image_precedente and k > 0 \
                and t - derniere_transition >= ecart:
            role = "transition"
        if role in moments and role not in sans and b["moments"].get(role):
            prises = b["moments"][role]
            p = prises[_choix(f"{cle}/{k}", len(prises))]
            r = moments[role]
            avance = p["pic"] if r.get("caler") == "pic" else p["attaque"]
            sc["sons"] = [{"src": p["src"], "a": float(r.get("a", 0)), "avance": avance,
                           "gain": round(10 ** ((float(r.get("gain_db", 0)) + gain_format) / 20), 4)}]
            poses += 1
            if role == "transition":
                derniere_transition = t
        image_precedente = image or image_precedente
        t += duree_scene(sc) if duree_scene else float((sc.get("voix") or {}).get("duree") or sc.get("duree") or 3.0)
    reglages = {}
    if b.get("musiques"):
        m = b["musiques"][_choix(cle, len(b["musiques"]))]
        reglages = {"musique": m["src"], "volume_musique": float(ch.get("musique_volume", 0.10)), "credit_musique": m["credit"]}
    journal(f"    🔊 {poses} bruitage(s) de la charte {production}" + (f", musique {Path(reglages['musique']).name}" if reglages else ""))
    return reglages


# --------------------------------------------------------------------------- volume final

def _ffmpeg() -> str:
    import imageio_ffmpeg
    return imageio_ffmpeg.get_ffmpeg_exe()


def mesurer(fichier: Path) -> dict:
    """Volume intégré (LUFS) et pic vrai (dBTP) de la piste audio, mesurés par ffmpeg (ebur128)."""
    r = subprocess.run([_ffmpeg(), "-hide_banner", "-nostats", "-i", str(fichier), "-vn", "-af", "ebur128=peak=true",
                        "-f", "null", "-"], capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=600)
    fin = r.stderr[r.stderr.rfind("Summary:"):]
    i = re.search(r"I:\s+(-?[\d.]+) LUFS", fin)
    p = re.search(r"Peak:\s+(-?[\d.]+) dBFS", fin)
    if not i or not p:
        raise RuntimeError("mesure du volume impossible")
    return {"lufs": float(i.group(1)), "pic": float(p.group(1))}


def niveler(cfg: dict, production: str, mp4: Path, journal=print) -> dict | None:
    """Ramène le MP4 au volume de la charte (loudnorm en deux passes, image copiée telle quelle), puis le re-mesure.
    Renvoie la mesure finale, ou None si la production n'a pas de cible ou si le nivellement échoue."""
    ch = charte(cfg, production) or {}
    cible = ch.get("volume_final_lufs")
    if cible is None:
        return None
    try:
        avant = mesurer(mp4)
        if abs(avant["lufs"] - cible) <= 0.7 and avant["pic"] <= -1.5:
            journal(f"    🎚️ volume {avant['lufs']:.1f} LUFS, pic {avant['pic']:.1f} dBTP : déjà dans la charte")
            return avant
        filtre = f"loudnorm=I={cible}:TP=-1.5:LRA=11"
        r = subprocess.run([_ffmpeg(), "-hide_banner", "-nostats", "-i", str(mp4), "-vn", "-af", filtre + ":print_format=json",
                            "-f", "null", "-"], capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=600)
        m = json.loads(r.stderr[r.stderr.rfind("{"):r.stderr.rfind("}") + 1])
        filtre += (f":measured_I={m['input_i']}:measured_TP={m['input_tp']}:measured_LRA={m['input_lra']}"
                   f":measured_thresh={m['input_thresh']}:offset={m['target_offset']}:linear=true")
        tmp = mp4.with_name(mp4.stem + ".niveau.mp4")
        subprocess.run([_ffmpeg(), "-v", "error", "-y", "-i", str(mp4), "-map", "0", "-c:v", "copy", "-af", filtre,
                        "-ar", "48000", "-c:a", "aac", "-b:a", "192k", "-movflags", "+faststart", str(tmp)],
                       check=True, capture_output=True, timeout=600)
        apres = mesurer(tmp)
        if abs(apres["lufs"] - cible) > 1.0 or apres["pic"] > -1.0:
            tmp.unlink(missing_ok=True)
            journal(f"    ⚠️ nivellement hors charte ({apres['lufs']:.1f} LUFS, {apres['pic']:.1f} dBTP) : vidéo gardée telle quelle")
            return avant
        tmp.replace(mp4)
        journal(f"    🎚️ volume {avant['lufs']:.1f} → {apres['lufs']:.1f} LUFS, pic {apres['pic']:.1f} dBTP")
        return apres
    except Exception as e:
        journal(f"    ⚠️ volume non contrôlé : {e}")
        return None
