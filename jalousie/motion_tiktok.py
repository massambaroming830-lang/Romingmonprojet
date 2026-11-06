"""Motion TikTok (1080x1920, 15 s) « À bas la jalousie » : Jérémie en avant, effets caméra réels
(Ken Burns, flashs, secousses, flou de mouvement, grain pellicule, light leak, particules lumineuses),
voix off naturelle (voix_kokoro.py) et une séquence « Christelle Business Service Dubaï soutient l'équipe JS Production ».

Usage :
  python3 musique.py musique_tiktok.wav 26 17.5 4.5 8.5 12.5 17.5
  python3 voix_kokoro.py kokoro-v1.0.onnx voices-v1.0.bin   -> voix_tiktok.wav
  python3 motion_tiktok.py                                   -> Jeremie_A_bas_la_jalousie_motion_TikTok.mp4
  python3 motion_tiktok.py --remix   (remplace seulement le son, ex. après avoir changé fond_musique.m4a)
"""
import math, os, subprocess
import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageFont, ImageEnhance

HERE = os.path.dirname(os.path.abspath(__file__))
W, H, FPS, DUR = 1080, 1920, 30, 26.0
OUT = os.path.join(HERE, "Jeremie_A_bas_la_jalousie_motion_TikTok.mp4")
F_BLACK = "/usr/share/fonts/opentype/inter/InterDisplay-Black.otf"
F_BOLD = "/usr/share/fonts/opentype/inter/InterDisplay-Bold.otf"
F_ITAL = "/usr/share/fonts/opentype/inter/Inter-BlackItalic.otf"
RED, YELLOW, WHITE = (228, 32, 42), (255, 214, 10), (255, 255, 255)
CUTS = [4.5, 8.5, 12.5, 17.5]  # changements de scène
REVEAL = 17.5  # impact + affiche
rng = np.random.default_rng(7)

# ---------- sources ----------
poster = Image.open(os.path.join(HERE, "affiche.jpg")).convert("RGB")
jeremie = poster.crop((400, 0, 760, 359)).resize((1440, 1436), Image.LANCZOS)
jeremie = jeremie.filter(ImageFilter.UnsharpMask(radius=3, percent=90, threshold=2))
christelle = Image.open(os.path.join(HERE, "christelle_mafuila.jpg")).convert("RGB")
christelle_dubai = Image.open(os.path.join(HERE, "christelle_dubai.jpg")).convert("RGB")


def cover(img, w, h):
    s = max(w / img.width, h / img.height)
    im = img.resize((math.ceil(img.width * s), math.ceil(img.height * s)), Image.LANCZOS)
    x, y = (im.width - w) // 2, (im.height - h) // 2
    return im.crop((x, y, x + w, y + h))


BG_POSTER = ImageEnhance.Brightness(cover(poster, W, H).filter(ImageFilter.GaussianBlur(40))).enhance(0.55)
BG_CHRIS = ImageEnhance.Brightness(cover(christelle_dubai, W, H).filter(ImageFilter.GaussianBlur(45))).enhance(0.45)
POSTER_HD = poster.resize((poster.width * 2, poster.height * 2), Image.LANCZOS).filter(
    ImageFilter.UnsharpMask(radius=2, percent=80))


def kenburns(img, t, dur, z0, z1, cx0=0.5, cy0=0.5, cx1=0.5, cy1=0.5, w=W, h=H):
    """Recadrage animé (zoom + panoramique) d'une image vers w x h."""
    p = ease_io(min(1, max(0, t / dur)))
    z = z0 + (z1 - z0) * p
    cx, cy = cx0 + (cx1 - cx0) * p, cy0 + (cy1 - cy0) * p
    s = max(w / img.width, h / img.height) * z
    cw, ch = w / s, h / s
    x = min(max(0, cx * img.width - cw / 2), img.width - cw)
    y = min(max(0, cy * img.height - ch / 2), img.height - ch)
    return img.resize((w, h), Image.BICUBIC, box=(x, y, x + cw, y + ch))


# ---------- easing ----------
def clamp(x): return min(1.0, max(0.0, x))
def ease_out(x): x = clamp(x); return 1 - (1 - x) ** 3
def ease_io(x): x = clamp(x); return 3 * x * x - 2 * x * x * x
def ease_back(x):
    x = clamp(x); c = 1.9
    return 1 + (c + 1) * (x - 1) ** 3 + c * (x - 1) ** 2


# ---------- texte ----------
_cache = {}


def text_img(txt, font, size, fill=WHITE, shadow=True, stroke=0):
    key = (txt, font, size, fill, shadow, stroke)
    if key in _cache:
        return _cache[key]
    f = ImageFont.truetype(font, size)
    l, t, r, b = f.getbbox(txt, stroke_width=stroke)
    pad = 40
    im = Image.new("RGBA", (r - l + 2 * pad, b - t + 2 * pad), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    if shadow:
        sh = Image.new("RGBA", im.size, (0, 0, 0, 0))
        ImageDraw.Draw(sh).text((pad - l + 6, pad - t + 8), txt, font=f, fill=(0, 0, 0, 170), stroke_width=stroke)
        im = Image.alpha_composite(im, sh.filter(ImageFilter.GaussianBlur(10)))
        d = ImageDraw.Draw(im)
    d.text((pad - l, pad - t), txt, font=f, fill=fill, stroke_width=stroke, stroke_fill=(0, 0, 0))
    _cache[key] = im
    return im


def paste(canvas, im, cx, cy, scale=1.0, alpha=1.0, angle=0.0):
    if alpha <= 0.01 or scale <= 0.01:
        return
    if abs(scale - 1) > 1e-3:
        im = im.resize((max(1, int(im.width * scale)), max(1, int(im.height * scale))), Image.BICUBIC)
    if angle:
        im = im.rotate(angle, Image.BICUBIC, expand=True)
    if alpha < 1:
        im = im.copy(); im.putalpha(im.getchannel("A").point(lambda v: int(v * alpha)))
    canvas.alpha_composite(im, (int(cx - im.width / 2), int(cy - im.height / 2)))


def pop(canvas, txt, font, size, cx, cy, t, start, fill=WHITE, slide=0):
    """Apparition : petit rebond d'échelle + fondu (+ glissement vertical)."""
    k = (t - start) / 0.35
    if k <= 0:
        return
    paste(canvas, text_img(txt, font, size, fill), cx, cy + slide * (1 - ease_out(k)),
          scale=0.6 + 0.4 * ease_back(k), alpha=clamp(k * 2.5))


def typing(canvas, txt, font, size, cx, cy, t, start, per=0.045, fill=WHITE):
    n = int((t - start) / per)
    if n <= 0:
        return
    full = text_img(txt, font, size, fill)
    part = text_img(txt[:min(n, len(txt))], font, size, fill)
    canvas.alpha_composite(part, (int(cx - full.width / 2), int(cy - full.height / 2)))


def bar(canvas, cx, cy, w, h, color, t, start, radius=18):
    k = ease_out((t - start) / 0.3)
    if k <= 0:
        return
    ww = int(w * k)
    d = ImageDraw.Draw(canvas)
    d.rounded_rectangle((cx - ww // 2, cy - h // 2, cx + ww // 2, cy + h // 2), radius, fill=color)


def vgrad(alpha_top, alpha_bottom, start=0.0):
    a = np.clip((np.linspace(0, 1, H) - start) / max(1e-6, 1 - start), 0, 1)
    a = alpha_top + (alpha_bottom - alpha_top) * a
    g = np.zeros((H, W, 4), np.uint8)
    g[..., 3] = (a[:, None] * 255).astype(np.uint8)
    return Image.fromarray(g, "RGBA")


SHADE_BOTTOM = vgrad(0.0, 0.92, 0.45)
SHADE_ALL = vgrad(0.35, 0.75)

# ---------- scènes ----------


def scene_intro(t):  # 0 - 4.5 : Jérémie, gros plan qui se rapproche
    c = kenburns(jeremie, t, 4.8, 1.02, 1.3, 0.45, 0.5, 0.38, 0.36).convert("RGBA")
    c.alpha_composite(SHADE_BOTTOM)
    pop(c, "JÉRÉMIE", F_BLACK, 190, W / 2, 1340, t, 0.35, slide=80)
    pop(c, "ET SON GROUPE", F_BOLD, 64, W / 2, 1500, t, 0.75)
    bar(c, W // 2, 1640, 430, 92, RED, t, 1.15)
    pop(c, "EN SPECTACLE", F_ITAL, 56, W / 2, 1636, t, 1.25)
    pop(c, "PRÉPAREZ-VOUS À RIRE", F_BLACK, 62, W / 2, 1770, t, 2.4, fill=YELLOW)
    return c


def scene_title(t):  # 4.5 - 8.5 : le titre
    bg = kenburns(jeremie, t, 4.0, 1.6, 1.75, 0.35, 0.3, 0.33, 0.28).filter(ImageFilter.GaussianBlur(6))
    bg = Image.blend(bg, Image.new("RGB", (W, H), (120, 10, 20)), 0.45).convert("RGBA")
    bg.alpha_composite(SHADE_ALL)
    pop(bg, "À BAS", F_BLACK, 250, W / 2, 640, t, 0.1, slide=-60)
    bar(bg, W // 2, 900, 330, 160, YELLOW, t, 0.45, radius=10)
    pop(bg, "LA", F_BLACK, 150, W / 2, 895, t, 0.55, fill=(20, 20, 20))
    jw = text_img("JALOUSIE", F_BLACK, 170).width - 80
    pop(bg, "JALOUSIE", F_BLACK, 170, W / 2 - 40, 1140, t, 0.85, slide=60)
    pop(bg, "!", F_BLACK, 300, W / 2 - 40 + jw / 2 + 50, 1115, t, 1.25, fill=RED)
    pop(bg, "LE SPECTACLE ÉVÉNEMENT", F_BOLD, 56, W / 2, 1360, t, 2.0)
    return bg


def scene_date(t):  # 8.5 - 12.5 : date + lieu, Jérémie en plan large
    c = kenburns(jeremie, t, 4.0, 1.0, 1.08, 0.5, 0.55, 0.52, 0.5).convert("RGBA")
    c.alpha_composite(SHADE_BOTTOM)
    k = ease_out((t - 0.15) / 0.35)
    if k > 0:
        d = ImageDraw.Draw(c)
        bw = int(880 * k)
        d.rounded_rectangle((W // 2 - bw // 2, 1210, W // 2 + bw // 2, 1390), 26, outline=RED, width=10,
                            fill=(0, 0, 0, 110))
    typing(c, "20.12.2026", F_BLACK, 128, W / 2, 1298, t, 0.35, per=0.06)
    pop(c, "LA MADELEINE", F_BLACK, 100, W / 2, 1520, t, 1.0, slide=40)
    pop(c, "BRUXELLES", F_BOLD, 64, W / 2, 1625, t, 1.3)
    pop(c, "THÉÂTRE", F_BOLD, 40, W / 2, 1440, t, 0.9, fill=(255, 220, 200))
    return c


_cards = {}


def card(img, pw=560, focus=0.5):
    """Photo encadrée de blanc, coins arrondis, ombre portée."""
    key = (id(img), pw)
    if key in _cards:
        return _cards[key]
    ph = int(pw * 1.33)
    s = max(pw / img.width, ph / img.height)
    im = img.resize((math.ceil(img.width * s), math.ceil(img.height * s)), Image.LANCZOS)
    y = int(min(max(0, focus * im.height - ph / 2), im.height - ph))
    photo = im.crop(((im.width - pw) // 2, y, (im.width - pw) // 2 + pw, y + ph))
    frame = Image.new("RGBA", (pw + 28, ph + 28), (255, 255, 255, 255))
    frame.paste(photo, (14, 14))
    mask = Image.new("L", frame.size, 0)
    ImageDraw.Draw(mask).rounded_rectangle((0, 0, *frame.size), 30, fill=255)
    frame.putalpha(mask)
    sh = Image.new("RGBA", (frame.width + 120, frame.height + 120), (0, 0, 0, 0))
    sh.paste((0, 0, 0, 150), (60, 75, 60 + frame.width, 75 + frame.height), mask)
    sh = sh.filter(ImageFilter.GaussianBlur(25))
    sh.alpha_composite(frame, (60, 60))
    _cards[key] = sh
    return sh


def scene_christelle(t):  # 12.5 - 17.5 : soutien (séquence secondaire), deux photos
    c = BG_CHRIS.copy().convert("RGBA")
    zoom = 1 + 0.05 * t / 5
    k1 = ease_out(t / 0.5)
    paste(c, card(christelle), W / 2 - 165 + 40 * (1 - k1), 760 + 300 * (1 - k1),
          scale=zoom * 0.78 * (0.85 + 0.15 * k1), alpha=clamp(k1 * 2), angle=-7 + 2 * k1)
    k2 = ease_out((t - 1.4) / 0.55)
    if k2 > 0:  # la photo de Dubaï arrive par la droite, devant
        paste(c, card(christelle_dubai, focus=0.42), W / 2 + 175 + 420 * (1 - k2), 820,
              scale=zoom * 0.8, alpha=clamp(k2 * 2), angle=6 - 14 * (1 - k2))
    pop(c, "AVEC LE SOUTIEN DE", F_BOLD, 44, W / 2, 1385, t, 0.35)
    pop(c, "Christelle", F_BLACK, 96, W / 2, 1470, t, 0.5, slide=40)
    pop(c, "BUSINESS SERVICE DUBAÏ", F_BLACK, 58, W / 2, 1568, t, 0.8, fill=YELLOW)
    bar(c, W // 2, 1690, 760, 96, RED, t, 1.1)
    pop(c, "soutient l'équipe JS PRODUCTION", F_BOLD, 44, W / 2, 1687, t, 1.2)
    return c


def scene_poster(t):  # 17.5 - 26.0 : révélation de l'affiche + appel à l'action
    c = kenburns(BG_POSTER, t, 8.5, 1.0, 1.15).convert("RGBA")
    pw = 1040
    ph = int(pw * poster.height / poster.width)
    fg = kenburns(POSTER_HD, t, 8.5, 1.0, 1.12, w=pw, h=ph).convert("RGBA")
    k = ease_back(t / 0.5)
    paste(c, fg, W / 2, H / 2 - 40, scale=0.75 + 0.25 * k, alpha=clamp(t / 0.15))
    pop(c, "20.12.2026", F_BLACK, 120, W / 2, 470, t, 0.5, slide=-40)
    pop(c, "LA MADELEINE · BRUXELLES", F_BOLD, 50, W / 2, 575, t, 0.8)
    if t > 1.3:
        pulse = 1 + 0.035 * math.sin((t - 1.3) * 2 * math.pi * 1.6)
        btn = Image.new("RGBA", (700, 120), (0, 0, 0, 0))
        ImageDraw.Draw(btn).rounded_rectangle((0, 0, 699, 119), 60, fill=RED)
        lbl = text_img("RÉSERVEZ VOS PLACES", F_BLACK, 52, shadow=False)
        btn.alpha_composite(lbl, ((700 - lbl.width) // 2, (120 - lbl.height) // 2))
        paste(c, btn, W / 2, 1420, scale=pulse * (0.7 + 0.3 * ease_back((t - 1.3) / 0.35)),
              alpha=clamp((t - 1.3) * 4))
    pop(c, "LES PLACES PARTENT VITE", F_BLACK, 50, W / 2, 1290, t, 0.4, fill=YELLOW)
    pop(c, "Avec le soutien de Christelle Business Service Dubaï · JS Production", F_BOLD, 30, W / 2, 1580, t, 1.8)
    pop(c, "En collaboration avec MING Store Entreprise", F_BOLD, 32, W / 2, 1628, t, 2.2, fill=(255, 225, 200))
    pop(c, "ON VOUS ATTEND !", F_BLACK, 90, W / 2, 1720, t, 4.4, slide=50)
    return c


SCENES = [(0.0, scene_intro), (4.5, scene_title), (8.5, scene_date), (12.5, scene_christelle), (17.5, scene_poster)]

# ---------- effets « caméra réelle » ----------
GRAIN = [rng.normal(0, 5, (H // 2, W // 2)).astype(np.float32) for _ in range(6)]
yy, xx = np.mgrid[0:H, 0:W].astype(np.float32)
VIGN = (1 - 0.55 * (((xx - W / 2) / (W * 0.75)) ** 2 + ((yy - H / 2) / (H * 0.7)) ** 2)).clip(0.35, 1)[..., None]
LEAK_COL = np.array([255, 140, 50], np.float32)


def light_leak(t):
    """Fuite de lumière chaude qui traverse l'image (plus forte aux transitions)."""
    cx = W * (-0.3 + 1.6 * ((t * 0.09) % 1))
    cy = H * (0.25 + 0.2 * math.sin(t * 0.7))
    near = max([math.exp(-((t - c) / 0.35) ** 2) for c in CUTS])
    strength = 0.10 + 0.45 * near
    d = ((xx - cx) / (W * 0.55)) ** 2 + ((yy - cy) / (H * 0.35)) ** 2
    return (np.exp(-d)[..., None] * strength) * LEAK_COL


PARTS = [(rng.uniform(0, W), rng.uniform(0, H), rng.uniform(6, 26), rng.uniform(20, 70), rng.uniform(0, 6.28))
         for _ in range(28)]


def particles(img, t):
    layer = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    d = ImageDraw.Draw(layer)
    for x, y, r, v, ph in PARTS:
        py = (y - v * t) % H
        px = x + 25 * math.sin(t + ph)
        a = int(70 + 60 * math.sin(t * 2 + ph))
        d.ellipse((px - r, py - r, px + r, py + r), fill=(255, 220, 160, max(0, a)))
    img.alpha_composite(layer.filter(ImageFilter.GaussianBlur(6)))


def scene_frame(t):
    for i in range(len(SCENES) - 1, -1, -1):
        if t >= SCENES[i][0]:
            return SCENES[i][1](t - SCENES[i][0])


def render(fi):
    t = fi / FPS
    img = scene_frame(t)
    # transition : fondu enchaîné court + flou de mouvement vertical (whip)
    for c in CUTS:
        if c - 0.12 <= t < c:
            nxt = scene_frame(c + 0.001)
            img = Image.blend(img, nxt, (t - (c - 0.12)) / 0.12)
    particles(img, t)
    near = min(abs(t - c) for c in CUTS)
    if near < 0.12:
        img = img.filter(ImageFilter.BoxBlur(int(14 * (1 - near / 0.12)) + 1))
    # secousse caméra (impact) + légère respiration handheld
    sh = sum(max(0, 1 - (t - c) / 0.4) * (28 if c == REVEAL else 12) for c in CUTS if 0 <= t - c < 0.4)
    dx = math.sin(t * 1.3) * 5 + sh * math.sin(t * 90)
    dy = math.cos(t * 1.1) * 5 + sh * math.cos(t * 77)
    img = img.convert("RGB").transform((W, H), Image.AFFINE, (1, 0, -dx, 0, 1, -dy), Image.BICUBIC)
    if sh:  # bords noirs masqués par un léger zoom
        img = img.resize((int(W * 1.04), int(H * 1.04)), Image.BICUBIC).crop(
            (int(W * 0.02), int(H * 0.02), int(W * 0.02) + W, int(H * 0.02) + H))
    a = np.asarray(img, np.float32)
    a = a + light_leak(t)
    a = a * VIGN
    # flash blanc aux coupes
    fl = max([math.exp(-((t - c) / 0.07) ** 2) * (1.0 if c == REVEAL else 0.75) for c in CUTS])
    a = a + (255 - a) * fl
    g = np.repeat(np.repeat(GRAIN[fi % len(GRAIN)], 2, 0), 2, 1)[..., None]
    a = a + g
    # étalonnage : contraste doux et tons chauds
    a = (a - 128) * 1.06 + 128
    a[..., 0] *= 1.03; a[..., 2] *= 0.96
    # fondu final
    if t > DUR - 0.6:
        a *= (DUR - t) / 0.6
    if t < 0.25:
        a *= t / 0.25
    return np.clip(a, 0, 255).astype(np.uint8)


def audio_filter():
    """Musique de fond (fond_musique.m4a si présent, sinon musique_tiktok.wav) baissée sous la voix."""
    fond = os.path.join(HERE, "fond_musique.m4a")
    if os.path.exists(fond):  # titre réel, très fort : on le baisse et on creuse la zone de la voix
        music, mvol = fond, ("volume=0.32,equalizer=f=2500:t=q:w=1.2:g=-5,afade=t=in:st=0:d=0.4")
    else:
        music, mvol = os.path.join(HERE, "musique_tiktok.wav"), "volume=0.75"
    voix = os.path.join(HERE, "voix_tiktok.wav")
    af = (f"[1:a]aformat=sample_rates=44100:channel_layouts=stereo,atrim=0:{DUR},{mvol}[m];"
          f"[2:a]aformat=sample_rates=44100:channel_layouts=stereo,highpass=f=80,"
          f"acompressor=threshold=0.1:ratio=3:attack=5:release=120,volume=1.6,asplit=2[v][k];"
          f"[m][k]sidechaincompress=threshold=0.03:ratio=6:attack=15:release=450[mb];"
          f"[mb][v]amix=inputs=2:normalize=0,alimiter=limit=0.95,afade=t=out:st={DUR-1.5}:d=1.5[a]")
    return ["-i", music, "-i", voix, "-filter_complex", af]


def remix():
    """Remplace seulement le son de la vidéo déjà rendue (pas de nouveau rendu des images)."""
    tmp = OUT + ".tmp.mp4"
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", OUT, *audio_filter(), "-map", "0:v", "-map", "[a]",
                    "-c:v", "copy", "-c:a", "aac", "-b:a", "192k", "-movflags", "+faststart",
                    "-t", str(DUR), tmp], check=True)
    os.replace(tmp, OUT)
    print(f"OK (son remplacé) -> {OUT}")


def main():
    cmd = ["ffmpeg", "-v", "error", "-y", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{W}x{H}",
           "-r", str(FPS), "-i", "-", *audio_filter(),
           "-map", "0:v", "-map", "[a]",
           "-c:v", "libx264", "-crf", "20", "-maxrate", "12M", "-bufsize", "24M", "-preset", "slow", "-pix_fmt", "yuv420p",
           "-c:a", "aac", "-b:a", "192k", "-movflags", "+faststart", "-t", str(DUR), OUT]
    p = subprocess.Popen(cmd, stdin=subprocess.PIPE)
    n = int(DUR * FPS)
    for fi in range(n):
        p.stdin.write(render(fi).tobytes())
        if fi % 60 == 0:
            print(f"{fi}/{n}", flush=True)
    p.stdin.close()
    p.wait()
    print(f"OK -> {OUT}")


if __name__ == "__main__":
    import sys
    if len(sys.argv) > 2 and sys.argv[1] == "--frame":  # aperçu d'une image : --frame 3.5 out.png
        Image.fromarray(render(int(float(sys.argv[2]) * FPS))).save(sys.argv[3])
    elif "--remix" in sys.argv:  # nouveau son sur la vidéo existante
        remix()
    else:
        main()
