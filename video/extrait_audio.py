"""Extrait MING Store : voix off (Kokoro TTS, voix ff_siwis) + musique, avec le minutage
de chaque mot pour caler l'animation sur la parole.
Usage : python3 extrait_audio.py <kokoro.onnx> <voices.bin> <espeak-ng>
Produit extrait.wav (mix final) et extrait_timings.js (minutage lu par extrait.html)."""
import json, re, subprocess, sys, wave
import numpy as np
import onnxruntime as ort

MODEL, VOICES, ESPEAK = sys.argv[1:4]
SR = 24000
START = 0.5      # la voix démarre après l'impact d'intro
GAP = 0.32       # respiration entre deux phrases
TAIL = 3.2       # écran final après la dernière phrase

# (scène, texte, vitesse) : une phrase = une scène de l'animation
LINES = [
    ('projet',   "Un projet d'import-export en tête ?", 1.0),
    ('pays',     "Vous voulez acheter en Chine, à Dubaï ou en Turquie ?", 1.08),
    ('endroit',  "Vous êtes au bon endroit !", 1.0),
    ('ming',     "Ming Store, votre partenaire du commerce international.", 1.08),
    ('afrique',  "On livre vos marchandises jusqu'aux pays africains.", 1.08),
    ('services', "Import, export, livraison :", 1.0),
    ('monde',    "le monde à portée de votre business !", 1.05),
    ('whatsapp', "Pour nous contacter, écrivez-nous sur WhatsApp,", 1.1),
    ('reseaux',  "ou sur Instagram et TikTok : Ming Store Entreprise !", 1.08),
]

vocab = json.load(open('kokoro_config.json'))['vocab']
voice = np.load(VOICES)['ff_siwis']
sess = ort.InferenceSession(MODEL, providers=['CPUExecutionProvider'])
names = {i.name for i in sess.get_inputs()}
tok_name = 'input_ids' if 'input_ids' in names else 'tokens'

def ipa(word):
    out = subprocess.run([ESPEAK, '-v', 'fr', '-q', '--ipa'], input=word, capture_output=True, text=True).stdout
    return re.sub(r'\([a-z]+\)', '', out).replace('\n', ' ').strip()

def speak(text, speed):
    # phonèmes mot par mot pour connaître le poids de chaque mot dans la phrase
    words = text.replace(' :', ':').replace(' ?', '?').replace(' !', '!').split()
    ph, weights = '', []
    for w in words:
        core = w.strip(',.:;!?')
        p = ''.join(c for c in ipa(core) if c in vocab)
        weights.append(len([c for c in p if c not in 'ˈˌː']))
        ph += p + (w[-1] + ' ' if w[-1] in ',.:;!?' else ' ')
    ph = ph.strip()
    toks = [vocab[c] for c in ph if c in vocab]
    audio = sess.run(None, {tok_name: np.array([[0, *toks, 0]], dtype=np.int64),
                            'style': voice[len(toks) - 1].astype(np.float32),
                            'speed': np.array([speed], dtype=np.float32)})[0]
    a = np.asarray(audio, dtype=np.float32).reshape(-1)
    idx = np.where(np.abs(a) > 0.01)[0]
    a = a[max(0, idx[0] - 200): idx[-1] + 1200]
    return a, [w.strip(',.;') for w in words], weights

def word_times(a, words, weights, t0):
    """Répartit les mots sur la durée parlée ; les pauses (virgules) sont repérées sur l'énergie."""
    hop = int(SR * 0.01)
    env = np.array([np.sqrt(np.mean(a[i:i + hop] ** 2)) for i in range(0, len(a), hop)])
    voiced = env > 0.012
    # segments voisés séparés par une pause de plus de 120 ms
    segs, s, quiet = [], None, 0
    for i, v in enumerate(voiced):
        if v:
            if s is None: s = i
            quiet = 0
        elif s is not None:
            quiet += 1
            if quiet > 12:
                segs.append((s, i - quiet + 1)); s, quiet = None, 0
    if s is not None: segs.append((s, len(voiced)))
    # un groupe de mots par segment, en coupant à la ponctuation interne
    groups, cur = [], []
    for k, w in enumerate(words):
        cur.append(k)
        if w[-1] in ',:' and k < len(words) - 1: groups.append(cur); cur = []
    groups.append(cur)
    if len(segs) != len(groups):
        segs, groups = [(segs[0][0], segs[-1][1])], [list(range(len(words)))]
    out = []
    for (s0, s1), g in zip(segs, groups):
        tot = sum(weights[k] for k in g)
        t = s0 * 0.01
        for k in g:
            d = (s1 - s0) * 0.01 * weights[k] / tot
            out.append({'w': words[k], 's': round(t0 + t, 3), 'e': round(t0 + t + d, 3)})
            t += d
    return out

clips, timeline, t = [], [], START
for scene, text, speed in LINES:
    a, words, weights = speak(text, speed)
    d = len(a) / SR
    timeline.append({'scene': scene, 'text': text, 's': round(t, 3), 'e': round(t + d, 3),
                     'words': word_times(a, words, weights, t)})
    clips.append((t, a))
    print(f"{t:6.2f}s → {t + d:6.2f}s  {text}")
    t += d + GAP
DUR = round(t - GAP + TAIL, 2)

voice_mix = np.zeros(int(SR * DUR), dtype=np.float32)
for at, a in clips:
    i = int(at * SR); voice_mix[i:i + len(a)] += a
voice_mix /= np.max(np.abs(voice_mix)) / 0.95

# ---------- Musique : même univers que la vidéo principale, plus discrète sous la voix ----------
MSR = 44100
N = int(MSR * DUR)
tt_all = np.arange(N) / MSR
music = np.zeros(N)
rng = np.random.default_rng(7)
beat = 0.5

def add(sig, at, gain=1.0):
    i = int(at * MSR)
    if i >= N: return
    sig = sig[: N - i]; music[i:i + len(sig)] += sig * gain

def env_t(d): return np.arange(int(MSR * d)) / MSR
def kick():
    tt = env_t(0.45); f = 50 + 110 * np.exp(-tt * 30)
    return np.sin(2 * np.pi * np.cumsum(f) / MSR) * np.exp(-tt * 7)
def hat():
    n = np.diff(rng.standard_normal(int(MSR * 0.06)), prepend=0)
    return n * np.exp(-np.arange(len(n)) / MSR * 70) * 0.5
def whoosh(d=0.6):
    n = rng.standard_normal(int(MSR * d)); out = np.zeros_like(n); y = 0
    a = np.linspace(0.02, 0.35, len(n))
    for k in range(len(n)): y += a[k] * (n[k] - y); out[k] = y
    return out * np.sin(np.linspace(0, np.pi, len(n))) ** 2 * 1.6
def impact():
    tt = env_t(1.6); return np.sin(2 * np.pi * (40 + 60 * np.exp(-tt * 8)) * tt) * np.exp(-tt * 2.5)
def bass(freq, d):
    tt = env_t(d); s = np.sign(np.sin(2 * np.pi * freq * tt)) * 0.3 + np.sin(2 * np.pi * freq * tt)
    return s * np.minimum(1, tt * 40) * np.exp(-tt * 1.2)
def pad(freqs, d):
    tt = env_t(d); s = sum(np.sin(2 * np.pi * f * tt + np.sin(2 * np.pi * 0.3 * tt)) for f in freqs)
    return s * np.minimum(1, tt / 0.8) * np.minimum(1, (d - tt) / 0.8) / len(freqs)

add(impact(), 0.0, 0.9)
chords = [[220, 261.6, 329.6], [174.6, 220, 261.6], [261.6, 329.6, 392], [196, 246.9, 293.7]]
roots = [55, 43.65, 65.4, 49]
for k in range(int(DUR / 2) + 1):
    add(pad(chords[k % 4], 2.2), k * 2, 0.18)
    if k >= 1:
        for b in range(4): add(bass(roots[k % 4], beat * 0.9), k * 2 + b * beat, 0.3)
for i in range(int(DUR / beat)):
    at = i * beat
    if at < 2 or at > DUR - 1.5: continue
    add(kick(), at, 0.8); add(hat(), at + beat / 2, 0.5)
for sc in timeline[1:]:
    add(whoosh(), sc['s'] - 0.45, 0.4)
add(impact(), timeline[-1]['s'], 0.5)
music *= np.clip((DUR - tt_all) / 1.2, 0, 1)
music = np.tanh(music * 1.2); music /= np.max(np.abs(music))

# voix rééchantillonnée à 44,1 kHz + ducking de la musique quand on parle
v = np.interp(np.arange(N) / MSR, np.arange(len(voice_mix)) / SR, voice_mix)
level = np.convolve(np.abs(v), np.ones(4410) / 4410, mode='same')
duck = 1 - 0.55 * np.clip(level / 0.05, 0, 1)
mix = v * 0.92 + music * 0.30 * duck
mix /= np.max(np.abs(mix)) / 0.97
pcm = (np.stack([mix, mix], axis=1) * 32767).astype(np.int16)
with wave.open('extrait.wav', 'wb') as f:
    f.setnchannels(2); f.setsampwidth(2); f.setframerate(MSR); f.writeframes(pcm.tobytes())

with open('extrait_timings.js', 'w') as f:
    f.write('// Généré par extrait_audio.py : minutage de chaque phrase et de chaque mot (secondes).\n')
    f.write(f'window.DURATION = {DUR};\nwindow.TIMINGS = ')
    json.dump(timeline, f, ensure_ascii=False, indent=1)
    f.write(';\n')
print('durée totale', DUR)
