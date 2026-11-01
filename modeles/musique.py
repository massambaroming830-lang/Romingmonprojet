"""Génère une musique originale calée sur une vidéo.

Usage :
  python3 musique.py sortie.wav --duree 20 [--bpm 120] [--ambiance energique|douce|luxe|afro]
                                [--transitions 3.5,7,10.5] [--graine 7]

--transitions : instants (en secondes) où placer un « whoosh » + impact.
"""
import argparse, wave
import numpy as np

ap = argparse.ArgumentParser()
ap.add_argument('sortie')
ap.add_argument('--duree', type=float, required=True)
ap.add_argument('--bpm', type=float, default=None)
ap.add_argument('--ambiance', default='energique', choices=['energique', 'douce', 'luxe', 'afro'])
ap.add_argument('--transitions', default='')
ap.add_argument('--graine', type=int, default=7)
a = ap.parse_args()

SR = 44100
DUR = a.duree
AMB = a.ambiance
BPM = a.bpm or {'energique': 124, 'douce': 92, 'luxe': 100, 'afro': 108}[AMB]
beat = 60 / BPM
N = int(SR * DUR)
t = np.arange(N) / SR
mix = np.zeros(N)
rng = np.random.default_rng(a.graine)
coupures = [float(x) for x in a.transitions.split(',') if x.strip()]


def add(sig, at, gain=1.0):
    i = int(at * SR)
    if i >= N or i + len(sig) <= 0:
        return
    if i < 0:
        sig, i = sig[-i:], 0
    sig = sig[: N - i]
    mix[i:i + len(sig)] += sig * gain


def env_t(d):
    return np.arange(int(SR * d)) / SR


def kick():
    tt = env_t(.45)
    f = 50 + 110 * np.exp(-tt * 30)
    return np.sin(2 * np.pi * np.cumsum(f) / SR) * np.exp(-tt * 7)


def hat(d=.06, dec=70):
    n = np.diff(rng.standard_normal(int(SR * d)), prepend=0)
    return n * np.exp(-np.arange(len(n)) / SR * dec) * .5


def clap():
    n = rng.standard_normal(int(SR * .2))
    return n * np.exp(-np.arange(len(n)) / SR * 22) * .5


def perc(freq, d=.18):  # percussion boisée (conga / shaker)
    tt = env_t(d)
    return np.sin(2 * np.pi * freq * tt * (1 + .5 * np.exp(-tt * 40))) * np.exp(-tt * 25)


def whoosh(d=.8):
    n = rng.standard_normal(int(SR * d))
    env = np.sin(np.linspace(0, np.pi, len(n))) ** 2
    out = np.zeros_like(n); y = 0
    coef = np.linspace(.02, .35, len(n))
    for k in range(len(n)):
        y += coef[k] * (n[k] - y); out[k] = y
    return out * env * 1.6


def impact(d=1.6):
    tt = env_t(d)
    return np.sin(2 * np.pi * (40 + 60 * np.exp(-tt * 8)) * tt) * np.exp(-tt * 2.5)


def bass(freq, d):
    tt = env_t(d)
    s = np.sign(np.sin(2 * np.pi * freq * tt)) * .3 + np.sin(2 * np.pi * freq * tt)
    return s * np.minimum(1, tt * 40) * np.exp(-tt * 1.2)


def pad(freqs, d):
    tt = env_t(d)
    s = sum(np.sin(2 * np.pi * f * tt + np.sin(2 * np.pi * .3 * tt)) for f in freqs)
    return s * np.minimum(1, tt / .8) * np.minimum(1, np.maximum(0, d - tt) / .8) / len(freqs)


def pluck(freq, d=.5):  # note pincée (marimba / kalimba)
    tt = env_t(d)
    return (np.sin(2 * np.pi * freq * tt) + .3 * np.sin(4 * np.pi * freq * tt)) * np.exp(-tt * 9)


# Progressions d'accords (fréquences) selon l'ambiance
PROG = {
    'energique': ([[220, 261.6, 329.6], [174.6, 220, 261.6], [261.6, 329.6, 392], [196, 246.9, 293.7]], [55, 43.65, 65.4, 49]),
    'douce': ([[261.6, 329.6, 392], [220, 261.6, 329.6], [174.6, 220, 261.6], [196, 246.9, 293.7]], [65.4, 55, 43.65, 49]),
    'luxe': ([[220, 261.6, 329.6, 392], [293.7, 349.2, 440], [246.9, 293.7, 349.2, 440], [329.6, 415.3, 493.9]], [55, 73.4, 61.7, 82.4]),
    'afro': ([[196, 246.9, 293.7], [261.6, 329.6, 392], [220, 261.6, 329.6], [174.6, 220, 261.6]], [49, 65.4, 55, 43.65]),
}
accords, basses = PROG[AMB]
mesure = beat * 4
intro = min(2 * mesure, DUR * .2)

add(impact(), .3, .8)
k = 0
while k * mesure < DUR:
    at = k * mesure
    add(pad(accords[k % 4], mesure * 1.1), at, .2 if AMB != 'douce' else .28)
    if at >= intro:
        if AMB == 'douce':
            for b in range(4):
                add(pluck(accords[k % 4][b % 3] * 2, .8), at + b * beat, .18)
            add(bass(basses[k % 4], mesure * .9), at, .25)
        elif AMB == 'afro':
            for b, frac in enumerate([0, .75, 1.5, 2, 2.75, 3.5]):
                add(bass(basses[k % 4], beat * .45), at + frac * beat, .3)
        else:
            for b in range(4):
                add(bass(basses[k % 4], beat * .9), at + b * beat, .32)
    k += 1

# Batterie
i = 0
while i * beat < DUR:
    at = i * beat
    if at >= intro and at < DUR - .8:
        if AMB == 'energique':
            add(kick(), at, .9); add(hat(), at + beat / 2, .6)
            if i % 2: add(clap(), at, .35)
        elif AMB == 'luxe':
            add(kick(), at, .7 if i % 2 == 0 else .4); add(hat(.04), at + beat / 2, .35)
            if i % 4 == 2: add(clap(), at, .3)
        elif AMB == 'afro':
            if i % 2 == 0: add(kick(), at, .85)
            add(kick(), at + beat * .75, .4) if i % 4 == 1 else None
            for s in range(4): add(hat(.03, 90), at + s * beat / 4, .25 + (.2 if s == 2 else 0))
            add(perc(320 if i % 2 else 240), at + beat * .5, .4)
            if i % 4 == 3: add(perc(420), at + beat * .25, .35)
            if i % 2: add(clap(), at, .25)
            for nn, fr in enumerate([523.3, 659.3, 784, 659.3]):
                if (i + nn) % 3 == 0: add(pluck(fr, .4), at + nn * beat / 4, .1)
        elif AMB == 'douce':
            if i % 4 == 0: add(kick(), at, .4)
            add(hat(.03), at + beat / 2, .15)
    i += 1

for c in coupures:
    add(whoosh(), c - .55, .45)
    add(impact(1.0), c, .3)

# Fondu de sortie, saturation douce, normalisation
mix *= np.clip((DUR - t) / 1.2, 0, 1) * np.clip(t / .05, 0, 1)
mix = np.tanh(mix * 1.2)
mix /= max(1e-9, np.max(np.abs(mix))) * 1.12
stereo = np.stack([mix, mix], axis=1)
with wave.open(a.sortie, 'wb') as f:
    f.setnchannels(2); f.setsampwidth(2); f.setframerate(SR)
    f.writeframes((stereo * 32767).astype(np.int16).tobytes())
print(f'Musique : {a.sortie} ({DUR:.1f} s, {BPM:.0f} BPM, ambiance {AMB})')
