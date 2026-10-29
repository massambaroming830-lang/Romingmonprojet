"""Bande-son du montage « parole » : la voix d'origine + bruitages (whoosh aux transitions,
impacts sur les mots forts) + une nappe pour l'écran de fin.
Usage : python3 montage_audio.py   (lit sources/parole.mp4 et montage_timings.js, écrit montage.wav)"""
import json, subprocess
import numpy as np

SR = 44100
src = open('montage_timings.js').read()
M = json.loads(src[src.index('{'): src.rindex('}') + 1])
DUR = M['clip'] + M['outro']
N = int(SR * DUR)

raw = subprocess.run(['ffmpeg', '-v', 'error', '-i', 'sources/parole.mp4', '-f', 's16le', '-ac', '2', '-ar', str(SR), '-'],
                     capture_output=True, check=True).stdout
voice = np.frombuffer(raw, dtype=np.int16).astype(np.float32).reshape(-1, 2) / 32768
mix = np.zeros((N, 2), dtype=np.float32)
n = min(N, len(voice))
fade = np.clip((M['clip'] - np.arange(n) / SR) / 0.08, 0, 1)[:, None]   # évite un clic à la coupe
mix[:n] += voice[:n] * fade

rng = np.random.default_rng(3)
fx = np.zeros(N, dtype=np.float32)

def add(sig, at, gain):
    i = int(at * SR)
    if i >= N: return
    sig = sig[: N - i]; fx[i:i + len(sig)] += sig * gain

def whoosh(d=0.45):
    x = rng.standard_normal(int(SR * d)); out = np.zeros_like(x); y = 0
    a = np.linspace(0.03, 0.4, len(x))
    for k in range(len(x)): y += a[k] * (x[k] - y); out[k] = y
    return out * np.sin(np.linspace(0, np.pi, len(x))) ** 2 * 1.6

def impact(d=0.9):
    tt = np.arange(int(SR * d)) / SR
    return np.sin(2 * np.pi * (45 + 70 * np.exp(-tt * 10)) * tt) * np.exp(-tt * 5)

def pad(freqs, d):
    tt = np.arange(int(SR * d)) / SR
    s = sum(np.sin(2 * np.pi * f * tt) for f in freqs) / len(freqs)
    return s * np.minimum(1, tt / 0.3) * np.minimum(1, (d - tt) / 0.6)

for w in M['whoosh']:
    add(whoosh(), w - 0.3, 0.22)
for h in M['hits']:
    add(impact(), h, 0.35)
add(pad([220, 277.2, 329.6, 440], M['outro']), M['clip'] + 0.1, 0.18)

mix += fx[:, None]
mix /= max(1.0, np.max(np.abs(mix)) / 0.97)
pcm = (mix * 32767).astype('<i2')
subprocess.run(['ffmpeg', '-v', 'error', '-y', '-f', 's16le', '-ac', '2', '-ar', str(SR), '-i', '-', 'montage.wav'],
               input=pcm.tobytes(), check=True)
print('montage.wav', round(DUR, 2), 's')
