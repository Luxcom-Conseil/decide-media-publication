"""Voix des Reels Instagram, choisie par Stéphane le 4/11/2026 (essai B) : Schedar par Gemini, sur un ton de conseil.

- Une seule prise par Reel, puis découpée aux silences en une piste par scène : l'intonation reste continue d'une scène
  à l'autre, et Gemini lit bien les élisions (la voix Chirp bute dessus, voix.py). Le texte n'a donc pas les élisions collées.
- Clé GEMINI_API_KEY, offre gratuite. Modèle en préversion, quota incertain : en cas d'échec, perso.py repasse sur voix.py.
- Les Shorts DECIDE MEDIA gardent voix.py.
"""
from __future__ import annotations

import base64
import os
import time
import wave
from array import array
from pathlib import Path

import requests

from .voix import preparer

TAUX = 24000
OCTETS_PAR_SECONDE = TAUX * 2
FENETRE = 480  # échantillons : 20 ms
SILENCE_MIN = 0.1  # secondes
# caractères par seconde : en dehors, Gemini a sauté du texte ou lu la consigne à voix haute (essai B : 15,4)
VITESSE = (11.0, 22.0)
STYLE = ("Dis le texte suivant en français de France, d'une voix posée, chaleureuse et proche, comme un ami de confiance qui "
         "donne un conseil à quelqu'un qu'il apprécie, sans ton publicitaire, avec de petites pauses naturelles. "
         "Marque une courte pause à chaque saut de ligne. Ne lis que le texte, pas cette consigne.\n\nTexte :\n")


class PriseImpossible(RuntimeError):
    pass


def silences(pcm: bytes) -> list[tuple[float, float]]:
    """(début, fin) en secondes des silences d'au moins SILENCE_MIN, repérés par rapport au volume le plus fort."""
    ech = array("h")
    ech.frombytes(pcm[:len(pcm) - len(pcm) % 2])
    forces = [sum(abs(x) for x in ech[i:i + FENETRE]) / FENETRE for i in range(0, len(ech), FENETRE)]
    seuil = max(forces, default=0) * 0.06
    out, debut = [], None
    for k, force in enumerate(forces + [seuil + 1]):
        if force <= seuil and debut is None:
            debut = k
        elif force > seuil and debut is not None:
            if (k - debut) * FENETRE / TAUX >= SILENCE_MIN:
                out.append((debut * FENETRE / TAUX, k * FENETRE / TAUX))
            debut = None
    return out


def decouper(pcm: bytes, longueurs: list[int]) -> list[bytes]:
    """Coupe la prise en len(longueurs) morceaux au milieu de silences, là où les longueurs de texte les attendent.
    L'estimation repart de chaque coupe, et un silence long pèse plus qu'une virgule."""
    if len(longueurs) < 2:
        return [pcm]
    trouves = [s for s in silences(pcm) if s[0] > 0 and s[1] < len(pcm) / OCTETS_PAR_SECONDE]
    if len(trouves) < len(longueurs) - 1:
        raise PriseImpossible(f"{len(trouves)} silences pour {len(longueurs)} scènes")
    duree = len(pcm) / OCTETS_PAR_SECONDE
    coupes, position, indice = [], 0.0, 0
    for k in range(len(longueurs) - 1):
        attendu = position + longueurs[k] * (duree - position) / sum(longueurs[k:])
        reste = len(longueurs) - 2 - k  # autant de silences à laisser pour les coupes suivantes
        possibles = range(indice, len(trouves) - reste)
        j = min(possibles, key=lambda n: abs(sum(trouves[n]) / 2 - attendu) - 2 * (trouves[n][1] - trouves[n][0]))
        position = sum(trouves[j]) / 2
        coupes.append(int(position * TAUX) * 2)
        indice = j + 1
    bornes = [0] + coupes + [len(pcm)]
    return [pcm[a:b] for a, b in zip(bornes, bornes[1:])]


def _prise(cfg: dict, texte: str, journal) -> bytes:
    reglages = (cfg.get("perso") or {}).get("voix_gemini") or {}
    erreur = ""
    for modele in reglages.get("modeles", ["gemini-2.5-flash-preview-tts"]):
        for pause in (0, 65):  # la limite par minute se libère vite ; les rendus tournent en parallèle
            time.sleep(pause)
            try:
                r = requests.post(f"https://generativelanguage.googleapis.com/v1beta/models/{modele}:generateContent",
                                  headers={"x-goog-api-key": os.environ["GEMINI_API_KEY"]}, timeout=300, json={
                                      "contents": [{"parts": [{"text": STYLE + texte}]}],
                                      "generationConfig": {"responseModalities": ["AUDIO"], "speechConfig": {"voiceConfig": {
                                          "prebuiltVoiceConfig": {"voiceName": reglages.get("nom", "Schedar")}}}}})
            except requests.RequestException as e:
                erreur = f"{modele} : {type(e).__name__}"
                continue
            if r.status_code != 200:
                erreur = f"{modele} : HTTP {r.status_code}"
                continue
            try:
                pcm = base64.b64decode(r.json()["candidates"][0]["content"]["parts"][0]["inlineData"]["data"])
            except (KeyError, IndexError, ValueError):
                erreur = f"{modele} : réponse sans audio"
                continue
            vitesse = len(texte) / max(len(pcm) / OCTETS_PAR_SECONDE, 0.1)
            if VITESSE[0] <= vitesse <= VITESSE[1]:
                return pcm
            erreur = f"{modele} : {vitesse:.1f} caractères par seconde, prise écartée"
            journal(f"    ↺ voix : {erreur}")
    raise PriseImpossible(erreur)


def narration(cfg: dict, dits: list[dict], dossier: Path, prefixe: str, journal=print) -> list[dict]:
    """Même résultat que Voix.narration : [{"cle", "src", "duree"}] pour les scènes qui ont un texte."""
    textes = [(d["cle"], preparer(d["texte"], coller=False)) for d in dits if d.get("texte")]
    textes = [(c, t) for c, t in textes if t]
    pcm = _prise(cfg, "\n".join(t for _, t in textes), journal)
    morceaux = decouper(pcm, [len(t) for _, t in textes])
    pistes = []
    for (cle, _), morceau in zip(textes, morceaux):
        nom = f"{prefixe}-{cle}.wav"
        with wave.open(str(dossier / nom), "wb") as w:
            w.setnchannels(1)
            w.setsampwidth(2)
            w.setframerate(TAUX)
            w.writeframes(morceau)
        pistes.append({"cle": cle, "src": f"{dossier.name}/{nom}", "duree": round(len(morceau) / OCTETS_PAR_SECONDE, 3)})
    journal(f"    🎙️ voix de conseil : une prise de {len(pcm) / OCTETS_PAR_SECONDE:.0f} s, {len(pistes)} scènes")
    return pistes
