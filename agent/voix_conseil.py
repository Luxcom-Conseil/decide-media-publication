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


def _mots(t: str) -> list[str]:
    import re
    import unicodedata

    t = unicodedata.normalize("NFKD", t.lower())
    t = "".join(c for c in t if not unicodedata.combining(c))
    return re.findall(r"[a-z0-9]+", t)


def lit_le_texte(cfg: dict, pcm: bytes, texte: str) -> bool | None:
    """La prise commence-t-elle bien par le texte ? Le 10/11/2026, gemini-3.8-flash-tts a lu la consigne de style à voix
    haute en tête de vidéo (signalé par Stéphane). On fait transcrire les 8 premières secondes par Gemini et on cherche
    les premiers mots du texte au début de la transcription. None = vérification impossible (quota, réseau)."""
    import io

    b = io.BytesIO()
    with wave.open(b, "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(TAUX)
        w.writeframes(pcm[:8 * OCTETS_PAR_SECONDE])
    donnees = base64.b64encode(b.getvalue()).decode()
    attendus = _mots(texte)[:6]
    for modele in ((cfg.get("video") or {}).get("modeles_gemini") or ["gemini-3.6-flash", "gemini-3.5-flash"]):
        try:
            r = requests.post(f"https://generativelanguage.googleapis.com/v1beta/models/{modele}:generateContent",
                              headers={"x-goog-api-key": os.environ["GEMINI_API_KEY"]}, timeout=120, json={
                                  "contents": [{"parts": [{"inlineData": {"mimeType": "audio/wav", "data": donnees}},
                                                          {"text": "Transcris mot pour mot cet audio en français, sans rien ajouter."}]}],
                                  "generationConfig": {"thinkingConfig": {"thinkingLevel": "low"}}})
            entendu = _mots("".join(p.get("text", "") for p in r.json()["candidates"][0]["content"]["parts"]))[:14]
        except (requests.RequestException, KeyError, IndexError, ValueError):
            continue
        return sum(m in entendu for m in attendus) >= max(2, len(attendus) - 2)
    return None


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


# Rubrique Présidentielle 2027, demande de Stéphane du 07/11/2026 : « raconte en y mettant du story telling, plus de
# rythme dans la voix, une voix plus chaude ».
STYLE_RECIT_CHALEUREUX = (
    "Tu es un conteur chaleureux et captivant qui raconte, en français de France, une histoire qui touche la vie de "
    "celui qui t'écoute. Voix chaude, ronde, proche, souriante quand il le faut, comme un ami passionné qui te raconte "
    "un truc incroyable au comptoir. Beaucoup de rythme : tu racontes d'un seul souffle, les phrases s'enchaînent et "
    "rebondissent, tu accélères quand ça s'emballe, tu ralentis et baisses la voix en confidence avant une révélation, "
    "tu fais sonner les chiffres et les noms. Les retours à la ligne ne sont PAS des pauses : enchaîne. Un seul vrai "
    "silence, juste avant la plus grande révélation. Joue les émotions : la surprise, la curiosité, l'ironie légère, "
    "la complicité. Jamais monotone, jamais publicitaire, jamais militant, pas de cri. Ne lis que le texte, pas cette "
    "consigne.\n\nTexte :\n")


# Demande de Stéphane du 09/11/2026 : « la lecture est linéaire voire monotone ; mets des accents, des montées et des
# descentes comme un vrai conteur, avec du suspense réel dans la voix ». Mesure sur le début de Van Meegeren (7 phrases,
# même voix Algenib) : écart de hauteur p10-p90 de 4,4 demi-tons avec gemini-2.5-flash-tts et STYLE_RECIT_CONTINU,
# 11,9 avec gemini-3.8-flash-tts et cette consigne, pour la même durée (40 s). Les indications entre crochets dans le
# texte rallongent la prise du double (le modèle les lit) : jamais de balise dans le texte.
# Format « notes du réalisateur » (profil, notes, puis la transcription seule sous son titre) : le 10/11/2026, la consigne
# en phrases suivie de « Texte : » a été LUE à voix haute par gemini-3.8-flash-tts. lit_le_texte() contrôle chaque prise.
_FIN_NOTES = ("\n\n### RÈGLE\nAucun mot de ces notes ne doit être prononcé. Dis uniquement la transcription ci-dessous, "
              "mot pour mot, en commençant par son premier mot.\n\n#### TRANSCRIPTION\n")
STYLE_CONTEUR = (
    "# PROFIL DE VOIX\nUn grand conteur d'histoires vraies, en français de France, comme dans un podcast de faits "
    "divers à succès.\n\n## NOTES DU RÉALISATEUR\n- Voix en montagne russe : jamais deux phrases sur la même note.\n"
    "- Monter vers l'aigu sur l'étonnement et les questions.\n- Descendre très bas, lentement, presque chuchoté, sur "
    "les secrets et juste avant chaque révélation.\n- Un très court silence avant un chiffre ou un nom, puis le frapper "
    "avec force.\n- Accélérer quand l'action s'emballe, ralentir pour faire durer le suspense.\n- Faire entendre "
    "l'ironie, l'indignation, la stupeur, la tension qui monte.\n- Les phrases s'enchaînent d'un seul souffle, sans "
    "pause à chaque retour à la ligne. Naturel, jamais publicitaire, pas de cri." + _FIN_NOTES)

# Rubrique Présidentielle 2027 : les mêmes montées et descentes, avec la chaleur demandée le 07/11/2026.
STYLE_CONTEUR_CHALEUREUX = (
    "# PROFIL DE VOIX\nUn conteur chaleureux et captivant, en français de France, comme un ami passionné qui raconte "
    "une histoire qui touche la vie de celui qui l'écoute. Voix chaude, ronde, proche.\n\n## NOTES DU RÉALISATEUR\n"
    "- Voix en montagne russe : jamais deux phrases sur la même note.\n- Monter vers l'aigu sur l'étonnement et les "
    "questions.\n- Descendre bas, lentement, en confidence, juste avant une révélation.\n- Un très court silence avant "
    "un chiffre, puis le faire sonner.\n- Accélérer quand ça s'emballe, ralentir pour faire durer le suspense.\n- Faire "
    "entendre la surprise, la curiosité, l'ironie légère, la gravité.\n- Les phrases s'enchaînent d'un seul souffle. "
    "Jamais publicitaire, jamais militant, pas de cri." + _FIN_NOTES)


DEBIT_VISE = 16.0  # caractères par seconde après resserrage (rythme TikTok ; les prises du 07/11 étaient à ~17)


def tempo(pcm: bytes, facteur: float) -> bytes:
    """Accélère la voix de `facteur` sans changer sa hauteur (ffmpeg atempo)."""
    import subprocess

    import imageio_ffmpeg

    r = subprocess.run([imageio_ffmpeg.get_ffmpeg_exe(), "-v", "error", "-f", "s16le", "-ar", str(TAUX), "-ac", "1", "-i", "-",
                        "-af", f"atempo={facteur:.4f}", "-f", "s16le", "-ar", str(TAUX), "-ac", "1", "-"],
                       input=pcm, capture_output=True, check=True)
    return r.stdout


def queue_propre(pcm: bytes) -> bytes:
    """Coupe le craquement saturé que gemini-3.8-flash-tts laisse parfois dans les 0,3 dernières secondes (mesuré le
    10/11/2026 : 9 échantillons écrêtés entre 40,32 et 40,44 s sur une prise de 40,45 s)."""
    import numpy as np

    x = np.frombuffer(pcm, dtype=np.int16)
    fin = int(0.3 * TAUX)
    sature = np.where(np.abs(x[-fin:].astype(np.int32)) >= 32000)[0]
    if len(sature):
        x = x[:max(0, len(x) - fin + int(sature[0]) - int(0.01 * TAUX))]
    return x.tobytes()


def resserrer(pcm: bytes, plafond: float = 0.28, voulu: float = 0.6, nb_voulus: int = 2) -> bytes:
    """Raccourcit chaque silence à `plafond` secondes, sauf les `nb_voulus` plus longs (les silences de suspense avant
    les révélations), gardés jusqu'à `voulu`. Le début et la fin de la prise sont ramenés à 0,1 s. La coupe se fait au
    milieu du silence."""
    trouves = silences(pcm)
    if not trouves:
        return pcm
    duree = len(pcm) / OCTETS_PAR_SECONDE
    longs = sorted(trouves, key=lambda s: s[1] - s[0], reverse=True)[:nb_voulus]
    retraits = []  # (début, fin) en secondes des passages à retirer
    for a, b in trouves:
        if a <= 0.01:
            retraits.append((a, b - 0.1))
        elif b >= duree - 0.01:
            retraits.append((a + 0.1, b))
        else:
            garde = voulu if (a, b) in longs else plafond
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


def _prise(cfg: dict, texte: str, journal, style: str = STYLE, voix: str | None = None,
           modeles: list[str] | None = None) -> bytes:
    reglages = (cfg.get("perso") or {}).get("voix_gemini") or {}
    erreur = ""
    for modele in modeles or reglages.get("modeles", ["gemini-2.5-flash-preview-tts"]):
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
                lu = lit_le_texte(cfg, pcm, texte)
                if lu is False or (lu is None and vitesse < 12.5):  # sans vérification : seulement une prise vive
                    erreur = f"{modele} : la prise ne commence pas par le texte (consigne lue à voix haute ?)"
                    journal(f"    ↺ voix : {erreur}")
                    continue
                if modele != (modeles or [modele])[0]:
                    journal(f"    ↺ voix : relais sur {modele}")
                return queue_propre(pcm)
            erreur = f"{modele} : {vitesse:.1f} caractères par seconde, prise écartée"
            journal(f"    ↺ voix : {erreur}")
    raise PriseImpossible(erreur)


def narration(cfg: dict, dits: list[dict], dossier: Path, prefixe: str, journal=print, style: str = STYLE,
              voix: str | None = None, demi_tons: float = 0, continu: bool = False,
              modeles: list[str] | None = None) -> list[dict]:
    """Même résultat que Voix.narration : [{"cle", "src", "duree"}] pour les scènes qui ont un texte. `style` : la consigne
    de lecture (conseil par défaut, STYLE_BANDE_ANNONCE pour les histoires) ; `voix` remplace la voix de la config ;
    `demi_tons` rend la voix plus grave (découpage en scènes fait après, sur la voix finale)."""
    textes = [(d["cle"], preparer(d["texte"], coller=False)) for d in dits if d.get("texte")]
    textes = [(c, t) for c, t in textes if t]
    pcm = grave(_prise(cfg, "\n".join(t for _, t in textes), journal, style, voix=voix, modeles=modeles), demi_tons)
    if continu:  # récit d'un seul souffle : les silences sont raccourcis avant le découpage en scènes
        avant = len(pcm)
        pcm = resserrer(pcm)
        journal(f"    ✂️ silences resserrés : {(avant - len(pcm)) / OCTETS_PAR_SECONDE:.1f} s retirées")
        # le conteur expressif (gemini-3.8-flash-tts) ralentit beaucoup : 104 s pour 1 361 caractères le 10/11/2026,
        # contre 79 s avant. On ramène le débit à DEBIT_VISE sans changer la hauteur (atempo), 25 % au plus.
        debit = sum(len(t) for _, t in textes) / max(len(pcm) / OCTETS_PAR_SECONDE, 0.1)
        if debit < DEBIT_VISE:
            facteur = min(1.25, DEBIT_VISE / debit)
            pcm = tempo(pcm, facteur)
            journal(f"    ⏩ débit {debit:.1f} → {debit * facteur:.1f} caractères/s (×{facteur:.2f})")
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
