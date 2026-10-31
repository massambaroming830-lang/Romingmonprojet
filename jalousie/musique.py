"""Bande-son originale : nappe cinématique + vent + whoosh aux transitions + impact sur l'affiche.
Usage : python3 musique.py musique.wav"""
import sys, wave
import numpy as np

SR, DUR = 44100, 15.0
N = int(SR * DUR)
t = np.arange(N) / SR
rng = np.random.default_rng(3)
mix = np.zeros((N, 2))
TRANS = [2.8, 5.4, 8.0, 10.0]  # instants des transitions (voir montage.py)
REVEAL = 10.0


def env(a, r, n):
    e = np.ones(n)
    a, r = int(a * SR), int(r * SR)
    e[:a] = np.linspace(0, 1, a)
    e[-r:] *= np.linspace(1, 0, r)
    return e


def add(sig, at, gain=1.0, pan=0.0):
    i = int(at * SR)
    sig = sig[: N - i]
    mix[i:i + len(sig), 0] += sig * gain * (1 - pan)
    mix[i:i + len(sig), 1] += sig * gain * (1 + pan)


def lowpass(x, a):
    y = np.empty_like(x); acc = 0.0
    for k in range(len(x)):
        acc += a * (x[k] - acc); y[k] = acc
    return y


# nappe : accords La mineur -> Fa -> Do -> Sol (cordes synthétiques douces)
chords = [[220, 261.63, 329.63], [174.61, 220, 261.63], [261.63, 329.63, 392], [196, 246.94, 293.66]]
seg = REVEAL / 4
for j, ch in enumerate(chords):
    n = int(seg * SR * 1.15)
    tt = np.arange(n) / SR
    s = sum(np.sin(2 * np.pi * f * tt + np.sin(2 * np.pi * 5 * tt) * 0.02) +
            0.3 * np.sin(2 * np.pi * f * 2.003 * tt) for f in ch)
    add(s * env(0.6, 0.6, n) / 6, j * seg, 0.5, pan=0.2 * (-1) ** j)

# basse qui pulse et accélère vers l'arrivée
for k, b in enumerate(np.arange(0, REVEAL, 0.5)):
    n = int(0.4 * SR); tt = np.arange(n) / SR
    f = [110, 87.31, 130.81, 98][min(3, int(b // seg))]
    add(np.sin(2 * np.pi * f * tt) * np.exp(-tt * 6), b, 0.35 + 0.03 * k / 4)

# vent continu (bruit filtré)
wind = lowpass(rng.standard_normal(int(REVEAL * SR)), 0.02)
add(wind / np.abs(wind).max() * env(1.0, 0.5, len(wind)), 0, 0.25)

# whoosh aux transitions
for x in TRANS:
    n = int(0.9 * SR)
    w = lowpass(rng.standard_normal(n), 0.15) * np.hanning(n)
    add(w, x - 0.45, 0.9, pan=0.3)

# impact + accord final sur l'affiche
n = int(4.5 * SR); tt = np.arange(n) / SR
boom = np.sin(2 * np.pi * (40 + 80 * np.exp(-tt * 20)) * tt) * np.exp(-tt * 2.5)
final = sum(np.sin(2 * np.pi * f * tt) for f in [220, 277.18, 329.63, 440]) * np.exp(-tt * 0.6) / 4
add(boom, REVEAL, 1.0)
add(final, REVEAL, 0.5)

mix /= np.abs(mix).max() * 1.12
with wave.open(sys.argv[1] if len(sys.argv) > 1 else "musique.wav", "wb") as f:
    f.setnchannels(2); f.setsampwidth(2); f.setframerate(SR)
    f.writeframes((mix * 32767).astype(np.int16).tobytes())
print("OK")
