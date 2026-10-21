"""Compose une mélodie de fond originale (libre de droits) : nappe douce + arpège léger + pulsation discrète.

Progression La mineur – Fa – Do – Sol, 92 BPM, 64 secondes, conçue pour boucler sans à-coup.
    python outils/melodie.py public/melodie.wav
"""
import sys
import wave

import numpy as np

SR = 44100
BPM = 92
TEMPS = 60 / BPM
DUREE = 64.0

ACCORDS = [  # (fondamentale, notes de l'accord) en Hz
    (110.00, [220.00, 261.63, 329.63]),  # La mineur
    (87.31, [174.61, 220.00, 261.63]),   # Fa majeur
    (130.81, [261.63, 329.63, 392.00]),  # Do majeur
    (98.00, [196.00, 246.94, 293.66]),   # Sol majeur
]
MESURE = 4 * TEMPS * 2  # chaque accord dure 2 mesures


def enveloppe(n, attaque, relache):
    e = np.ones(n)
    a, r = int(attaque * SR), int(relache * SR)
    e[:a] = np.linspace(0, 1, a)
    e[-r:] = np.linspace(1, 0, r)
    return e


def note(freq, duree, volume, timbre="nappe"):
    t = np.arange(int(duree * SR)) / SR
    if timbre == "nappe":  # deux sinus légèrement désaccordés = chorus doux
        s = np.sin(2 * np.pi * freq * t) + 0.6 * np.sin(2 * np.pi * freq * 1.003 * t) + 0.25 * np.sin(2 * np.pi * freq * 2 * t)
        s *= enveloppe(len(t), 1.2, 1.5)
    elif timbre == "pluck":  # attaque nette, extinction rapide
        s = (np.sin(2 * np.pi * freq * t) + 0.3 * np.sin(2 * np.pi * freq * 3 * t)) * np.exp(-t * 4.5)
        s *= enveloppe(len(t), 0.005, 0.05)
    else:  # basse
        s = np.sin(2 * np.pi * freq * t) * np.exp(-t * 1.2)
        s *= enveloppe(len(t), 0.01, 0.2)
    return volume * s


def composer() -> np.ndarray:
    total = int(DUREE * SR)
    piste = np.zeros(total + int((MESURE + 3) * SR))
    t, k = 0.0, 0
    while t < DUREE:
        fond, notes = ACCORDS[k % len(ACCORDS)]
        debut = int(t * SR)
        for f in notes:  # nappe
            n = note(f, MESURE + 1.0, 0.10, "nappe")
            piste[debut:debut + len(n)] += n
        for b in range(4):  # basse sur chaque demi-mesure
            n = note(fond, TEMPS * 2, 0.22, "basse")
            p = debut + int(b * TEMPS * 2 * SR)
            piste[p:p + len(n)] += n
        motif = [0, 1, 2, 1, 2, 0, 1, 2]  # arpège en croches
        for i in range(16):
            f = notes[motif[i % len(motif)]] * 2
            n = note(f, TEMPS * 0.9, 0.07, "pluck")
            p = debut + int(i * TEMPS / 2 * SR)
            piste[p:p + len(n)] += n
        t += MESURE
        k += 1
    piste = piste[:total]
    piste /= np.max(np.abs(piste)) + 1e-9
    stereo = np.stack([piste, np.roll(piste, int(0.012 * SR))], axis=1) * 0.8  # léger élargissement
    return (stereo * 32767).astype(np.int16)


if __name__ == "__main__":
    sortie = sys.argv[1] if len(sys.argv) > 1 else "public/melodie.wav"
    with wave.open(sortie, "wb") as w:
        w.setnchannels(2)
        w.setsampwidth(2)
        w.setframerate(SR)
        w.writeframes(composer().tobytes())
    print("mélodie écrite :", sortie)
