"""Constitue la banque de bruitages d'une production à partir de sa charte (config.yaml, bloc <production>.son).

À lancer en LOCAL, une fois, ou quand la charte change : il faut Earshot (github.com/Leonxlnx/earshot), pas installé
sur GitHub Actions. Chaque moment de la charte est rendu en N prises (graines différentes) depuis la banque d'Earshot,
des sons fabriqués par du code, donc sans aucun risque Content ID. Les fichiers vont dans motion/public/<banque>/,
avec banque.json : pour chaque prise, le fichier, la durée et les temps mesurés de l'attaque et du pic, que
agent/sons.py utilise pour caler le son à l'image près. Les musiques, choisies à l'oreille, sont ajoutées par
`--musique FICHIER --credit "…"` (CC0 ou domaine public seulement pour Histoires).

  python scripts/banque_sons.py histoires
  python scripts/banque_sons.py histoires --musique chemin/morceau.mp3 --credit "« Titre » par X (CC0, Freesound)"
"""
import argparse
import json
import re
import shutil
import subprocess
import sys
from pathlib import Path

import yaml

RACINE = Path(__file__).resolve().parent.parent
PUBLIC = RACINE / "motion" / "public"


def ffmpeg() -> str:
    exe = shutil.which("ffmpeg")
    if exe:
        return exe
    import imageio_ffmpeg
    return imageio_ffmpeg.get_ffmpeg_exe()


def rendre(earshot: str, son: str, graine: int, sortie: Path) -> dict:
    brut = sortie.with_suffix(".brut.wav")
    r = subprocess.run([earshot, "sfx", "render", son, "-o", str(brut), "--seed", str(graine)],
                       capture_output=True, text=True, encoding="utf-8", errors="replace")
    ligne = (r.stdout + r.stderr).strip().splitlines()[-1] if (r.stdout + r.stderr).strip() else ""
    if r.returncode != 0 or not brut.exists():
        raise RuntimeError(f"{son} graine {graine} : {ligne}")
    if "checks: clean" not in ligne:
        brut.unlink(missing_ok=True)
        raise ValueError(f"{son} graine {graine} : prise refusée par l'audit d'Earshot ({ligne})")
    nombre = lambda motif: float(re.search(motif, ligne).group(1))
    infos = {"duree": nombre(r": ([\d.]+) s,"), "attaque": nombre(r"onset ([\d.]+) s"), "pic": nombre(r"peak at ([\d.]+) s")}
    # 48 kHz, 16 bits, stéréo : la moitié du poids du rendu 24 bits, inaudible sous la voix
    subprocess.run([ffmpeg(), "-v", "error", "-y", "-i", str(brut), "-ar", "48000", "-ac", "2", "-c:a", "pcm_s16le", str(sortie)],
                   check=True)
    brut.unlink(missing_ok=True)
    return infos


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("production")
    ap.add_argument("--earshot", default=shutil.which("earshot") or str(Path.home() / "Tools" / "bin" / "earshot.exe"))
    ap.add_argument("--musique", type=Path, help="ajoute un morceau choisi à l'oreille (sans re-rendre les bruitages)")
    ap.add_argument("--credit", help="crédit du morceau, recopié tel quel (attribution Openverse)")
    a = ap.parse_args()

    cfg = yaml.safe_load((RACINE / "config.yaml").read_text(encoding="utf-8"))
    charte = (cfg.get(a.production) or {}).get("son")
    if not charte:
        sys.exit(f"pas de bloc {a.production}.son dans config.yaml")
    dossier = PUBLIC / charte["banque"]
    dossier.mkdir(parents=True, exist_ok=True)
    fichier = dossier / "banque.json"
    banque = json.loads(fichier.read_text(encoding="utf-8")) if fichier.exists() else {"moments": {}, "musiques": []}

    if a.musique:
        if not a.credit:
            sys.exit("--credit est obligatoire avec --musique")
        cible = dossier / "musique" / re.sub(r"[^\w.-]+", "_", a.musique.name)
        cible.parent.mkdir(exist_ok=True)
        # MP3 192 kbps, 48 kHz : un morceau de 3 min pèse ~4 Mo
        subprocess.run([ffmpeg(), "-v", "error", "-y", "-i", str(a.musique), "-ar", "48000", "-ac", "2", "-b:a", "192k",
                        str(cible.with_suffix(".mp3"))], check=True)
        src = f"{charte['banque']}/musique/{cible.with_suffix('.mp3').name}"
        banque["musiques"] = [m for m in banque["musiques"] if m["src"] != src] + [{"src": src, "credit": a.credit}]
        fichier.write_text(json.dumps(banque, ensure_ascii=False, indent=1), encoding="utf-8")
        print(f"musique ajoutée : {src} ({len(banque['musiques'])} au total)")
        return

    prises = int(charte.get("prises", 3))
    for moment, regle in charte["moments"].items():
        faites, graine = [], 1
        while len(faites) < prises and graine < prises + 12:   # une prise refusée par l'audit est remplacée
            nom = f"{moment}_{len(faites) + 1}.wav"
            try:
                infos = rendre(a.earshot, regle["son"], graine, dossier / nom)
                faites.append({"src": f"{charte['banque']}/{nom}", "son": regle["son"], "graine": graine, **infos})
            except ValueError as e:
                print(f"  {e}")
            graine += 1
        banque["moments"][moment] = faites
        print(f"{moment:11s} {regle['son']:18s} {len(faites)} prise(s)")
    banque["origine"] = "Earshot (github.com/Leonxlnx/earshot, MIT) : sons fabriqués par du code, aucun enregistrement"
    fichier.write_text(json.dumps(banque, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"→ {fichier}")


if __name__ == "__main__":
    main()
