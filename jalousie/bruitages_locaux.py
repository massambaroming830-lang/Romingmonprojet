"""Bruitages de remplacement synthétisés localement (sans API) pour « À bas la jalousie ».

À utiliser tant que la clé ElevenLabs n'a pas la permission sound_generation.
Usage : python3 bruitages_locaux.py  ->  bruitages.wav (repris automatiquement par montage.py)
Relancer elevenlabs.py avec une clé complète écrase ce fichier avec les vrais bruitages.
"""
import os, wave

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
SR = 44100
TOTAL = 14.4
rng = np.random.default_rng(7)


def lowpass(x, alpha):
    """Filtre passe-bas d'ordre 1 ; alpha (0..1) peut varier dans le temps."""
    y = np.empty_like(x)
    acc = 0.0
    a = np.broadcast_to(alpha, x.shape)
    for i in range(len(x)):
        acc += a[i] * (x[i] - acc)
        y[i] = acc
    return y


def env(n, attack, release):
    e = np.ones(n)
    na, nr = int(attack * SR), int(release * SR)
    if na: e[:na] = np.linspace(0, 1, na)
    if nr: e[-nr:] *= np.linspace(1, 0, nr)
    return e


def stereo(m, pan=0.0):
    return np.stack([m * (1 - max(0, pan)), m * (1 + min(0, pan))], axis=1)


def wind(dur):
    n = int(dur * SR)
    t = np.arange(n) / SR
    gust = 0.55 + 0.45 * np.sin(2 * np.pi * 0.35 * t) * np.sin(2 * np.pi * 0.13 * t + 1)
    l = lowpass(rng.standard_normal(n), 0.02 + 0.04 * gust) * gust
    r = lowpass(rng.standard_normal(n), 0.02 + 0.04 * gust[::-1]) * gust
    return np.stack([l, r], axis=1) * env(n, 0.6, 0.8)[:, None]


def whoosh(dur=0.9, down=False):
    n = int(dur * SR)
    t = np.linspace(0, 1, n)
    sweep = (1 - t) if down else t
    a = 0.01 + 0.25 * np.sin(np.pi * t) * (0.4 + 0.6 * sweep)
    m = lowpass(rng.standard_normal(n), a) * np.sin(np.pi * t) ** 2
    pan = np.linspace(-0.8, 0.8, n)
    return np.stack([m * (1 - np.clip(pan, 0, 1)), m * (1 + np.clip(pan, -1, 0))], axis=1)


def wing_flaps(dur, rate=3.0):
    n = int(dur * SR)
    out = np.zeros(n)
    for k in np.arange(0.2, dur - 0.3, 1 / rate):
        i, m = int(k * SR), int(0.18 * SR)
        burst = lowpass(rng.standard_normal(m), 0.08) * np.exp(-np.linspace(0, 6, m))
        out[i:i + m] += burst[: n - i]
    return stereo(out)


def boom(dur=2.5):
    n = int(dur * SR)
    t = np.arange(n) / SR
    f = 38 + 60 * np.exp(-t * 6)
    sub = np.sin(2 * np.pi * np.cumsum(f) / SR) * np.exp(-t * 1.6)
    hit = lowpass(rng.standard_normal(n), 0.3) * np.exp(-t * 18)
    tail = lowpass(rng.standard_normal(n), 0.05) * np.exp(-t * 2.2) * 0.4
    return stereo(sub + 0.6 * hit + tail)


def waves(dur):
    n = int(dur * SR)
    t = np.arange(n) / SR
    swell = np.clip(np.sin(2 * np.pi * 0.7 * t), 0, None) ** 2
    m = lowpass(rng.standard_normal(n), 0.03 + 0.15 * swell) * (0.3 + swell)
    return stereo(m) * env(n, 0.2, 0.4)[:, None]


def bells(dur):
    n = int(dur * SR)
    t = np.arange(n) / SR
    out = np.zeros(n)
    for k, f0 in [(0.2, 523.0), (0.9, 440.0), (1.6, 392.0)]:
        i = int(k * SR)
        tt = t[: n - i]
        tone = sum(a * np.sin(2 * np.pi * f0 * r * tt) for r, a in [(1, 1), (2.0, 0.5), (2.4, 0.35), (3.0, 0.2)])
        out[i:] += tone * np.exp(-tt * 1.8)
    city = lowpass(rng.standard_normal(n), 0.015) * 2
    return stereo(0.25 * out + city) * env(n, 0.3, 0.5)[:, None]


def applause(dur):
    n = int(dur * SR)
    out = np.zeros((n, 2))
    for _ in range(int(dur * 400)):
        i = rng.integers(0, n - 800)
        m = 300 + rng.integers(0, 400)
        clap = rng.standard_normal(m) * np.exp(-np.linspace(0, 8, m))
        pan = rng.uniform(-1, 1)
        out[i:i + m] += stereo(clap, pan) * rng.uniform(0.3, 1)
    return out * env(n, 0.6, 0.8)[:, None]


def place(mix, a, at, gain):
    i = int(at * SR)
    a = a[: len(mix) - i] * gain
    mix[i:i + len(a)] += a


def main():
    mix = np.zeros((int(TOTAL * SR), 2))
    w = wind(10.0); place(mix, w / np.abs(w).max(), 0.0, 0.35)
    f = wing_flaps(10.0); place(mix, f / np.abs(f).max(), 0.0, 0.25)
    for at, down in [(2.45, False), (5.05, False), (7.65, True)]:
        s = whoosh(0.9, down); place(mix, s / np.abs(s).max(), at, 0.8)
    s = waves(2.3); place(mix, s / np.abs(s).max(), 3.1, 0.35)
    s = bells(2.4); place(mix, s / np.abs(s).max(), 5.6, 0.3)
    s = boom(2.5); place(mix, s / np.abs(s).max(), 9.8, 1.0)
    s = applause(3.4); place(mix, s / np.abs(s).max(), 11.0, 0.4)
    mix = mix / np.abs(mix).max() * 0.9
    with wave.open(os.path.join(HERE, "bruitages.wav"), "wb") as fh:
        fh.setnchannels(2); fh.setsampwidth(2); fh.setframerate(SR)
        fh.writeframes((mix * 32767).astype(np.int16).tobytes())
    print("OK -> bruitages.wav (bruitages synthétisés localement)")


if __name__ == "__main__":
    main()
