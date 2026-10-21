"""Fabrication d'un Short YouTube à partir d'un article de lot : visuel + voix off du texte.

- Format vertical 1080x1920 : le visuel carré au centre, avec un léger zoom, sur un fond flou du même visuel.
- Voix off : synthèse vocale Windows (voix française « Hortense »), gratuite et locale.
- Montage : ffmpeg (fourni par le paquet imageio-ffmpeg).
"""
from __future__ import annotations

import re
import subprocess
import tempfile
import wave
from pathlib import Path

VOIX = "Microsoft Hortense Desktop"
FPS = 30


def texte_a_lire(titre: str, corps: str) -> str:
    """Texte prononcé : titre puis corps, sans hashtags ni liens ni emojis."""
    t = f"{titre}.\n\n{corps}"
    t = re.sub(r"https?://\S+", "", t)
    t = re.sub(r"#\w+", "", t)
    t = re.sub(r"[\U0001F300-\U0001FAFF☀-➿]", "", t)
    t = t.replace("—", ",").replace("–", ",")
    return re.sub(r"[ \t]+", " ", t).strip()


def synthese_vocale(texte: str, sortie: Path, voix: str = VOIX, vitesse: int = 0) -> Path:
    """Écrit un WAV avec la synthèse vocale de Windows (System.Speech)."""
    with tempfile.TemporaryDirectory() as d:
        fichier_texte = Path(d) / "texte.txt"
        fichier_texte.write_text(texte, encoding="utf-8")
        script = (
            "Add-Type -AssemblyName System.Speech;"
            "$s = New-Object System.Speech.Synthesis.SpeechSynthesizer;"
            f"$s.SelectVoice('{voix}'); $s.Rate = {int(vitesse)};"
            f"$s.SetOutputToWaveFile('{sortie}');"
            f"$s.Speak([IO.File]::ReadAllText('{fichier_texte}', [Text.Encoding]::UTF8));"
            "$s.Dispose()"
        )
        subprocess.run(["powershell", "-NoProfile", "-NonInteractive", "-Command", script],
                       check=True, capture_output=True, timeout=300)
    if not sortie.exists() or sortie.stat().st_size < 1000:
        raise RuntimeError("la synthèse vocale n'a produit aucun son")
    return sortie


def duree_wav(chemin: Path) -> float:
    with wave.open(str(chemin), "rb") as w:
        return w.getnframes() / float(w.getframerate())


def fabriquer_short(image: Path, titre: str, corps: str, sortie: Path, voix: str = VOIX) -> Path:
    import imageio_ffmpeg

    ffmpeg = imageio_ffmpeg.get_ffmpeg_exe()
    with tempfile.TemporaryDirectory() as d:
        wav = synthese_vocale(texte_a_lire(titre, corps), Path(d) / "voix.wav", voix)
        duree = min(duree_wav(wav) + 1.5, 175.0)  # Shorts : 3 minutes maximum
        images = int(duree * FPS)
        filtre = (
            # fond : visuel agrandi, recadré en vertical, flouté et assombri
            "[0:v]scale=1920:1920,crop=1080:1920,boxblur=25:2,eq=brightness=-0.18,setsar=1[fond];"
            # premier plan : visuel carré avec zoom lent
            # zoom limité à 3 % pour ne jamais couper le logo ni le titre incrustés dans le visuel
            f"[1:v]scale=2160:2160,zoompan=z='1+0.03*on/{images}':x='iw/2-(iw/zoom/2)':"
            f"y='ih/2-(ih/zoom/2)':d={images}:s=1080x1080:fps={FPS},setsar=1[avant];"
            "[fond][avant]overlay=0:(H-h)/2:shortest=1,format=yuv420p[v]"
        )
        commande = [
            ffmpeg, "-y", "-loglevel", "error",
            "-loop", "1", "-framerate", str(FPS), "-t", f"{duree:.2f}", "-i", str(image),
            "-i", str(image),
            "-i", str(wav),
            "-filter_complex", filtre, "-map", "[v]", "-map", "2:a",
            "-c:v", "libx264", "-preset", "medium", "-crf", "21", "-r", str(FPS),
            "-c:a", "aac", "-b:a", "160k", "-t", f"{duree:.2f}", "-movflags", "+faststart",
            str(sortie),
        ]
        r = subprocess.run(commande, capture_output=True, text=True, timeout=600)
        if r.returncode != 0:
            raise RuntimeError(f"montage vidéo impossible : {r.stderr[-500:]}")
    return sortie
