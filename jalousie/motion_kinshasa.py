"""Motion TikTok (1080x1920, 26 s) « À bas la jalousie » — Kinshasa, dimanche 6 décembre 2026.

Style « interface » épuré : fonds clairs à halo, billet animé, texte cinétique (mots qui passent du flou au net),
écrans pleine couleur avec texte lettre par lettre, cartes-infos qui s'empilent, cartes photo à gros titre,
collage final. Couleurs de l'affiche (orange / jaune).

Usage :
  python3 voix_kokoro.py kokoro-v1.0.onnx voices-v1.0.bin kinshasa   -> voix_kinshasa.wav
  python3 motion_kinshasa.py                                          -> Jeremie_A_bas_la_jalousie_Kinshasa_TikTok.mp4
  python3 motion_kinshasa.py --frame 5.0 apercu.png                   (aperçu d'une image)
"""
import math, os, subprocess, sys
import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageFont

HERE = os.path.dirname(os.path.abspath(__file__))
W, H, FPS, DUR = 1080, 1920, 30, 26.0
OUT = os.path.join(HERE, "Jeremie_A_bas_la_jalousie_Kinshasa_TikTok.mp4")
FD = "/usr/share/fonts/opentype/inter/InterDisplay-"
BLACK, XBOLD, BOLD, SEMI, MED = (FD + s + ".otf" for s in ("Black", "ExtraBold", "Bold", "SemiBold", "Medium"))

INK = (30, 24, 22)
GREY = (120, 110, 104)
ORANGE = (243, 101, 18)
ORANGE2 = (255, 154, 31)
YELLOW = (255, 214, 31)
CREAM = (255, 247, 238)
DARK = (34, 14, 6)
WHITE = (255, 255, 255)

poster = Image.open(os.path.join(HERE, "affiche_kinshasa.jpg")).convert("RGB")  # 1170 x 1518
face = poster.crop((390, 380, 1050, 1010))           # Jérémie, gros plan
title_crop = poster.crop((0, 0, 1170, 560))          # haut de l'affiche (titre)

# ---------------- outils ----------------


def clamp(x): return min(1.0, max(0.0, x))
def ease_out(x): x = clamp(x); return 1 - (1 - x) ** 3
def ease_io(x): x = clamp(x); return 3 * x * x - 2 * x ** 3
def ease_back(x, c=1.7):
    x = clamp(x)
    return 1 + (c + 1) * (x - 1) ** 3 + c * (x - 1) ** 2


_font = {}


def font(path, size):
    k = (path, size)
    if k not in _font:
        _font[k] = ImageFont.truetype(path, size)
    return _font[k]


_txt = {}


def text(txt, path, size, fill=INK, blur=0, spacing=0):
    """Texte rendu dans une image RGBA (mis en cache, avec version floutée)."""
    k = (txt, path, size, fill, blur, spacing)
    if k in _txt:
        return _txt[k]
    if blur:
        im = text(txt, path, size, fill, 0, spacing)
        pad = blur * 3
        big = Image.new("RGBA", (im.width + 2 * pad, im.height + 2 * pad), (0, 0, 0, 0))
        big.paste(im, (pad, pad))
        im = big.filter(ImageFilter.GaussianBlur(blur))
    else:
        f = font(path, size)
        if spacing:
            ws = [f.getlength(ch) + spacing for ch in txt]
            wdt, (_, t, _, b) = int(sum(ws)) + 20, f.getbbox(txt)
            im = Image.new("RGBA", (wdt, b + 20), (0, 0, 0, 0))
            d, x = ImageDraw.Draw(im), 10
            for ch, w_ in zip(txt, ws):
                d.text((x, 10), ch, font=f, fill=fill); x += w_
        else:
            l, t, r, b = f.getbbox(txt)
            im = Image.new("RGBA", (r - l + 20, b + 20), (0, 0, 0, 0))
            ImageDraw.Draw(im).text((10 - l, 10), txt, font=f, fill=fill)
    _txt[k] = im
    return im


def put(canvas, im, x, y, anchor="lt", alpha=1.0, scale=1.0, angle=0.0):
    if alpha <= 0.01 or scale <= 0.01:
        return
    if abs(scale - 1) > 1e-3:
        im = im.resize((max(1, int(im.width * scale)), max(1, int(im.height * scale))), Image.BICUBIC)
    if angle:
        im = im.rotate(angle, Image.BICUBIC, expand=True)
    if alpha < 0.999:
        im = im.copy(); im.putalpha(im.getchannel("A").point(lambda v: int(v * alpha)))
    ox = {"l": 0, "m": im.width / 2, "r": im.width}[anchor[0]]
    oy = {"t": 0, "m": im.height / 2, "b": im.height}[anchor[1]]
    canvas.alpha_composite(im, (int(x - ox), int(y - oy)))


def reveal(canvas, txt, path, size, x, y, t, start, fill=INK, anchor="lt", dur=0.45, rise=40, spacing=0):
    """Mot qui passe du flou au net en montant (effet de la référence)."""
    k = (t - start) / dur
    if k <= 0:
        return 0
    e = ease_out(k)
    blur = int(round((1 - e) * 14))
    im = text(txt, path, size, fill, blur, spacing)
    shift = (blur * 3) if blur else 0
    ax = {"l": x - shift, "m": x, "r": x + shift}[anchor[0]]
    put(canvas, im, ax, y + rise * (1 - e) - shift if anchor[1] == "t" else y + rise * (1 - e),
        anchor=anchor, alpha=clamp(k * 1.6))
    return text(txt, path, size, fill, 0, spacing).width - 20


def typed(canvas, txt, path, size, x, y, t, start, per=0.05, fill=WHITE, anchor="lt"):
    """Lettre par lettre, chaque lettre arrive floue puis nette."""
    full = text(txt, path, size, fill)
    f = font(path, size)
    if anchor[0] == "m":
        x = x - (full.width - 20) / 2
    cx = x
    for i, ch in enumerate(txt):
        k = (t - start - i * per) / 0.25
        w_ = f.getlength(ch)
        if k > 0 and ch != " ":
            e = ease_out(k)
            b = int(round((1 - e) * 8))
            im = text(ch, path, size, fill, b)
            put(canvas, im, cx - b * 3 - 10 + 10, y - b * 3 + 30 * (1 - e), alpha=clamp(k * 2))
        cx += w_


def rrect(size, radius, fill, outline=None, width=0):
    im = Image.new("RGBA", size, (0, 0, 0, 0))
    ImageDraw.Draw(im).rounded_rectangle((0, 0, size[0] - 1, size[1] - 1), radius, fill=fill,
                                         outline=outline, width=width)
    return im


def shadowed(im, radius=30, off=18, alpha=70):
    pad = radius * 3
    out = Image.new("RGBA", (im.width + 2 * pad, im.height + 2 * pad), (0, 0, 0, 0))
    sh = Image.new("RGBA", out.size, (0, 0, 0, 0))
    sh.paste((60, 25, 0, alpha), (pad, pad + off, pad + im.width, pad + off + im.height), im.getchannel("A"))
    out = Image.alpha_composite(out, sh.filter(ImageFilter.GaussianBlur(radius)))
    out.alpha_composite(im, (pad, pad))
    return out


def rounded_photo(img, w, h, radius=36, border=0):
    s = max(w / img.width, h / img.height)
    im = img.resize((math.ceil(img.width * s), math.ceil(img.height * s)), Image.LANCZOS)
    im = im.crop(((im.width - w) // 2, (im.height - h) // 2, (im.width - w) // 2 + w, (im.height - h) // 2 + h))
    if border:
        fr = Image.new("RGB", (w + 2 * border, h + 2 * border), WHITE)
        fr.paste(im, (border, border)); im = fr
    m = Image.new("L", im.size, 0)
    ImageDraw.Draw(m).rounded_rectangle((0, 0, im.width - 1, im.height - 1), radius, fill=255)
    im = im.convert("RGBA"); im.putalpha(m)
    return im


yy, xx = np.mgrid[0:H, 0:W].astype(np.float32)


def glow_bg(base, glow, cx, cy, rx, ry, strength=1.0):
    d = ((xx - cx) / rx) ** 2 + ((yy - cy) / ry) ** 2
    g = np.exp(-d)[..., None] * strength
    a = np.array(base, np.float32) * (1 - g) + np.array(glow, np.float32) * g
    return Image.fromarray(a.clip(0, 255).astype(np.uint8)).convert("RGBA")


def light_bg(t):
    return glow_bg(CREAM, (255, 214, 170), W * (0.7 + 0.1 * math.sin(t * 0.6)), H * (0.25 + 0.05 * math.cos(t * 0.5)),
                   520, 640, 0.85)


def orange_bg(t):
    return glow_bg((226, 74, 8), (255, 168, 40), W * (0.5 + 0.15 * math.sin(t * 0.8)), H * 0.45, 700, 900, 0.9)


def dark_bg(t):
    return glow_bg(DARK, (190, 70, 10), W * (0.55 + 0.1 * math.sin(t * 0.7)), H * (0.45 + 0.05 * math.sin(t)),
                   560, 720, 0.8)


def dotted_arc(canvas, p0, p1, bend, prog, color, dot=7, gap=26, arrow=True):
    """Trajectoire en pointillés qui se dessine (avec pointe de flèche)."""
    if prog <= 0:
        return
    d = ImageDraw.Draw(canvas)
    (x0, y0), (x1, y1) = p0, p1
    mx, my = (x0 + x1) / 2, (y0 + y1) / 2 - bend
    pts = []
    n = 120
    for i in range(int(n * prog) + 1):
        u = i / n
        pts.append(((1 - u) ** 2 * x0 + 2 * (1 - u) * u * mx + u * u * x1,
                    (1 - u) ** 2 * y0 + 2 * (1 - u) * u * my + u * u * y1))
    acc, last = 0, pts[0]
    for p in pts[1:]:
        acc += math.dist(p, last); last = p
        if acc >= gap:
            acc = 0
            d.ellipse((p[0] - dot / 2, p[1] - dot / 2, p[0] + dot / 2, p[1] + dot / 2), fill=color)
    if arrow and len(pts) > 3:
        (ax, ay), (bx, by) = pts[-4], pts[-1]
        ang = math.atan2(by - ay, bx - ax)
        L = 30
        tri = [(bx + 8 * math.cos(ang), by + 8 * math.sin(ang)),
               (bx - L * math.cos(ang - 0.45), by - L * math.sin(ang - 0.45)),
               (bx - L * math.cos(ang + 0.45), by - L * math.sin(ang + 0.45))]
        d.polygon(tri, fill=color)


def check_icon(size, bg=ORANGE):
    im = rrect((size, size), size // 4, bg)
    d = ImageDraw.Draw(im)
    s = size
    d.line([(s * 0.27, s * 0.52), (s * 0.44, s * 0.68), (s * 0.74, s * 0.34)], fill=WHITE, width=max(4, s // 9),
           joint="curve")
    return im


# ---------------- éléments ----------------


def make_ticket():
    w, h = 820, 400
    tk = rrect((w, h), 34, WHITE)
    d = ImageDraw.Draw(tk)
    hdr = rrect((w, 74), 34, ORANGE)
    tk.alpha_composite(hdr, (0, 0))
    d.rectangle((0, 40, w, 74), fill=ORANGE)
    tk.alpha_composite(text("BILLET · SPECTACLE", BOLD, 24, WHITE, spacing=4), (36, 16))
    tk.alpha_composite(text("BEN ORACLE BUSINESS", SEMI, 22, (255, 230, 210), spacing=3), (w - 350, 18))
    tk.alpha_composite(text("JÉRÉMIE SHABANI", MED, 26, GREY), (36, 102))
    tk.alpha_composite(text("À bas la jalousie", BLACK, 62, INK), (30, 136))
    labels = [("DATE", "DIM. 06/12"), ("HEURE", "16H00"), ("SALLE", "GRAND TAMBOUR")]
    x = 36
    for lab, val in labels:
        tk.alpha_composite(text(lab, BOLD, 20, GREY, spacing=2), (x, 250))
        im = text(val, XBOLD, 29, INK)
        tk.alpha_composite(im, (x - 2, 278))
        x += im.width + 14
    # perforation + code-barres
    px = w - 165
    for y in range(80, h - 10, 22):
        d.ellipse((px - 4, y, px + 4, y + 8), fill=(235, 225, 215))
    rng = np.random.default_rng(4)
    bx = px + 32
    while bx < w - 36:
        bw = int(rng.integers(2, 7))
        d.rectangle((bx, 100, bx + bw, 300), fill=INK)
        bx += bw + int(rng.integers(3, 8))
    tk.alpha_composite(text("KINSHASA", BLACK, 22, ORANGE), (px + 16, 322))
    return shadowed(tk, 34, 22, 80)


TICKET = make_ticket()
POSTER_CARD = shadowed(rounded_photo(poster, 640, int(640 * 1518 / 1170), 34, border=12), 40, 26, 110)
FACE_CARD = shadowed(rounded_photo(face, 700, 760, 44), 40, 26, 120)
TITLE_CARD = shadowed(rounded_photo(title_crop, 820, 760, 44), 40, 26, 120)
FACE_ROUND = None


def face_round(size):
    global FACE_ROUND
    if FACE_ROUND is None:
        im = face.resize((size, int(size * face.height / face.width)), Image.LANCZOS).crop((0, 0, size, size))
        m = Image.new("L", (size, size), 0)
        ImageDraw.Draw(m).ellipse((0, 0, size - 1, size - 1), fill=255)
        im = im.convert("RGBA"); im.putalpha(m)
        FACE_ROUND = im
    return FACE_ROUND


def pill(txt, path, size, bg, fg, padx=34, pady=16):
    t_ = text(txt, path, size, fg)
    p = rrect((t_.width - 20 + 2 * padx, t_.height - 20 + 2 * pady + 6), (t_.height + 2 * pady) // 2, bg)
    p.alpha_composite(t_, (padx - 10, pady - 10 + 3))
    return p


def info_card(label, value, tag, w=900):
    c = rrect((w, 150), 34, WHITE)
    c.alpha_composite(check_icon(78), (34, 36))
    c.alpha_composite(text(label, BOLD, 22, GREY, spacing=3), (136, 28))
    c.alpha_composite(text(value, XBOLD, 44, INK), (134, 60))
    tg = pill(tag, BOLD, 22, (255, 236, 220), ORANGE, 20, 10)
    c.alpha_composite(tg, (w - tg.width - 30, (150 - tg.height) // 2))
    return shadowed(c, 26, 14, 55)


INFOS = [("DATE", "Dimanche 6 décembre 2026", "Réglé"),
         ("HEURE", "À partir de 16h00", "Réglé"),
         ("LIEU", "Centre culturel de Kinshasa", "Réglé"),
         ("SALLE", "Grand Tambour", "Réglé"),
         ("AMBIANCE", "Rires garantis", "100 %")]
INFO_CARDS = [info_card(*i) for i in INFOS]

PRICES = [("10$", YELLOW, INK), ("20$", (255, 120, 20), WHITE), ("50$", (40, 210, 220), INK), ("100$", (70, 190, 60), WHITE)]


def price_card(p, bg, fg):
    c = rrect((400, 300), 40, bg)
    c.alpha_composite(text("PLACE", BOLD, 26, fg, spacing=4), (36, 30))
    t_ = text(p, BLACK, 140, fg)
    c.alpha_composite(t_, ((400 - t_.width) // 2 + 4, 110))
    return shadowed(c, 30, 20, 120)


PRICE_CARDS = [price_card(*p) for p in PRICES]

# ---------------- scènes ----------------
# (début, fin, fonction) ; temps local passé à la fonction


def s_ticket(t):  # 0 - 4.2
    c = light_bg(t)
    reveal(c, "BEN ORACLE BUSINESS PRÉSENTE", BOLD, 26, 110, 300, t, 0.1, ORANGE, spacing=5)
    reveal(c, "Réservez", BLACK, 150, 100, 360, t, 0.35)
    reveal(c, "votre", BLACK, 150, 100, 530, t, 0.75)
    reveal(c, "place.", BLACK, 150, 100, 700, t, 1.15, ORANGE)
    k = ease_out((t - 0.5) / 0.9)
    if k > 0:  # billet qui glisse et se redresse
        put(c, TICKET, W / 2 + 60 + 600 * (1 - k), 1250 + 40 * math.sin(t * 1.4), "mm",
            alpha=clamp(k * 1.5), angle=8 - 4 * k + 1.5 * math.sin(t * 1.2))
    dotted_arc(c, (180, 1640), (860, 1560), 160, ease_io((t - 1.6) / 1.0), ORANGE)
    kb = ease_back((t - 2.6) / 0.4)
    if t > 2.6:  # bouton flèche
        bt = Image.new("RGBA", (150, 150), (0, 0, 0, 0))
        d = ImageDraw.Draw(bt)
        d.ellipse((0, 0, 149, 149), fill=ORANGE)
        d.line([(48, 75), (100, 75)], fill=WHITE, width=9)
        d.polygon([(104, 75), (80, 52), (80, 98)], fill=WHITE)
        put(c, shadowed(bt, 20, 10, 90), 860, 1560, "mm", scale=max(0.01, kb))
    return c


def s_name(t):  # 4.2 - 7.6
    c = orange_bg(t)
    d = ImageDraw.Draw(c)
    # orbite tournante
    rot = t * 25
    box = (W / 2 - 470, H / 2 - 330, W / 2 + 470, H / 2 + 330)
    d.arc(box, rot, rot + 140, fill=(255, 220, 170), width=4)
    d.arc(box, rot + 200, rot + 250, fill=(255, 220, 170), width=4)
    typed(c, "Jérémie", BLACK, 170, W / 2, 640, t, 0.15, 0.06, WHITE, "mt")
    typed(c, "Shabani", BLACK, 170, W / 2, 820, t, 0.55, 0.06, WHITE, "mt")
    reveal(c, "et son groupe", BOLD, 70, W / 2, 1050, t, 1.2, (255, 236, 215), "mt")
    k = ease_back((t - 1.7) / 0.45)
    if t > 1.7:
        put(c, pill("en spectacle", BLACK, 76, YELLOW, INK, 44, 18), W / 2, 1230, "mm", scale=max(0.01, k))
    return c


def s_infos(t):  # 7.6 - 13.2
    c = light_bg(t + 3)
    reveal(c, "Dimanche 6 décembre", MED, 50, W / 2, 230, t, 0.1, GREY, "mt")
    reveal(c, "À bas la", BLACK, 120, W / 2, 310, t, 0.35, INK, "mt")
    reveal(c, "jalousie !", BLACK, 120, W / 2, 450, t, 0.65, ORANGE, "mt")
    # soulignement qui se dessine
    k = ease_out((t - 1.0) / 0.5)
    if k > 0:
        d = ImageDraw.Draw(c)
        x0, x1 = W / 2 - 270, W / 2 - 270 + 540 * k
        d.line([(x0, 612), (x1, 606)], fill=ORANGE, width=10)
    # portrait rond avec anneau qui pulse
    ka = ease_back((t - 0.4) / 0.5)
    if t > 0.4:
        cx, cy, r = W / 2, 860, 160
        ring = Image.new("RGBA", (520, 520), (0, 0, 0, 0))
        dd = ImageDraw.Draw(ring)
        pul = (t * 1.2) % 1
        rr = 175 + 70 * pul
        dd.ellipse((260 - rr, 260 - rr, 260 + rr, 260 + rr), outline=ORANGE + (int(160 * (1 - pul)),), width=6)
        dd.ellipse((260 - 176, 260 - 176, 260 + 176, 260 + 176), fill=ORANGE)
        ring.alpha_composite(face_round(320), (100, 100))
        put(c, shadowed(ring, 30, 18, 60), cx, cy, "mm", scale=max(0.01, ka))
    # cartes qui s'empilent
    for i, card in enumerate(INFO_CARDS):
        st = 1.2 + i * 0.6
        k = ease_out((t - st) / 0.45)
        if k > 0:
            put(c, card, W / 2 + 200 * (1 - k), 1130 + i * 150, "mm", alpha=clamp(k * 1.8))
    # compteur
    n = sum(1 for i in range(5) if t > 1.2 + i * 0.6 + 0.3)
    d = ImageDraw.Draw(c)
    for i in range(5):
        x = W / 2 - 220 + i * 26
        d.ellipse((x, 1872, x + 12, 1884), fill=ORANGE if i < n else (225, 210, 200))
    put(c, text(f"{n} / 5  tout est prêt" if n == 5 else f"{n} / 5", SEMI, 30, INK), W / 2 - 80, 1860)
    return c


def s_prices(t):  # 13.2 - 17.6
    c = dark_bg(t)
    reveal(c, "LES TARIFS", BOLD, 34, W / 2, 330, t, 0.1, ORANGE2, "mt", spacing=8)
    reveal(c, "Choisissez", BLACK, 120, W / 2, 400, t, 0.3, WHITE, "mt")
    reveal(c, "votre place.", BLACK, 120, W / 2, 540, t, 0.6, YELLOW, "mt")
    pos = [(W / 2 - 215, 920), (W / 2 + 215, 920), (W / 2 - 215, 1260), (W / 2 + 215, 1260)]
    for i, (card, (x, y)) in enumerate(zip(PRICE_CARDS, pos)):
        st = 0.9 + i * 0.25
        k = ease_back((t - st) / 0.45)
        if t > st:
            put(c, card, x, y + 8 * math.sin(t * 2 + i), "mm", scale=max(0.01, k), angle=(-3, 2, 2, -3)[i] * k)
    reveal(c, "Centre culturel de Kinshasa · Grand Tambour", SEMI, 36, W / 2, 1520, t, 2.2, (255, 220, 190), "mt")
    return c


def s_cards(t):  # 17.6 - 21.4 : cartes photo + gros titre tapé
    c = dark_bg(t + 5)
    if t < 1.9:
        card, word, tag = FACE_CARD, "Jérémie.", "Tête d'affiche"
        tt = t
    else:
        card, word, tag = TITLE_CARD, "Kinshasa.", "Grand Tambour"
        tt = t - 1.9
    k = ease_out(tt / 0.5)
    put(c, card, W / 2 + 80 * (1 - k), 820, "mm", alpha=clamp(k * 2), scale=0.92 + 0.08 * k + 0.02 * tt)
    if tt > 0.35:
        put(c, shadowed(pill(tag, BOLD, 34, WHITE, ORANGE, 28, 12), 14, 8, 80), W / 2 + 300, 420, "mm",
            scale=max(0.01, ease_back((tt - 0.35) / 0.4)))
    typed(c, word, BLACK, 190, 80, 1350, tt, 0.4, 0.07, WHITE)
    reveal(c, "Dimanche 6 décembre · 16h00", SEMI, 42, 90, 1600, tt, 1.0, (255, 220, 190))
    return c


def s_final(t):  # 21.4 - 26.0 : collage + appel à l'action
    c = light_bg(t + 7)
    reveal(c, "Un rendez-vous.", BLACK, 96, W / 2, 150, t, 0.1, INK, "mt")
    kf = ease_out((t - 0.2) / 0.6)
    put(c, FACE_CARD, W / 2 - 250 - 120 * (1 - kf), 820, "mm", alpha=clamp(kf * 2), scale=0.48, angle=8)
    put(c, TITLE_CARD, W / 2 + 250 + 120 * (1 - kf), 800, "mm", alpha=clamp(kf * 2), scale=0.44, angle=-8)
    kp = ease_back((t - 0.5) / 0.6)
    if t > 0.5:
        put(c, POSTER_CARD, W / 2, 860 + 6 * math.sin(t * 1.5), "mm", scale=max(0.01, 0.95 * kp + 0.01 * t))
    reveal(c, "DIM. 06.12.2026 · 16H00", BLACK, 54, W / 2, 1450, t, 1.2, INK, "mt")
    if t > 1.6:
        pulse = 1 + 0.03 * math.sin((t - 1.6) * 2 * math.pi * 1.4)
        put(c, shadowed(pill("Réservez votre place", BLACK, 54, ORANGE, WHITE, 50, 24), 24, 14, 100),
            W / 2, 1620, "mm", scale=pulse * max(0.01, ease_back((t - 1.6) / 0.4)))
    reveal(c, "INFOLINE  +243 80 008 40 76", BOLD, 38, W / 2, 1740, t, 2.1, ORANGE, "mt", spacing=2)
    return c


SCENES = [(0.0, s_ticket), (4.2, s_name), (7.6, s_infos), (13.2, s_prices), (17.6, s_cards), (21.4, s_final)]
# transitions : (instant, type, durée)
TRANS = {4.2: ("circle", 0.45, (860, 1560)), 7.6: ("push_up", 0.5, None), 13.2: ("circle", 0.45, (W / 2, 1880)),
         17.6: ("zoom", 0.4, None), 21.4: ("push_left", 0.5, None)}


def scene_at(t):
    for i in range(len(SCENES) - 1, -1, -1):
        if t >= SCENES[i][0]:
            return SCENES[i][1](t - SCENES[i][0])


def scene_index(t):
    return max(i for i, s in enumerate(SCENES) if t >= s[0])


def frame(t):
    i = scene_index(t)
    cur = scene_at(t)
    # transition entrante : on mélange avec la scène précédente
    st = SCENES[i][0]
    if st in TRANS and t - st < TRANS[st][1]:
        kind, d, ctr = TRANS[st]
        p = ease_io((t - st) / d)
        prev = SCENES[i - 1][1](st - SCENES[i - 1][0] + (t - st))
        if kind == "circle":
            m = Image.new("L", (W, H), 0)
            r = p * math.hypot(W, H)
            ImageDraw.Draw(m).ellipse((ctr[0] - r, ctr[1] - r, ctr[0] + r, ctr[1] + r), fill=255)
            prev.paste(cur, (0, 0), m)
            cur = prev
        elif kind == "push_up":
            out = Image.new("RGBA", (W, H))
            out.paste(prev, (0, int(-H * p)))
            out.paste(cur, (0, int(H * (1 - p))))
            cur = out
        elif kind == "push_left":
            out = Image.new("RGBA", (W, H))
            out.paste(prev, (int(-W * p), 0))
            out.paste(cur, (int(W * (1 - p)), 0))
            cur = out
        elif kind == "zoom":
            z = 1 + 0.25 * p
            pz = prev.resize((int(W * z), int(H * z)), Image.BICUBIC).crop(
                (int((W * z - W) / 2), int((H * z - H) / 2), int((W * z - W) / 2) + W, int((H * z - H) / 2) + H))
            cur = Image.blend(pz, cur, p)
    a = np.asarray(cur.convert("RGB"), np.float32)
    # dérive caméra très légère + grain fin
    a += np.random.default_rng(int(t * FPS)).normal(0, 3.2, (H // 2, W // 2, 1)).repeat(2, 0).repeat(2, 1)
    if t > DUR - 0.5:
        a *= (DUR - t) / 0.5
    if t < 0.2:
        a = a * (t / 0.2) + 255 * (1 - t / 0.2)
    return np.clip(a, 0, 255).astype(np.uint8)


def audio_args():
    music = os.path.join(HERE, "fond_musique.m4a")
    voix = os.path.join(HERE, "voix_kinshasa.wav")
    ins, n = [], 1
    chain = []
    if os.path.exists(music):
        ins += ["-i", music]
        chain.append(f"[{n}:a]aformat=sample_rates=44100:channel_layouts=stereo,atrim=0:{DUR},volume=0.32,"
                     f"equalizer=f=2500:t=q:w=1.2:g=-5,afade=t=in:st=0:d=0.4[m]")
        n += 1
    if os.path.exists(voix):
        ins += ["-i", voix]
        chain.append(f"[{n}:a]aformat=sample_rates=44100:channel_layouts=stereo,highpass=f=80,"
                     f"acompressor=threshold=0.1:ratio=3:attack=5:release=120,volume=1.6,asplit=2[v][k]")
    if len(chain) == 2:
        chain += ["[m][k]sidechaincompress=threshold=0.03:ratio=6:attack=15:release=450[mb]",
                  f"[mb][v]amix=inputs=2:normalize=0,alimiter=limit=0.95,afade=t=out:st={DUR-1.5}:d=1.5[a]"]
    elif chain:
        chain[-1] = chain[-1].rsplit("[", 1)[0] + f",afade=t=out:st={DUR-1.5}:d=1.5[a]"
        if "asplit" in chain[-1]:
            chain[-1] = chain[-1].replace(",asplit=2[v][k]", "")
    else:
        ins += ["-f", "lavfi", "-i", "anullsrc=r=44100:cl=stereo"]
        chain.append(f"[1:a]atrim=0:{DUR}[a]")
    return ins + ["-filter_complex", ";".join(chain)]


def main():
    cmd = ["ffmpeg", "-v", "error", "-y", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{W}x{H}", "-r", str(FPS),
           "-i", "-", *audio_args(), "-map", "0:v", "-map", "[a]",
           "-c:v", "libx264", "-crf", "20", "-maxrate", "12M", "-bufsize", "24M", "-preset", "slow",
           "-pix_fmt", "yuv420p", "-c:a", "aac", "-b:a", "192k", "-movflags", "+faststart", "-t", str(DUR), OUT]
    p = subprocess.Popen(cmd, stdin=subprocess.PIPE)
    n = int(DUR * FPS)
    for fi in range(n):
        p.stdin.write(frame(fi / FPS).tobytes())
        if fi % 90 == 0:
            print(f"{fi}/{n}", flush=True)
    p.stdin.close(); p.wait()
    print(f"OK -> {OUT}")


if __name__ == "__main__":
    if len(sys.argv) > 2 and sys.argv[1] == "--frame":
        Image.fromarray(frame(float(sys.argv[2]))).save(sys.argv[3])
    else:
        main()
