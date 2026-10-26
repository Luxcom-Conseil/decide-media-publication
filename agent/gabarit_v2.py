"""Prototype du gabarit V2 (composition Remotion DecideShortV2) : pas branché sur la production.

Une phrase courte par scène (≈ 5 à 6 s de voix), sous-titres = texte dit, fin en question, outro court.
"""
from __future__ import annotations

import json
import re
import shutil
import subprocess
import tempfile
from pathlib import Path

from .scenario import MOTION, RUBRIQUES, _date_fr, _icone, _phrases
from .voix import Voix, preparer

PAROLE_MAX = 85  # caractères prononcés par scène (≈ 6 s avec Schedar)
PAROLE_TOTALE = 520  # ≈ 40 s de voix pour le corps de l'article
RE_MONTANT = re.compile(r"\d[\d  .,]*\s?(?:%|FCFA|francs CFA|millions?|milliards?|€|dollars?)", re.I)


def _decouper(phrase: str) -> list[str]:
    """Coupe une phrase trop longue à la virgule (ou au « : ») la plus proche du milieu."""
    if len(preparer(phrase, [])) <= PAROLE_MAX:
        return [phrase]
    coupes = [m.end() for m in re.finditer(r"[,;:]\s", phrase)]
    if not coupes:
        return [phrase]
    k = min(coupes, key=lambda c: abs(c - len(phrase) / 2))
    return _decouper(phrase[:k].rstrip(" ,;:") + ",") + _decouper(phrase[k:].strip())


def _couper_en_scenes(phrase: str) -> list[str]:
    """Morceaux de ≈ 6 s ; un morceau trop court (< 40 caractères) rejoint son voisin."""
    morceaux: list[str] = []
    for m in _decouper(phrase):
        if morceaux and (len(m) < 40 or len(morceaux[-1]) < 40) and len(preparer(morceaux[-1] + " " + m, [])) <= PAROLE_MAX + 25:
            morceaux[-1] += " " + m
        else:
            morceaux.append(m)
    return morceaux


def _chiffre(texte: str) -> str | None:
    montants = [m.group(0).strip() for m in RE_MONTANT.finditer(texte)]
    return montants[-1] if montants else None


RE_EXEMPLE = re.compile(r"\b(exemple|prenons|imaginons|concrètement|supposons|mettons)\b", re.I)
RE_CONSEIL = re.compile(r"^(pour (choisir|éviter|bien|savoir)|avant de|demande[zs]?|demandons|vérifie[zs]?|vérifions|compare[zs]?|"
                        r"comparons|retene[zs]|gardons|exigeons|conservez|lisez|n'hésitez)\b", re.I)


def selection(corps: str) -> list[tuple[str, str]]:
    """Ce que la voix dit, dans l'ordre qui fait comprendre : le fait, l'exemple concret de l'article, le conseil.
    Renvoie [(étiquette, phrase)]. Sans exemple dans l'article : les premières phrases, comme avant."""
    paragraphes = [p for p in re.split(r"\n\s*\n", corps.strip()) if p.strip()]
    fait = [p for p in _phrases(paragraphes[0]) if not p.endswith("?")][:2] if paragraphes else []
    i = next((k for k, p in enumerate(paragraphes) if k and RE_EXEMPLE.search(p)), None)
    exemple: list[str] = []
    if i is not None:
        exemple = _phrases(paragraphes[i])
        if i + 1 < len(paragraphes) and RE_MONTANT.search(paragraphes[i + 1]) and not RE_EXEMPLE.search(paragraphes[i + 1]):
            exemple += _phrases(paragraphes[i + 1])  # l'exemple continue (« Le contrat B… »)
        if exemple and RE_EXEMPLE.search(exemple[0]) and not RE_MONTANT.search(exemple[0]):
            exemple[0] = exemple[0].split(",")[0].rstrip(".") + "."  # « Prenons un exemple fictif, sans… » → « Prenons un exemple fictif. »
        while len(exemple) > 1 and not RE_MONTANT.search(exemple[-1]):
            exemple.pop()  # les réserves techniques après le dernier montant n'aident pas à comprendre
    conseil = next((ph for p in reversed(paragraphes) for ph in _phrases(p) if RE_CONSEIL.search(ph)), None)
    if not exemple:
        reste = [p for p in _phrases(corps) if not p.endswith("?")]
        out, total = [], 0
        for p in reste:
            if total and total + len(preparer(p, [])) > PAROLE_TOTALE:
                break
            total += len(preparer(p, []))
            out.append(("L'ESSENTIEL" if not out else "À COMPRENDRE", p))
        return out
    return ([("LE FAIT", p) for p in fait] + [("EXEMPLE CONCRET", p) for p in exemple]
            + ([("CE QU'IL FAUT FAIRE", conseil)] if conseil else []))


def construire(article: dict, image: str) -> tuple[dict, list[dict]]:
    corps = article.get("body") or article.get("post_text", "")
    phrases = _phrases(corps)
    scenes, dits = [{"type": "visuel"}], [{"cle": "s0", "texte": article.get("title", "")}]
    cas = None  # « CONTRAT A » : rappelé au-dessus des montants tant qu'on parle du même cas
    for n, (etiquette, p) in enumerate(selection(corps)):
        for m in _couper_en_scenes(p):
            c = re.search(r"\b(contrat|offre|option|cas|scénario|formule)\s+([A-D1-4])\b", m, re.I)
            cas = f"{c.group(1)} {c.group(2)}".upper() if c else (cas if etiquette == "EXEMPLE CONCRET" else None)
            scenes.append({"type": "texte", "etiquette": etiquette, "cas": cas, "icone": _icone(m, n), "chiffre": _chiffre(m),
                           "soustitre": _insecables(m)})
            dits.append({"cle": f"s{len(scenes) - 1}", "texte": m})
    question = next((p for p in phrases if p.endswith("?")), "Et toi, qu'en penses-tu ?")
    scenes.append({"type": "question", "texte": question, "soustitre": question})
    dits.append({"cle": f"s{len(scenes) - 1}", "texte": question + " Dis-le en commentaire."})
    scenes.append({"type": "outro", "duree": 3.5})
    dits.append({"cle": f"s{len(scenes) - 1}", "texte": "Décide média. Abonne-toi."})
    editeurs = list(dict.fromkeys((s or {}).get("publisher") for s in article.get("sources") or [] if (s or {}).get("publisher")))
    script = {
        "rubrique": RUBRIQUES.get(article.get("editorial_type") or article.get("content_type"), "ACTUALITÉ"),
        "lieu": article.get("country"), "date": _date_fr(article.get("event_date")),
        "titre": article.get("title", ""), "image": image, "source": ("Source : " + ", ".join(editeurs[:3])) if editeurs else None,
        "scenes": scenes, "musique": "melodie.wav", "volume_musique": 0.10,
    }
    return script, dits


def _insecables(t: str) -> str:
    """« 80 000 FCFA », « 10,99 % » : jamais coupés entre deux blocs de sous-titres."""
    return re.sub(r"(\d)[  ](?=\d{3}\b)|(\d)[  ](?=%|FCFA|€)", lambda x: (x.group(1) or x.group(2)) + " ", t)


def depuis_script(article: dict, image: str, ecrit: dict) -> tuple[dict, list[dict]]:
    """Script pédagogique écrit à la main (ou fourni par le producteur) : {"titre", "scenes": [{type, dit, …}]}."""
    script, _ = construire(article, image)
    scenes, dits = [], []
    for k, sc in enumerate(ecrit["scenes"]):
        sc = dict(sc)
        dit = sc.pop("dit", "")
        if dit and sc["type"] not in ("visuel", "outro"):
            sc["soustitre"] = _insecables(dit)
        scenes.append(sc)
        dits.append({"cle": f"s{k}", "texte": dit})
    script.update({"titre": ecrit.get("titre") or script["titre"], "scenes": scenes})
    return script, dits


def rendre_v2(article: dict, image: Path, sortie: Path, journal=print, ecrit: dict | None = None, essai: bool = False) -> Path:
    """Short au gabarit V2. Sans script fourni : celui de Claude (script_video), sinon le découpage automatique."""
    if ecrit is None:
        from .config import charger_config
        from .script_video import script_pour
        ecrit = script_pour(article, charger_config(MOTION.parent / "config.yaml"), journal)
    dossier = MOTION / "public" / "_lots"
    dossier.mkdir(parents=True, exist_ok=True)
    ident = article.get("id", "article") + "-v2"
    nom_image = f"{ident}{image.suffix.lower()}"
    shutil.copy(image, dossier / nom_image)
    script, dits = (depuis_script if ecrit else construire)(article, f"_lots/{nom_image}", *([ecrit] if ecrit else []))
    try:
        pistes = {p["cle"]: p for p in Voix(journal).narration(dits, dossier, ident, forcer=essai) or []}
    except Exception as e:  # la voix ne bloque jamais la vidéo
        journal(f"⚠️ Voix off indisponible, Short sans voix : {e}")
        pistes = {}
    for k, sc in enumerate(script["scenes"]):
        if f"s{k}" in pistes:
            sc["voix"] = {"src": pistes[f"s{k}"]["src"], "duree": pistes[f"s{k}"]["duree"]}
            if sc["type"] == "outro":
                sc.pop("duree", None)
    with tempfile.TemporaryDirectory() as d:
        props = Path(d) / "props.json"
        props.write_text(json.dumps(script, ensure_ascii=False), encoding="utf-8")
        r = subprocess.run(["npx.cmd" if shutil.which("npx.cmd") else "npx", "remotion", "render", "src/index.ts", "DecideShortV2",
                            str(sortie.resolve()), f"--props={props}", "--codec=h264", "--crf=20", "--log=warn"],
                           cwd=MOTION, capture_output=True, text=True, timeout=1800)
    for f in [dossier / nom_image, *dossier.glob(f"{ident}-*.wav")]:
        f.unlink(missing_ok=True)
    if r.returncode != 0 or not sortie.exists():
        raise RuntimeError(f"rendu Remotion impossible (code {r.returncode}) : {(r.stderr + r.stdout)[-1500:]}")
    return sortie
