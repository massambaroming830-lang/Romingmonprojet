"""Voix off + bruitages ElevenLabs pour « À bas la jalousie », calés sur le montage (14,4 s).

Usage : ELEVENLABS_API_KEY=... python3 elevenlabs.py
Sorties : voix_off.wav et bruitages.wav (44,1 kHz stéréo), utilisés automatiquement par montage.py.
Les réponses de l'API sont gardées dans audio_el/ : relancer le script ne refacture pas les crédits.
Supprimer un fichier de audio_el/ pour régénérer seulement cet élément.

Variables optionnelles :
  ELEVENLABS_VOICE_ID   voix du narrateur (défaut : George, voix grave de bande-annonce)
  ELEVENLABS_MODEL_ID   défaut : eleven_multilingual_v2 (bon en français)
"""
import hashlib, json, os, subprocess, sys, urllib.request, urllib.error

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
CACHE = os.path.join(HERE, "audio_el")
SR = 44100
TOTAL = 14.4  # durée de la vidéo (voir montage.py : scènes + affiche - transitions)
API = "https://api.elevenlabs.io/v1"
KEY = os.environ.get("ELEVENLABS_API_KEY", "").strip()
VOICE = os.environ.get("ELEVENLABS_VOICE_ID", "JBFqnCBsd6RMkjVDRZzb")
MODEL = os.environ.get("ELEVENLABS_MODEL_ID", "eleven_multilingual_v2")

# Repères du montage : Kinshasa 0-2,8 | Angola 2,8-5,4 | Bruxelles 5,4-8,0 | La Madeleine 8,0-10,0 | affiche 10,0-14,4
# (début, fin max, texte)
VOIX = [
    (0.35, 2.65, "De Kinshasa..."),
    (3.00, 5.30, "en passant par l'Angola..."),
    (5.60, 7.90, "il arrive enfin à Bruxelles !"),
    (8.15, 10.0, "Jérémie et son groupe présentent..."),
    (10.25, 14.2, "À bas la jalousie ! Le 20 décembre, à La Madeleine. Réservez vos places !"),
]

# (début, durée, volume, description en anglais pour le modèle d'effets sonores)
BRUITAGES = [
    (0.0, 10.0, 0.55, "continuous strong wind rushing past the camera during a fast aerial drone flight, "
                      "with occasional powerful eagle wing flaps, cinematic"),
    (0.15, 2.0, 0.8, "a single loud African fish eagle cry echoing over a wide river"),
    (2.45, 0.9, 0.9, "fast cinematic whoosh transition"),
    (3.1, 2.3, 0.7, "ocean waves crashing on cliffs and water splashing as a bird skims the surface"),
    (5.05, 0.9, 0.9, "fast cinematic whoosh transition"),
    (5.6, 2.4, 0.5, "european city ambience at dusk, distant traffic and church bells ringing"),
    (7.65, 0.9, 0.9, "deep cinematic swoosh as a bird dives down"),
    (8.0, 2.0, 0.6, "excited crowd chatter outside a theatre at night, eagle wings landing"),
    (9.8, 2.5, 1.0, "huge cinematic trailer boom impact hit with reverb tail"),
    (11.0, 3.4, 0.55, "theatre audience bursting into laughter and applause"),
]


def post(path, payload, out):
    if os.path.exists(out):
        return out
    if not KEY:
        sys.exit("ELEVENLABS_API_KEY manquante.")
    req = urllib.request.Request(f"{API}{path}", data=json.dumps(payload).encode(), method="POST",
                                 headers={"xi-api-key": KEY, "Content-Type": "application/json",
                                          "Accept": "audio/mpeg"})
    try:
        with urllib.request.urlopen(req, timeout=180) as r:
            data = r.read()
    except urllib.error.HTTPError as e:
        sys.exit(f"ElevenLabs {path} -> HTTP {e.code} : {e.read().decode(errors='replace')[:300]}")
    os.makedirs(CACHE, exist_ok=True)
    with open(out, "wb") as f:
        f.write(data)
    return out


def cache_name(kind, payload):
    h = hashlib.sha1(json.dumps(payload, sort_keys=True).encode()).hexdigest()[:10]
    return os.path.join(CACHE, f"{kind}_{h}.mp3")


def decode(path, tempo=1.0):
    """mp3 -> tableau float32 stéréo 44,1 kHz (avec accélération éventuelle sans changer la hauteur)."""
    af = ["-af", f"atempo={tempo:.4f}"] if abs(tempo - 1) > 1e-3 else []
    raw = subprocess.run(["ffmpeg", "-v", "error", "-i", path, *af, "-f", "f32le", "-ac", "2",
                          "-ar", str(SR), "-"], check=True, capture_output=True).stdout
    return np.frombuffer(raw, dtype=np.float32).reshape(-1, 2).copy()


def trim_silence(a, thr=0.01):
    idx = np.where(np.abs(a).max(axis=1) > thr)[0]
    return a[max(0, idx[0] - 400): idx[-1] + 4000] if len(idx) else a


def place(mix, a, at, gain=1.0, fade=0.05):
    i = int(at * SR)
    a = a[: len(mix) - i] * gain
    nf = min(int(fade * SR), len(a) // 2)
    if nf:
        ramp = np.linspace(0, 1, nf)[:, None]
        a[:nf] *= ramp
        a[-nf:] *= ramp[::-1]
    mix[i:i + len(a)] += a


def save(path, mix, peak):
    mix = mix / max(1e-6, np.abs(mix).max()) * peak
    import wave
    with wave.open(path, "wb") as f:
        f.setnchannels(2); f.setsampwidth(2); f.setframerate(SR)
        f.writeframes((mix * 32767).astype(np.int16).tobytes())


def main():
    n = int(TOTAL * SR)

    voix = np.zeros((n, 2), dtype=np.float32)
    for start, end, text in VOIX:
        payload = {"text": text, "model_id": MODEL,
                   "voice_settings": {"stability": 0.4, "similarity_boost": 0.8, "style": 0.45,
                                      "use_speaker_boost": True}}
        mp3 = post(f"/text-to-speech/{VOICE}?output_format=mp3_44100_128", payload,
                   cache_name(f"voix_{VOICE}", payload))
        a = trim_silence(decode(mp3))
        slot = end - start
        tempo = 1.0
        if len(a) / SR > slot:  # trop long pour sa scène : on accélère légèrement (max x1,25)
            tempo = min(1.25, len(a) / SR / slot)
            a = trim_silence(decode(mp3, tempo))
        print(f"voix  {start:5.2f}s  {len(a)/SR:4.2f}s (créneau {slot:.2f}s, x{tempo:.2f})  {text}")
        place(voix, a, start, fade=0.01)
    save(os.path.join(HERE, "voix_off.wav"), voix, 0.95)

    sfx = np.zeros((n, 2), dtype=np.float32)
    for start, dur, gain, prompt in BRUITAGES:
        payload = {"text": prompt, "duration_seconds": max(0.5, round(dur, 2)), "prompt_influence": 0.5}
        mp3 = post("/sound-generation", payload, cache_name("sfx", payload))
        a = decode(mp3)[: int(dur * SR)]
        print(f"sfx   {start:5.2f}s  {dur:4.2f}s  {prompt[:60]}")
        place(sfx, a, start, gain, fade=0.08)
    save(os.path.join(HERE, "bruitages.wav"), sfx, 0.9)
    print("OK -> voix_off.wav, bruitages.wav")


if __name__ == "__main__":
    main()
