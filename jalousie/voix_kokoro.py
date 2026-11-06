"""Voix off naturelle (Kokoro TTS, voix française ff_siwis) pour le motion TikTok « À bas la jalousie ».

La phonétique (API) est écrite à la main : pas besoin d'espeak-ng.
Usage : python3 voix_kokoro.py <kokoro-v1.0.onnx> <voices-v1.0.bin> [voix_tiktok.wav | kinshasa | aigle]
Modèle : https://github.com/thewh1teagle/kokoro-onnx/releases/tag/model-files-v1.0
"""
import json, os, sys, wave
import numpy as np
import onnxruntime as ort

HERE = os.path.dirname(os.path.abspath(__file__))
MODEL, VOICES = sys.argv[1:3]
OUT = sys.argv[3] if len(sys.argv) > 3 else os.path.join(HERE, "voix_tiktok.wav")
SR = 24000
DUR = 26.0
VOICE = os.environ.get("KOKORO_VOICE", "ff_siwis")

# (début s, texte affiché, phonétique, vitesse) — calé sur motion_tiktok.py
LINES = [
    (0.45, "Il est de retour… Jérémie et son groupe !",
     "il ɛ də ʁətˈuʁ… ʒeʁemˈi e sɔ̃ ɡʁˈup!", 0.95),
    (2.75, "Préparez-vous à rire comme jamais.",
     "pʁepaʁe vˈu a ʁˈiʁ kɔm ʒamˈɛ.", 1.0),
    (4.75, "Le spectacle événement : À bas la jalousie !",
     "lə spɛktˈakl evɛnmˈɑ̃: a bˈa la ʒaluzˈi!", 0.95),
    (8.75, "Rendez-vous le vingt décembre, au théâtre La Madeleine, à Bruxelles.",
     "ʁɑ̃devˈu lə vˈɛ̃ desˈɑ̃bʁ, o teˈatʁ la madlˈɛn, a bʁysˈɛl.", 1.0),
    (12.65, "Avec le soutien de Christelle Business Service Dubaï, et de l'équipe JS Production.",
     "avɛk lə sutjˈɛ̃ də kʁistˈɛl, bizniss sɛʁvˈis dybˈaj, e də lekˈip ʒiˈɛs pʁɔdyksjˈɔ̃.", 1.05),
    (17.85, "Les places partent très vite… Réservez dès maintenant !",
     "le plˈas paʁt tʁɛ vˈit… ʁezɛʁvˈe dɛ mɛ̃tnˈɑ̃!", 1.0),
    (21.9, "À bas la jalousie ! On vous attend !",
     "a bˈa la ʒaluzˈi! ɔ̃ vuz atˈɑ̃!", 0.95),
]

# Version Kinshasa (motion_kinshasa.py) : python3 voix_kokoro.py <onnx> <voices> kinshasa
LINES_KINSHASA = [
    (0.5, "Réservez votre place !",
     "ʁezɛʁvˈe vɔtʁə plˈas!", 0.95),
    (4.55, "Jérémie Shabani et son groupe, en spectacle !",
     "ʒeʁemˈi ʃabanˈi, e sɔ̃ ɡʁˈup, ɑ̃ spɛktˈakl!", 0.95),
    (7.9, "À bas la jalousie ! Dimanche six décembre, à partir de seize heures.",
     "a bˈa la ʒaluzˈi! dimˈɑ̃ʃ si desˈɑ̃bʁ, a paʁtˈiʁ də sɛzˈœʁ.", 1.0),
    (11.8, "Au Centre culturel de Kinshasa, salle Grand Tambour.",
     "o sˈɑ̃tʁ kyltyʁˈɛl də kinʃasˈa, sal ɡʁɑ̃ tɑ̃bˈuʁ.", 1.0),
    (14.85, "Les places : dix, vingt, cinquante et cent dollars.",
     "le plˈas: dˈis, vˈɛ̃, sɛ̃kˈɑ̃t, e sˈɑ̃ dɔlˈaʁ.", 1.0),
    (17.85, "Jérémie, à Kinshasa : on vous attend !",
     "ʒeʁemˈi, a kinʃasˈa: ɔ̃ vuz atˈɑ̃!", 0.95),
    (21.75, "Ben Oracle Business vous attend. Réservez dès maintenant !",
     "bɛn ɔʁˈakl, bˈiznɛs, vuz atˈɑ̃. ʁezɛʁvˈe dɛ mɛ̃tnˈɑ̃!", 1.0),
]
# Vidéo de l'aigle Kinshasa -> Angola -> Bruxelles (montage.py, 14,4 s) : python3 voix_kokoro.py <onnx> <voices> aigle
LINES_AIGLE = [
    (0.35, "De Kinshasa…", "də kinʃasˈa…", 0.9),
    (3.0, "en passant par l'Angola…", "ɑ̃ pasˈɑ̃ paʁ lɑ̃ɡɔlˈa…", 0.95),
    (5.6, "il arrive enfin à Bruxelles !", "il aʁˈiv ɑ̃fˈɛ̃, a bʁysˈɛl!", 0.95),
    (8.1, "Jérémie et son groupe présentent…", "ʒeʁemˈi e sɔ̃ ɡʁˈup pʁezˈɑ̃t…", 1.0),
    (10.2, "À bas la jalousie ! Le vingt décembre, à La Madeleine. Réservez vos places !",
     "a bˈa la ʒaluzˈi! lə vˈɛ̃ desˈɑ̃bʁ, a la madlˈɛn. ʁezɛʁvˈe vo plˈas!", 1.05),
]
if len(sys.argv) > 3 and sys.argv[3] == "aigle":
    LINES, OUT, DUR = LINES_AIGLE, os.path.join(HERE, "voix_off.wav"), 14.4
if len(sys.argv) > 3 and sys.argv[3] == "kinshasa":
    LINES, OUT = LINES_KINSHASA, os.path.join(HERE, "voix_kinshasa.wav")

vocab = json.load(open(os.path.join(HERE, "..", "video", "kokoro_config.json")))["vocab"]
voice = np.load(VOICES)[VOICE]
sess = ort.InferenceSession(MODEL, providers=["CPUExecutionProvider"])


def speak(ipa, speed):
    missing = {c for c in ipa if c not in vocab}
    if missing:
        sys.exit(f"Caractères phonétiques inconnus : {missing}")
    toks = [vocab[c] for c in ipa]
    a = sess.run(None, {"tokens": np.array([[0, *toks, 0]], dtype=np.int64),
                        "style": voice[len(toks) - 1].astype(np.float32),
                        "speed": np.array([speed], dtype=np.float32)})[0]
    a = np.asarray(a, np.float32).reshape(-1)
    idx = np.where(np.abs(a) > 0.01)[0]
    return a[max(0, idx[0] - 240): idx[-1] + 3600] if len(idx) else a


mix = np.zeros(int(SR * DUR), np.float32)
prev_end = 0.0
for start, text, ipa, speed in LINES:
    a = speak(ipa, speed)
    n = min(len(a), len(mix) - int(start * SR))
    fade = np.ones(n, np.float32); k = min(1200, n // 4)
    fade[-k:] = np.linspace(1, 0, k)
    mix[int(start * SR): int(start * SR) + n] += a[:n] * fade
    end = start + len(a) / SR
    warn = "  <-- chevauche la phrase précédente" if start < prev_end else ""
    print(f"{start:5.2f}s -> {end:5.2f}s  ({len(a)/SR:4.2f}s)  {text}{warn}")
    prev_end = end

mix /= max(1e-6, np.abs(mix).max()) / 0.95
with wave.open(OUT, "wb") as f:
    f.setnchannels(1); f.setsampwidth(2); f.setframerate(SR)
    f.writeframes((mix * 32767).astype(np.int16).tobytes())
print(f"OK -> {OUT}")
