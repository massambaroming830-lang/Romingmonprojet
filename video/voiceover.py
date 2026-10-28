"""Voix off française (Kokoro TTS, voix ff_siwis) calée sur les scènes.
Usage : python3 voiceover.py <kokoro.onnx> <voices.bin> <espeak-ng> <sortie.wav>"""
import json, re, subprocess, sys, wave
import numpy as np
import onnxruntime as ort

MODEL, VOICES, ESPEAK, OUT = sys.argv[1:5]
CONFIG = sys.argv[5] if len(sys.argv) > 5 else 'kokoro_config.json'
SR = 24000
DUR = 23.0

# (début en secondes, texte, vitesse)
LINES = [
    (0.6,  "Bienvenue chez Ming Store !", 1.0),
    (4.25, "Import, export : votre partenaire du commerce international.", 1.08),
    (8.6,  "Vos marchandises de Chine, de Dubaï et de Turquie, livrées jusqu'aux pays africains.", 1.08),
    (14.55, "Le monde, à portée de votre business !", 1.05),
    (17.2, "Contactez-nous sur WhatsApp, Instagram et TikTok : Ming Store Entreprise !", 1.12),
]

vocab = json.load(open(CONFIG))['vocab']
voices = np.load(VOICES)
voice = voices['ff_siwis']
sess = ort.InferenceSession(MODEL, providers=['CPUExecutionProvider'])
names = {i.name for i in sess.get_inputs()}
tok_name = 'input_ids' if 'input_ids' in names else 'tokens'

def phonemes(text):
    # On découpe sur la ponctuation pour garder des pauses naturelles
    parts = re.split(r'([,.:;!?])', text)
    out = ''
    for p in parts:
        if p in ',.:;!?':
            out += p + ' '
            continue
        if not p.strip():
            continue
        ipa = subprocess.run([ESPEAK, '-v', 'fr', '-q', '--ipa'], input=p.strip(), capture_output=True, text=True).stdout
        ipa = re.sub(r'\([a-z]+\)', '', ipa).replace('\n', ' ').strip()
        out += ipa
    return ''.join(c for c in out.strip() if c in vocab)

def speak(text, speed):
    ph = phonemes(text)
    toks = [vocab[c] for c in ph]
    style = voice[len(toks) - 1]
    audio = sess.run(None, {tok_name: np.array([[0, *toks, 0]], dtype=np.int64),
                            'style': style.astype(np.float32),
                            'speed': np.array([speed], dtype=np.float32)})[0]
    a = np.asarray(audio, dtype=np.float32).reshape(-1)
    # coupe les silences au début et à la fin
    idx = np.where(np.abs(a) > 0.01)[0]
    return a[max(0, idx[0] - 200): idx[-1] + 2400] if len(idx) else a

mix = np.zeros(int(SR * DUR), dtype=np.float32)
for start, text, speed in LINES:
    a = speak(text, speed)
    i = int(start * SR)
    end = min(len(mix), i + len(a))
    print(f"{start:5.2f}s  durée {len(a)/SR:4.2f}s  fin {start + len(a)/SR:5.2f}s  {text}")
    mix[i:end] += a[: end - i]

mix /= max(1e-6, np.max(np.abs(mix))) / 0.95
pcm = (mix * 32767).astype(np.int16)
with wave.open(OUT, 'wb') as f:
    f.setnchannels(1); f.setsampwidth(2); f.setframerate(SR); f.writeframes(pcm.tobytes())
