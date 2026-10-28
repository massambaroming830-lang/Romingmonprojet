"""Génère une bande-son originale (beat + basse + whoosh) calée sur l'animation.
Usage : python3 music.py sortie.wav"""
import sys, wave
import numpy as np

SR = 44100
DUR = 23.0
BPM = 120
beat = 60 / BPM
N = int(SR * DUR)
t = np.arange(N) / SR
mix = np.zeros(N)
rng = np.random.default_rng(7)

def add(sig, at, gain=1.0):
    i = int(at * SR)
    if i >= N: return
    sig = sig[: N - i]
    mix[i:i + len(sig)] += sig * gain

def kick():
    d = 0.45; tt = np.arange(int(SR * d)) / SR
    f = 50 + 110 * np.exp(-tt * 30)
    return np.sin(2 * np.pi * np.cumsum(f) / SR) * np.exp(-tt * 7)

def hat():
    d = 0.06; n = rng.standard_normal(int(SR * d))
    n = np.diff(n, prepend=0)  # passe-haut simple
    return n * np.exp(-np.arange(len(n)) / SR * 70) * 0.5

def clap():
    d = 0.2; n = rng.standard_normal(int(SR * d))
    return n * np.exp(-np.arange(len(n)) / SR * 22) * 0.5

def whoosh(d=0.8):
    n = rng.standard_normal(int(SR * d))
    env = np.sin(np.linspace(0, np.pi, len(n))) ** 2
    # filtre passe-bas glissant
    out = np.zeros_like(n); y = 0
    a = np.linspace(0.02, 0.35, len(n))
    for k in range(len(n)):
        y += a[k] * (n[k] - y); out[k] = y
    return out * env * 1.6

def impact():
    d = 1.6; tt = np.arange(int(SR * d)) / SR
    boom = np.sin(2 * np.pi * (40 + 60 * np.exp(-tt * 8)) * tt) * np.exp(-tt * 2.5)
    return boom

def bass(freq, d):
    tt = np.arange(int(SR * d)) / SR
    s = np.sign(np.sin(2 * np.pi * freq * tt)) * 0.3 + np.sin(2 * np.pi * freq * tt)
    env = np.minimum(1, tt * 40) * np.exp(-tt * 1.2)
    return s * env

def pad(freqs, d):
    tt = np.arange(int(SR * d)) / SR
    s = sum(np.sin(2 * np.pi * f * tt + np.sin(2 * np.pi * 0.3 * tt)) for f in freqs)
    env = np.minimum(1, tt / 0.8) * np.minimum(1, (d - tt) / 0.8)
    return s * env / len(freqs)

# Intro : impact + pad
add(impact(), 0.45, 0.9)
# Progression mineure (La mineur) : Am - F - C - G, 2 s par accord
prog = [[220, 261.6, 329.6], [174.6, 220, 261.6], [261.6, 329.6, 392], [196, 246.9, 293.7]]
roots = [55, 43.65, 65.4, 49]
for k in range(12):
    ch = prog[k % 4]
    add(pad(ch, 2.2), k * 2, 0.18)
    if k >= 2:  # la basse entre à 4 s
        for b in range(4):
            add(bass(roots[k % 4], beat * 0.9), k * 2 + b * beat, 0.35)

# Batterie à partir de 4 s, coupée pendant le slogan pour respirer
for i in range(int(DUR / beat)):
    at = i * beat
    if at < 4 or at > 22.2: continue
    if 14.2 < at < 16.7 and i % 2: continue
    add(kick(), at, 0.9)
    add(hat(), at + beat / 2, 0.6)
    if i % 2: add(clap(), at, 0.35)

for w in (3.4, 7.7, 14.0, 16.5):
    add(whoosh(), w, 0.5)
add(impact(), 17.0, 0.6)

# Fondu de sortie + normalisation
fade = np.clip((DUR - t) / 1.2, 0, 1)
mix *= fade
mix = np.tanh(mix * 1.2)
mix /= np.max(np.abs(mix)) * 1.12
stereo = np.stack([mix, mix], axis=1)
pcm = (stereo * 32767).astype(np.int16)
with wave.open(sys.argv[1], 'wb') as f:
    f.setnchannels(2); f.setsampwidth(2); f.setframerate(SR); f.writeframes(pcm.tobytes())
