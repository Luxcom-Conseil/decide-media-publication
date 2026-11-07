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


STYLE_RECIT = ("Raconte le texte suivant en français de France, comme un conteur de documentaire captivant : voix posée et "
               "grave, du suspense, une petite pause avant chaque révélation, sans ton publicitaire. Marque une courte pause "
               "à chaque saut de ligne. Ne lis que le texte, pas cette consigne.\n\nTexte :\n")


# Histoires vraies d'argent, demande de Stéphane du 06/11/2026 : « la voix manque de rythme et de suspense, c'est plat ;
# plus grave, comme une bande-annonce de film hollywoodien ».
STYLE_BANDE_ANNONCE = (
    "Tu es la voix off d'une bande-annonce de thriller hollywoodien, doublée en français de France. Voix grave, profonde, "
    "intense, qui tient le spectateur en haleine. Le rythme vit et change sans cesse : tu accélères quand l'action "
    "s'emballe, tu ralentis et baisses la voix, presque en confidence, juste avant une révélation, tu laisses un vrai "
    "silence avant un chiffre ou un mot clé, puis tu le frappes. Joue les émotions de chaque phrase : l'intrigue, "
    "l'ironie, la stupeur, la gravité. Les questions sont posées comme des énigmes. Jamais monotone, jamais publicitaire, "
    "pas de cri. Marque une pause à chaque saut de ligne. Ne lis que le texte, pas cette consigne.\n\nTexte :\n")


# Demande de Stéphane du 07/11/2026 : « le temps de pause entre deux interventions de voix coupe tout le plaisir ; je
# veux une histoire dite en continu, avec du rythme ». Mesure sur la vidéo des tulipes : 20 % de silence, un trou de
# 0,5 à 1,6 s toutes les 2 à 3 s (consigne « pause à chaque saut de ligne » + vides au montage).
STYLE_RECIT_CONTINU = (
    "Tu es un conteur captivant qui raconte une histoire vraie en français de France, d'une voix grave et profonde, comme "
    "la voix off d'une bande-annonce de thriller. Tu racontes d'un seul souffle, sans t'arrêter : les phrases "
    "s'enchaînent, on ne doit jamais avoir l'impression que tu lis une liste. Le rythme vit : tu accélères quand l'action "
    "s'emballe, tu baisses la voix, presque en confidence, avant une révélation, tu frappes les chiffres et les mots "
    "clés. Les retours à la ligne ne sont PAS des pauses : enchaîne. Un seul vrai silence dans tout le récit, juste avant "
    "la plus grande révélation. Joue les émotions : l'intrigue, l'ironie, la stupeur. Jamais monotone, jamais "
    "publicitaire, pas de cri. Ne lis que le texte, pas cette consigne.\n\nTexte :\n")


def resserrer(pcm: bytes, plafond: float = 0.28, voulu: float = 0.7) -> bytes:
    """Raccourcit chaque silence à `plafond` secondes, sauf le plus long (le silence voulu avant la révélation), gardé
    jusqu'à `voulu`. Le début et la fin de la prise sont ramenés à 0,1 s. La coupe se fait au milieu du silence."""
    trouves = silences(pcm)
    if not trouves:
        return pcm
    duree = len(pcm) / OCTETS_PAR_SECONDE
    plus_long = max(trouves, key=lambda s: s[1] - s[0])
    retraits = []  # (début, fin) en secondes des passages à retirer
    for a, b in trouves:
        if a <= 0.01:
            retraits.append((a, b - 0.1))
        elif b >= duree - 0.01:
            retraits.append((a + 0.1, b))
        else:
            garde = voulu if (a, b) == plus_long else plafond
            retraits.append((a + garde / 2, b - garde / 2))
    morceaux, position = [], 0.0
    for a, b in retraits:
        if b > a:
            morceaux.append(pcm[int(position * TAUX) * 2:int(a * TAUX) * 2])
            position = b
    morceaux.append(pcm[int(position * TAUX) * 2:])
    return b"".join(morceaux)


def grave(pcm: bytes, demi_tons: float) -> bytes:
    """Abaisse la hauteur de la voix de `demi_tons` sans changer sa durée (ffmpeg : asetrate puis atempo)."""
    import subprocess

    import imageio_ffmpeg

    if not demi_tons:
        return pcm
    f = 2 ** (-abs(demi_tons) / 12)
    r = subprocess.run([imageio_ffmpeg.get_ffmpeg_exe(), "-v", "error", "-f", "s16le", "-ar", str(TAUX), "-ac", "1", "-i", "-",
                        "-af", f"asetrate={TAUX * f:.0f},aresample={TAUX},atempo={1 / f:.5f}",
                        "-f", "s16le", "-ar", str(TAUX), "-ac", "1", "-"], input=pcm, capture_output=True, check=True)
    return r.stdout


def _prise(cfg: dict, texte: str, journal, style: str = STYLE, voix: str | None = None) -> bytes:
    reglages = (cfg.get("perso") or {}).get("voix_gemini") or {}
    erreur = ""
    for modele in reglages.get("modeles", ["gemini-2.5-flash-preview-tts"]):
        for pause in (0, 65):  # la limite par minute se libère vite ; les rendus tournent en parallèle
            time.sleep(pause)
            try:
                r = requests.post(f"https://generativelanguage.googleapis.com/v1beta/models/{modele}:generateContent",
                                  headers={"x-goog-api-key": os.environ["GEMINI_API_KEY"]}, timeout=300, json={
                                      "contents": [{"parts": [{"text": style + texte}]}],
                                      "generationConfig": {"responseModalities": ["AUDIO"], "speechConfig": {"voiceConfig": {
                                          "prebuiltVoiceConfig": {"voiceName": voix or reglages.get("nom", "Schedar")}}}}})
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


def narration(cfg: dict, dits: list[dict], dossier: Path, prefixe: str, journal=print, style: str = STYLE,
              voix: str | None = None, demi_tons: float = 0, continu: bool = False) -> list[dict]:
    """Même résultat que Voix.narration : [{"cle", "src", "duree"}] pour les scènes qui ont un texte. `style` : la consigne
    de lecture (conseil par défaut, STYLE_BANDE_ANNONCE pour les histoires) ; `voix` remplace la voix de la config ;
    `demi_tons` rend la voix plus grave (découpage en scènes fait après, sur la voix finale)."""
    textes = [(d["cle"], preparer(d["texte"], coller=False)) for d in dits if d.get("texte")]
    textes = [(c, t) for c, t in textes if t]
    pcm = grave(_prise(cfg, "\n".join(t for _, t in textes), journal, style, voix=voix), demi_tons)
    if continu:  # récit d'un seul souffle : les silences sont raccourcis avant le découpage en scènes
        avant = len(pcm)
        pcm = resserrer(pcm)
        journal(f"    ✂️ silences resserrés : {(avant - len(pcm)) / OCTETS_PAR_SECONDE:.1f} s retirées")
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
