// =====================================================================
//  Moteur de modèles motion design
//  Une vidéo = une liste de scènes décrites dans un fichier JSON.
//  Le moteur dessine chaque image sur un <canvas> ; rendu.js les exporte en MP4.
// =====================================================================
(function () {
'use strict';

// ---------- Outils mathématiques ----------
const clamp = (x, a = 0, b = 1) => Math.max(a, Math.min(b, x));
const prog = (t, a, b) => clamp((t - a) / (b - a));
const lerp = (a, b, x) => a + (b - a) * x;
const eOut = x => 1 - Math.pow(1 - x, 3);
const eIn = x => x * x * x;
const eInOut = x => x < .5 ? 4 * x * x * x : 1 - Math.pow(-2 * x + 2, 3) / 2;
const eBack = x => { const c = 1.7; return 1 + (c + 1) * Math.pow(x - 1, 3) + c * Math.pow(x - 1, 2); };
function rnd(seed) { let s = seed; return () => (s = (s * 16807) % 2147483647) / 2147483647; }

// ---------- État global ----------
let cv, ctx, W, H, U, PORTRAIT, PAYSAGE;
let T = {};            // thème (couleurs)
let P = null;          // projet chargé
let timeline = [];     // [{ debut, duree, scene }]
let DUREE = 0;
const images = {};     // nom de fichier -> HTMLImageElement
const TR = 0.4;        // demi-durée d'une transition (s)

const THEME_DEFAUT = {
  fond: '#07070a', principal: '#A3192F', accent: '#E0344F', texte: '#ffffff',
  doux: '#bdbdc4', carte: 'rgba(255,255,255,0.06)', decor: 'particules', police: 'Inter'
};

function rgba(hex, a) {
  if (!hex || hex[0] !== '#') return hex;
  let h = hex.slice(1);
  if (h.length === 3) h = h.split('').map(c => c + c).join('');
  const n = parseInt(h, 16);
  return `rgba(${n >> 16 & 255},${n >> 8 & 255},${n & 255},${a})`;
}

// ---------- Texte ----------
function font(size, weight = 700) { ctx.font = `${weight} ${size * U}px ${T.police}, Inter, sans-serif`; }
function spacing(px) { if ('letterSpacing' in ctx) ctx.letterSpacing = `${px * U}px`; }
function measure(str, size, weight = 700, sp = 0) {
  font(size, weight); spacing(sp);
  const w = ctx.measureText(str).width;
  spacing(0);
  return w;
}
function text(str, x, y, { size = 60, weight = 700, color = T.texte, align = 'center', alpha = 1, sp = 0, base = 'middle' } = {}) {
  if (alpha <= 0 || str == null) return;
  ctx.save();
  ctx.globalAlpha *= alpha;
  font(size, weight); spacing(sp);
  ctx.fillStyle = color; ctx.textAlign = align; ctx.textBaseline = base;
  ctx.fillText(String(str), x, y);
  ctx.restore();
}
// Réduit la taille jusqu'à ce que le texte tienne dans maxW (en pixels).
function fit(str, maxW, size, weight = 700, sp = 0, min = 18) {
  let s = size;
  while (s > min && measure(str, s, weight, sp) > maxW) s -= 2;
  return s;
}
// Coupe un texte en lignes qui tiennent dans maxW.
function wrap(str, maxW, size, weight = 700) {
  const out = [];
  for (const para of String(str).split('\n')) {
    let line = '';
    for (const w of para.split(/\s+/).filter(Boolean)) {
      const test = line ? line + ' ' + w : w;
      if (line && measure(test, size, weight) > maxW) { out.push(line); line = w; } else line = test;
    }
    out.push(line);
  }
  return out;
}
// Texte en paragraphe centré, taille auto pour tenir en maxLignes.
function paragraph(str, x, y, maxW, { size = 50, weight = 500, maxLignes = 3, lh = 1.25, ...o } = {}) {
  let s = size, lines = wrap(str, maxW, s, weight);
  while (lines.length > maxLignes && s > 20) { s -= 2; lines = wrap(str, maxW, s, weight); }
  const step = s * lh * U;
  const y0 = y - (lines.length - 1) * step / 2;
  lines.forEach((ln, i) => text(ln, x, y0 + i * step, { size: s, weight, ...o }));
  return { hauteur: lines.length * step, lignes: lines.length };
}

function roundRect(x, y, w, h, r) {
  r = Math.min(r, w / 2, h / 2);
  ctx.beginPath(); ctx.moveTo(x + r, y); ctx.arcTo(x + w, y, x + w, y + h, r); ctx.arcTo(x + w, y + h, x, y + h, r);
  ctx.arcTo(x, y + h, x, y, r); ctx.arcTo(x, y, x + w, y, r); ctx.closePath();
}

// ---------- Décors de fond ----------
const R = rnd(42);
const particules = Array.from({ length: 80 }, () => ({ x: R(), y: R(), r: R() * 3 + 1, sp: R() * .04 + .01, ph: R() * 6.28, a: R() * .5 + .15 }));
const formes = Array.from({ length: 14 }, () => ({ x: R(), y: R(), s: R() * 90 + 40, rot: R() * 6.28, vr: (R() - .5) * .6, vy: R() * .02 + .005, k: Math.floor(R() * 3) }));

function halo(t, x, y, a) {
  const g = ctx.createRadialGradient(x, y, 0, x, y, Math.max(W, H) * .7);
  g.addColorStop(0, rgba(T.principal, a + .05 * Math.sin(t * 1.3)));
  g.addColorStop(1, rgba(T.principal, 0));
  ctx.fillStyle = g; ctx.fillRect(0, 0, W, H);
}
function vignette() {
  const v = ctx.createRadialGradient(W / 2, H / 2, Math.min(W, H) * .35, W / 2, H / 2, Math.max(W, H) * .75);
  v.addColorStop(0, 'rgba(0,0,0,0)'); v.addColorStop(1, 'rgba(0,0,0,0.7)');
  ctx.fillStyle = v; ctx.fillRect(0, 0, W, H);
}
const DECORS = {
  uni() {},
  particules(t) {
    halo(t, W / 2, H / 2, .18);
    for (const p of particules) {
      const y = ((p.y - t * p.sp) % 1 + 1) % 1, x = p.x + Math.sin(t * .5 + p.ph) * .01;
      ctx.globalAlpha = p.a * (.6 + .4 * Math.sin(t * 2 + p.ph));
      ctx.fillStyle = p.r > 3 ? T.accent : '#ffffff';
      ctx.beginPath(); ctx.arc(x * W, y * H, p.r * U, 0, 6.283); ctx.fill();
    }
    ctx.globalAlpha = 1;
  },
  grille(t) {
    halo(t, W / 2, H * .45, .14);
    const pas = 90 * U, dec = (t * 30 * U) % pas;
    ctx.strokeStyle = rgba(T.texte, .06); ctx.lineWidth = 1.5 * U;
    ctx.beginPath();
    for (let x = -pas + dec; x < W + pas; x += pas) { ctx.moveTo(x, 0); ctx.lineTo(x, H); }
    for (let y = -pas + dec; y < H + pas; y += pas) { ctx.moveTo(0, y); ctx.lineTo(W, y); }
    ctx.stroke();
    // points lumineux aux croisements
    const r2 = rnd(7);
    for (let i = 0; i < 24; i++) {
      const gx = Math.floor(r2() * W / pas) * pas + dec, gy = Math.floor(r2() * H / pas) * pas + dec;
      ctx.globalAlpha = .3 + .3 * Math.sin(t * 2 + i);
      ctx.fillStyle = T.accent; ctx.beginPath(); ctx.arc(gx, gy, 3 * U, 0, 6.283); ctx.fill();
    }
    ctx.globalAlpha = 1;
  },
  formes(t) {
    halo(t, W * .3, H * .3, .12); halo(t + 2, W * .8, H * .8, .1);
    for (const f of formes) {
      const y = ((f.y - t * f.vy) % 1.2 + 1.2) % 1.2 - .1;
      ctx.save(); ctx.translate(f.x * W, y * H); ctx.rotate(f.rot + t * f.vr);
      ctx.strokeStyle = rgba(f.k === 0 ? T.accent : T.texte, .14); ctx.lineWidth = 3 * U;
      const s = f.s * U;
      ctx.beginPath();
      if (f.k === 0) ctx.rect(-s / 2, -s / 2, s, s);
      else if (f.k === 1) ctx.arc(0, 0, s / 2, 0, 6.283);
      else { ctx.moveTo(0, -s / 2); ctx.lineTo(s / 2, s / 2); ctx.lineTo(-s / 2, s / 2); ctx.closePath(); }
      ctx.stroke(); ctx.restore();
    }
  },
  degrade(t) {
    const blobs = [[.25, .3, T.principal], [.75, .65, T.accent], [.5, .9, T.principal]];
    blobs.forEach(([bx, by, c], i) => {
      const x = (bx + .08 * Math.sin(t * .4 + i * 2)) * W, y = (by + .06 * Math.cos(t * .35 + i)) * H;
      const g = ctx.createRadialGradient(x, y, 0, x, y, Math.max(W, H) * .55);
      g.addColorStop(0, rgba(c, .35)); g.addColorStop(1, rgba(c, 0));
      ctx.fillStyle = g; ctx.fillRect(0, 0, W, H);
    });
  },
};
function fond(t) {
  ctx.fillStyle = T.fond; ctx.fillRect(0, 0, W, H);
  (DECORS[T.decor] || DECORS.particules)(t);
  vignette();
}

// ---------- Icônes ----------
function icone(kind, x, y, r) {
  ctx.save();
  const disque = (c) => { ctx.fillStyle = c; ctx.beginPath(); ctx.arc(x, y, r, 0, 6.283); ctx.fill(); ctx.fillStyle = '#fff'; };
  const carre = (c) => { ctx.fillStyle = c; roundRect(x - r, y - r, 2 * r, 2 * r, r * .5); ctx.fill(); ctx.fillStyle = '#fff'; };
  ctx.strokeStyle = '#fff'; ctx.fillStyle = '#fff'; ctx.lineCap = 'round'; ctx.lineJoin = 'round';
  switch (kind) {
    case 'whatsapp':
      disque('#25D366');
      ctx.fillStyle = '#25D366';
      ctx.beginPath(); ctx.moveTo(x - r * .55, y + r * .95); ctx.lineTo(x - r * .2, y + r * .55); ctx.lineTo(x - r * .75, y + r * .35); ctx.fill();
      ctx.lineWidth = r * .14; ctx.beginPath(); ctx.arc(x, y, r * .62, 0, 6.283); ctx.stroke();
      ctx.fillStyle = '#fff'; ctx.beginPath(); ctx.ellipse(x, y, r * .2, r * .32, -.7, 0, 6.283); ctx.fill();
      break;
    case 'instagram': {
      const g = ctx.createLinearGradient(x - r, y + r, x + r, y - r);
      g.addColorStop(0, '#F58529'); g.addColorStop(.5, '#DD2A7B'); g.addColorStop(1, '#8134AF');
      carre(g);
      ctx.lineWidth = r * .14; roundRect(x - r * .6, y - r * .6, 1.2 * r, 1.2 * r, r * .35); ctx.stroke();
      ctx.beginPath(); ctx.arc(x, y, r * .28, 0, 6.283); ctx.stroke();
      ctx.beginPath(); ctx.arc(x + r * .38, y - r * .38, r * .08, 0, 6.283); ctx.fill();
      break;
    }
    case 'tiktok': {
      carre('#111');
      const note = (dx, dy, c) => {
        ctx.strokeStyle = c; ctx.lineWidth = r * .18;
        ctx.beginPath(); ctx.moveTo(x + dx + r * .1, y + dy - r * .55); ctx.lineTo(x + dx + r * .1, y + dy + r * .25); ctx.stroke();
        ctx.beginPath(); ctx.arc(x + dx - r * .12, y + dy + r * .25, r * .22, 0, 6.283); ctx.stroke();
        ctx.beginPath(); ctx.moveTo(x + dx + r * .1, y + dy - r * .55); ctx.quadraticCurveTo(x + dx + r * .2, y + dy - r * .2, x + dx + r * .5, y + dy - r * .25); ctx.stroke();
      };
      note(-r * .05, -r * .03, '#25F4EE'); note(r * .05, r * .03, '#FE2C55'); note(0, 0, '#fff');
      break;
    }
    case 'facebook':
      disque('#1877F2');
      font(r * 1.5 / U, 900); ctx.fillStyle = '#fff'; ctx.textAlign = 'center'; ctx.textBaseline = 'middle';
      ctx.fillText('f', x + r * .05, y + r * .12);
      break;
    case 'telephone':
      disque(T.principal);
      ctx.lineWidth = r * .16;
      roundRect(x - r * .3, y - r * .5, r * .6, r, r * .12); ctx.stroke();
      ctx.beginPath(); ctx.arc(x, y + r * .32, r * .05, 0, 6.283); ctx.fill();
      break;
    case 'email':
      disque(T.principal);
      ctx.lineWidth = r * .12;
      ctx.strokeRect(x - r * .5, y - r * .32, r, r * .64);
      ctx.beginPath(); ctx.moveTo(x - r * .5, y - r * .32); ctx.lineTo(x, y + r * .08); ctx.lineTo(x + r * .5, y - r * .32); ctx.stroke();
      break;
    case 'lieu':
      disque(T.principal);
      ctx.beginPath(); ctx.arc(x, y - r * .15, r * .32, Math.PI * .85, Math.PI * .15); ctx.lineTo(x, y + r * .55); ctx.closePath(); ctx.fill();
      ctx.fillStyle = T.principal; ctx.beginPath(); ctx.arc(x, y - r * .15, r * .13, 0, 6.283); ctx.fill();
      break;
    case 'web':
      disque(T.principal);
      ctx.lineWidth = r * .1;
      ctx.beginPath(); ctx.arc(x, y, r * .55, 0, 6.283); ctx.stroke();
      ctx.beginPath(); ctx.ellipse(x, y, r * .25, r * .55, 0, 0, 6.283); ctx.stroke();
      ctx.beginPath(); ctx.moveTo(x - r * .55, y); ctx.lineTo(x + r * .55, y); ctx.stroke();
      break;
    case 'coche':
      disque(T.principal);
      ctx.lineWidth = r * .2;
      ctx.beginPath(); ctx.moveTo(x - r * .4, y); ctx.lineTo(x - r * .1, y + r * .3); ctx.lineTo(x + r * .42, y - r * .3); ctx.stroke();
      break;
    case 'etoile':
      disque(T.principal);
      ctx.beginPath();
      for (let i = 0; i < 10; i++) { const a = -Math.PI / 2 + i * Math.PI / 5, rr = i % 2 ? r * .25 : r * .6; ctx.lineTo(x + Math.cos(a) * rr, y + Math.sin(a) * rr); }
      ctx.closePath(); ctx.fill();
      break;
    case 'camion':
      disque(T.principal);
      ctx.fillRect(x - r * .55, y - r * .3, r * .62, r * .45);
      ctx.beginPath(); ctx.moveTo(x + r * .1, y - r * .15); ctx.lineTo(x + r * .35, y - r * .15); ctx.lineTo(x + r * .55, y + r * .05); ctx.lineTo(x + r * .55, y + r * .15); ctx.lineTo(x + r * .1, y + r * .15); ctx.fill();
      ctx.fillStyle = T.principal;
      [[-.32, .22], [.32, .22]].forEach(([dx, dy]) => { ctx.beginPath(); ctx.arc(x + r * dx, y + r * dy, r * .13, 0, 6.283); ctx.fill(); });
      ctx.fillStyle = '#fff';
      [[-.32, .22], [.32, .22]].forEach(([dx, dy]) => { ctx.beginPath(); ctx.arc(x + r * dx, y + r * dy, r * .07, 0, 6.283); ctx.fill(); });
      break;
    default: { // numéro ou texte court dans un disque
      disque(T.principal);
      const s = String(kind).length > 1 ? r * .8 : r * 1.05;
      font(s / U, 800); ctx.fillStyle = '#fff'; ctx.textAlign = 'center'; ctx.textBaseline = 'middle';
      ctx.fillText(String(kind), x, y + r * .04);
    }
  }
  ctx.restore();
}

// ---------- Éléments réutilisables ----------
function carte(cx, cy, w, h, p) {
  const e = eOut(p);
  ctx.save();
  ctx.globalAlpha *= clamp(p * 1.5);
  ctx.translate(0, (1 - e) * 50 * U);
  ctx.fillStyle = T.carte; ctx.strokeStyle = rgba(T.accent, .7); ctx.lineWidth = 2.5 * U;
  roundRect(cx - w / 2, cy - h / 2, w, h, 26 * U); ctx.fill(); ctx.stroke();
  ctx.fillStyle = T.principal; ctx.fillRect(cx - w / 2 + 2 * U, cy - h / 2 + 22 * U, 7 * U, h - 44 * U);
}
function titreHaut(str, y, l, size = 64) {
  if (!str) return;
  const p = eOut(prog(l, 0, .6));
  const s = fit(str.toUpperCase(), W * .88, size, 800, 6);
  text(str.toUpperCase(), W / 2, y - (1 - p) * 30 * U, { size: s, weight: 800, alpha: p, sp: 6 });
  ctx.fillStyle = T.principal;
  ctx.fillRect(W / 2 - 60 * U * p, y + s * U * .75, 120 * U * p, 6 * U);
}
function dessinerImage(img, x, y, w, h, zoom = 1, px = 0, py = 0) {
  // remplit le rectangle (mode "cover") avec zoom et décalage
  const r = Math.max(w / img.width, h / img.height) * zoom;
  const iw = img.width * r, ih = img.height * r;
  ctx.drawImage(img, x + (w - iw) / 2 + px * (iw - w) / 2, y + (h - ih) / 2 + py * (ih - h) / 2, iw, ih);
}
function emplacementPhoto(x, y, w, h, nom) {
  const g = ctx.createLinearGradient(x, y, x + w, y + h);
  g.addColorStop(0, rgba(T.principal, .55)); g.addColorStop(1, rgba(T.fond, .9));
  ctx.fillStyle = g; ctx.fillRect(x, y, w, h);
  ctx.strokeStyle = rgba(T.texte, .3); ctx.lineWidth = 3 * U; ctx.setLineDash([16 * U, 12 * U]);
  ctx.strokeRect(x + 20 * U, y + 20 * U, w - 40 * U, h - 40 * U); ctx.setLineDash([]);
  text('VOTRE PHOTO ICI', x + w / 2, y + h / 2 - 30 * U, { size: 46, weight: 800, sp: 4, alpha: .8 });
  if (nom) text(nom, x + w / 2, y + h / 2 + 35 * U, { size: 28, weight: 400, color: T.doux, alpha: .8 });
}

// =====================================================================
//  SCÈNES  —  chaque fonction reçoit (l = temps local, d = durée, s = réglages)
// =====================================================================
const SCENES = {};

// Logo / nom de marque : lettres qui montent, dernier mot en couleur.
SCENES.logo = (l, d, s) => {
  const img = s.image && images[s.image];
  let bas;
  if (img) {
    const p = prog(l, .1, .8), k = eBack(p);
    const maxW = W * .6, maxH = H * (PORTRAIT ? .25 : .4);
    const r = Math.min(maxW / img.width, maxH / img.height);
    const w = img.width * r * k, h = img.height * r * k;
    ctx.save(); ctx.globalAlpha *= clamp(p * 2);
    ctx.drawImage(img, W / 2 - w / 2, H * .45 - h / 2, w, h);
    ctx.restore();
    bas = H * .45 + img.height * r / 2;
  } else {
    const mots = String(s.texte || P.marque || 'Votre marque').split(' ');
    const size = fit(mots.join(' '), W * .86, PORTRAIT ? 170 : 190, 900);
    const total = measure(mots.join(' '), size, 900);
    let x = W / 2 - total / 2, idx = 0;
    const y = H * .45;
    mots.forEach((m, mi) => {
      const couleur = mi === mots.length - 1 && mots.length > 1 ? T.accent : T.texte;
      for (const ch of m + (mi < mots.length - 1 ? ' ' : '')) {
        const p = eOut(prog(l, .15 + idx * .06, .65 + idx * .06));
        const w = measure(ch, size, 900);
        ctx.save(); ctx.beginPath(); ctx.rect(x - 5 * U, y - size * U, w + 10 * U, size * U * 1.1); ctx.clip();
        text(ch, x, y + (1 - p) * size * U, { size, weight: 900, align: 'left', color: couleur, base: 'alphabetic' });
        ctx.restore();
        x += w; idx++;
      }
    });
    bas = y + 20 * U;
    // trait de soulignement
    const pl = eInOut(prog(l, .5, 1.2));
    ctx.fillStyle = T.principal;
    ctx.fillRect(W / 2 - total / 2, bas + 10 * U, total * pl, 8 * U);
  }
  if (s.sousTitre) {
    const p = eOut(prog(l, 1.0, 1.6));
    paragraph(s.sousTitre, W / 2, bas + 90 * U + (1 - p) * 30 * U, W * .84, { size: 50, weight: 500, color: T.doux, alpha: p, maxLignes: 2, sp: 2 });
  }
};

// Grand titre sur plusieurs lignes, révélées par masque.
SCENES.titre = (l, d, s) => {
  const lignes = s.lignes || [s.texte || 'Titre'];
  let size = s.taille || (PORTRAIT ? 165 : 125);
  for (const ln of lignes) size = Math.min(size, fit(ln, W * .88, size, 900));
  const lh = size * 1.18 * U;
  const y0 = H / 2 - (lignes.length - 1) * lh / 2 + (s.surtitre ? 30 * U : 0);
  const accent = s.accent != null ? s.accent : lignes.length - 1;
  if (s.surtitre) {
    const p = eOut(prog(l, 0, .5));
    text(s.surtitre.toUpperCase(), W / 2, y0 - lh * .5 - 70 * U, { size: fit(s.surtitre.toUpperCase(), W * .86, 40, 700, 8), weight: 700, color: T.accent, sp: 8, alpha: p });
  }
  lignes.forEach((ln, i) => {
    const p = eOut(prog(l, .1 + i * .16, .7 + i * .16));
    const y = y0 + i * lh;
    ctx.save(); ctx.beginPath(); ctx.rect(0, y - lh / 2, W, lh); ctx.clip();
    text(ln, W / 2, y + (1 - p) * lh, { size, weight: 900, color: i === accent ? T.accent : T.texte });
    ctx.restore();
  });
  if (s.sousTitre) {
    const p = eOut(prog(l, .9, 1.5));
    paragraph(s.sousTitre, W / 2, y0 + (lignes.length - .5) * lh + 70 * U, W * .84, { size: 44, weight: 500, color: T.doux, alpha: p, maxLignes: 2 });
  }
};

// Liste d'éléments (services, avantages...) qui arrivent un par un.
SCENES.liste = (l, d, s) => {
  const items = s.elements || [];
  const n = items.length || 1;
  const yt = PORTRAIT ? H * .17 : H * .14;
  titreHaut(s.titre, yt, l);
  const top = yt + 130 * U, bottom = H - (PORTRAIT ? H * .1 : 60 * U);
  const cols = (!PORTRAIT && n > 3) ? 2 : 1;
  const rows = Math.ceil(n / cols);
  const gap = 26 * U;
  const cw = cols === 1 ? Math.min(W * .86, 1300 * U) : W * .43;
  const ch = Math.min((bottom - top - gap * (rows - 1)) / rows, (PORTRAIT ? 250 : 210) * U);
  const blocH = rows * ch + (rows - 1) * gap;
  const y0 = top + (bottom - top - blocH) / 2;
  const etal = Math.min(.45, (d - 2) / n);
  items.forEach((it, i) => {
    const o = typeof it === 'string' ? { texte: it } : it;
    const c = i % cols, r = Math.floor(i / cols);
    const cx = cols === 1 ? W / 2 : W / 2 + (c ? 1 : -1) * (cw / 2 + gap / 2);
    const cy = y0 + r * (ch + gap) + ch / 2;
    const p = prog(l, .5 + i * etal, 1.1 + i * etal);
    if (p <= 0) return;
    carte(cx, cy, cw, ch, p);
    const ir = Math.min(ch * .3, 46 * U);
    const ix = cx - cw / 2 + 40 * U + ir;
    icone(o.icone || s.icone || String(i + 1), ix, cy, ir * eBack(clamp(p * 1.3)));
    const tx = ix + ir + 30 * U, maxW = cx + cw / 2 - tx - 30 * U;
    if (o.detail) {
      text(o.texte, tx, cy - ch * .16, { size: fit(o.texte, maxW, Math.min(52, ch / U * .3), 800), weight: 800, align: 'left' });
      text(o.detail, tx, cy + ch * .2, { size: fit(o.detail, maxW, Math.min(36, ch / U * .2), 400), weight: 400, align: 'left', color: T.doux });
    } else {
      text(o.texte, tx, cy, { size: fit(o.texte, maxW, Math.min(54, ch / U * .32), 700), weight: 700, align: 'left' });
    }
    ctx.restore();
  });
};

// Promotion : badge de remise, ancien prix barré, nouveau prix.
SCENES.promo = (l, d, s) => {
  const bx = PORTRAIT ? W / 2 : W * .3, by = PORTRAIT ? H * .3 : H / 2;
  const br = (PORTRAIT ? 260 : 270) * U;
  // badge étoilé qui tourne
  const pb = prog(l, .1, .7);
  if (pb > 0) {
    const k = eBack(pb);
    ctx.save(); ctx.translate(bx, by); ctx.scale(k, k);
    ctx.save(); ctx.rotate(l * .4);
    ctx.fillStyle = T.principal;
    ctx.beginPath();
    for (let i = 0; i < 32; i++) { const a = i * Math.PI / 16, r = i % 2 ? br * .88 : br; ctx.lineTo(Math.cos(a) * r, Math.sin(a) * r); }
    ctx.closePath(); ctx.fill();
    ctx.restore();
    ctx.strokeStyle = rgba('#ffffff', .5); ctx.lineWidth = 4 * U; ctx.setLineDash([10 * U, 10 * U]);
    ctx.beginPath(); ctx.arc(0, 0, br * .74, 0, 6.283); ctx.stroke(); ctx.setLineDash([]);
    const rem = s.remise || '-30%';
    text(rem, 0, s.etiquette ? -br * .08 : 0, { size: fit(rem, br * 1.3, 170, 900), weight: 900 });
    if (s.etiquette) text(s.etiquette.toUpperCase(), 0, br * .38, { size: fit(s.etiquette.toUpperCase(), br * 1.1, 40, 700, 4), weight: 700, sp: 4 });
    ctx.restore();
  }
  // halo pulsé
  const ring = (l * .8) % 1;
  if (pb >= 1) {
    ctx.strokeStyle = rgba(T.accent, (1 - ring) * .5); ctx.lineWidth = 5 * U;
    ctx.beginPath(); ctx.arc(bx, by, br * (1 + ring * .35), 0, 6.283); ctx.stroke();
  }
  // textes
  const tx = PORTRAIT ? W / 2 : W * .68, align = 'center';
  const maxW = PORTRAIT ? W * .86 : W * .55;
  // hauteur approximative du bloc pour le centrer verticalement
  const hb = (s.produit ? 220 : 0) + (s.ancienPrix ? 120 : 0) + (s.prix ? 130 : 0) + (s.mention ? 50 : 0);
  let y = PORTRAIT ? H * .58 : H / 2 - hb * U / 2 + 60 * U;
  if (s.produit) {
    const p = eOut(prog(l, .6, 1.2));
    const r = paragraph(s.produit, tx, y + (1 - p) * 30 * U, maxW, { size: PORTRAIT ? 72 : 70, weight: 800, alpha: p, maxLignes: 2, align });
    y += r.hauteur / 2 + 100 * U;
  }
  if (s.ancienPrix) {
    const p = eOut(prog(l, 1.0, 1.4));
    const sz = 56;
    text(s.ancienPrix, tx, y, { size: sz, weight: 500, color: T.doux, alpha: p, align });
    const w = measure(s.ancienPrix, sz, 500) + 20 * U, ps = eInOut(prog(l, 1.4, 1.8));
    ctx.save(); ctx.strokeStyle = T.accent; ctx.lineWidth = 7 * U; ctx.lineCap = 'round';
    ctx.beginPath(); ctx.moveTo(tx - w / 2, y + 12 * U); ctx.lineTo(tx - w / 2 + w * ps, y - 12 * U * (2 * ps - 1)); ctx.stroke(); ctx.restore();
    y += 120 * U;
  }
  if (s.prix) {
    const p = prog(l, 1.7, 2.2);
    if (p > 0) {
      const k = eBack(p), sz = fit(s.prix, maxW, 130, 900);
      ctx.save(); ctx.translate(tx, y); ctx.scale(k, k);
      text(s.prix, 0, 0, { size: sz, weight: 900, color: T.accent, alpha: clamp(p * 2) });
      ctx.restore();
    }
    y += 130 * U;
  }
  if (s.mention) {
    const p = eOut(prog(l, 2.2, 2.7));
    paragraph(s.mention, tx, y + (1 - p) * 20 * U, maxW, { size: 40, weight: 500, color: T.doux, alpha: p, maxLignes: 2, align });
  }
};

// Photo plein écran avec effet Ken Burns + légende.
SCENES.image = (l, d, s) => {
  const img = images[s.fichier];
  const p = prog(l, 0, d);
  const zoom = s.mouvement === 'zoom-arriere' ? lerp(1.18, 1, eInOut(p)) : lerp(1, 1.15, eInOut(p));
  const px = s.mouvement === 'gauche' ? lerp(.6, -.6, p) : s.mouvement === 'droite' ? lerp(-.6, .6, p) : 0;
  const cadre = s.cadre;
  let x = 0, y = 0, w = W, h = H;
  if (cadre) {
    w = W * .82; h = PORTRAIT ? H * .55 : H * .66;
    x = (W - w) / 2; y = PORTRAIT ? H * .14 : H * .1;
    const pe = eOut(prog(l, 0, .6));
    ctx.save(); ctx.globalAlpha *= pe; ctx.translate(0, (1 - pe) * 60 * U);
    ctx.shadowColor = 'rgba(0,0,0,.6)'; ctx.shadowBlur = 40 * U;
    ctx.fillStyle = '#000'; roundRect(x, y, w, h, 30 * U); ctx.fill();
    ctx.shadowBlur = 0;
    roundRect(x, y, w, h, 30 * U); ctx.clip();
  } else {
    ctx.save();
  }
  if (img) dessinerImage(img, x, y, w, h, zoom, px, 0); else emplacementPhoto(x, y, w, h, s.fichier);
  ctx.restore();
  if (!cadre) {
    const g = ctx.createLinearGradient(0, H * .5, 0, H);
    g.addColorStop(0, 'rgba(0,0,0,0)'); g.addColorStop(1, 'rgba(0,0,0,.85)');
    ctx.fillStyle = g; ctx.fillRect(0, H * .5, W, H * .5);
  }
  const ly = cadre ? y + h + (H - y - h) * .45 : H * (PORTRAIT ? .8 : .82);
  if (s.legende) {
    const pl = eOut(prog(l, .5, 1.1));
    paragraph(s.legende, W / 2, ly + (1 - pl) * 30 * U, W * .86, { size: PORTRAIT ? 64 : 62, weight: 800, alpha: pl, maxLignes: 2 });
  }
  if (s.detail) {
    const pd = eOut(prog(l, .9, 1.5));
    paragraph(s.detail, W / 2, ly + 110 * U + (1 - pd) * 20 * U, W * .84, { size: 40, weight: 500, color: T.doux, alpha: pd, maxLignes: 2 });
  }
};

// Chiffres clés qui défilent (compteurs).
SCENES.chiffres = (l, d, s) => {
  const items = s.elements || [];
  const n = items.length || 1;
  const yt = PORTRAIT ? H * .2 : H * .16;
  titreHaut(s.titre, yt, l);
  items.forEach((it, i) => {
    let cx, cy, cellW;
    if (PORTRAIT) { cx = W / 2; cellW = W * .86; cy = yt + 200 * U + (H * .78 - yt - 120 * U) * (i + .5) / n; }
    else { cellW = W * .86 / n; cx = W * .07 + cellW * (i + .5); cy = H * .56; }
    const p = prog(l, .4 + i * .25, 1.0 + i * .25);
    if (p <= 0) return;
    const c = eOut(prog(l, .4 + i * .25, Math.max(1.0, d - 1.2)));
    const v = Number(it.valeur) || 0;
    const dec = it.decimales || 0;
    const val = (v * c).toLocaleString('fr-FR', { minimumFractionDigits: dec, maximumFractionDigits: dec });
    const str = (it.prefixe || '') + val + (it.suffixe || '');
    const full = (it.prefixe || '') + v.toLocaleString('fr-FR', { minimumFractionDigits: dec }) + (it.suffixe || '');
    const sz = fit(full, cellW * .9, PORTRAIT ? 150 : 140, 900);
    ctx.save(); ctx.globalAlpha *= clamp(p * 2);
    ctx.translate(0, (1 - eOut(p)) * 40 * U);
    text(str, cx, cy, { size: sz, weight: 900, color: T.accent });
    paragraph(it.label || '', cx, cy + sz * U * .75 + 10 * U, cellW * .9, { size: 42, weight: 600, color: T.texte, maxLignes: 2 });
    ctx.restore();
  });
};

// Coordonnées : cartes avec icônes (WhatsApp, Instagram, TikTok, téléphone...).
SCENES.contact = (l, d, s) => {
  const items = s.elements || [];
  const n = items.length || 1;
  let top, bottom, cx;
  if (PORTRAIT) {
    const yt = H * .14;
    if (s.marque !== false) SCENES.logoMini(l, W / 2, yt, s.marque || P.marque);
    titreHaut(s.titre || 'Contactez-nous', yt + (s.marque !== false ? 180 * U : 0), l, 56);
    top = yt + (s.marque !== false ? 330 * U : 150 * U); bottom = H * .86; cx = W / 2;
  } else {
    if (s.marque !== false) SCENES.logoMini(l, W * .23, H * .45, s.marque || P.marque, 1.3);
    cx = s.marque !== false ? W * .68 : W / 2;
    const p = eOut(prog(l, .3, .8)), titre = (s.titre || 'Contactez-nous').toUpperCase();
    text(titre, cx, H * .14, { size: fit(titre, W * .55, 56, 800, 6), weight: 800, sp: 6, alpha: p });
    top = H * .24; bottom = H * .92;
  }
  const cw = PORTRAIT ? W * .86 : (s.marque !== false ? W * .5 : W * .7);
  const gap = 28 * U;
  const ch = Math.min((bottom - top - gap * (n - 1)) / n, 300 * U);
  const y0 = top + (bottom - top - (n * ch + (n - 1) * gap)) / 2;
  items.forEach((it, i) => {
    const cy = y0 + i * (ch + gap) + ch / 2;
    const p = prog(l, .7 + i * .3, 1.3 + i * .3);
    if (p <= 0) return;
    carte(cx, cy, cw, ch, p);
    const icones = [].concat(it.icone || []);
    const valeurs = [].concat(it.valeurs || it.valeur || []);
    const x0 = cx - cw / 2 + 50 * U;
    const ir = Math.min(40 * U, ch * .16);
    const lignes = 1 + valeurs.length;
    const step = Math.min(ch / (lignes + .3), 90 * U);
    let y = cy - (lignes - 1) * step / 2;
    let tx = x0;
    icones.forEach((ic, k) => { icone(ic, x0 + ir + k * (ir * 2 + 18 * U), y, ir); tx = x0 + (k + 1) * (ir * 2 + 18 * U) + 8 * U; });
    const maxW = cx + cw / 2 - x0 - 40 * U;
    if (it.titre) text(it.titre, tx, y, { size: fit(it.titre, cx + cw / 2 - tx - 30 * U, 42, 800), weight: 800, align: 'left' });
    valeurs.forEach((v, k) => {
      text(v, x0, y + (k + 1) * step, { size: fit(v, maxW, Math.min(56, step / U * .7), 600), weight: 600, align: 'left', color: k === 0 && it.couleur !== false ? T.texte : T.texte });
    });
    ctx.restore();
  });
  if (s.pied) {
    const p = eOut(prog(l, 1.5, 2.1));
    text(s.pied, PORTRAIT ? W / 2 : W * .23, PORTRAIT ? H * .93 : H * .8, { size: fit(s.pied, PORTRAIT ? W * .86 : W * .36, 36, 500), weight: 500, color: T.doux, alpha: p });
  }
};
SCENES.logoMini = (l, x, y, nom, k = 1) => {
  if (!nom) return;
  const img = images[nom];
  const p = eOut(prog(l, 0, .6));
  ctx.save(); ctx.globalAlpha *= p; ctx.translate(x, y); ctx.scale(lerp(.8, 1, p), lerp(.8, 1, p));
  if (img) {
    const r = Math.min(W * .4 / img.width, 220 * U * k / img.height);
    ctx.drawImage(img, -img.width * r / 2, -img.height * r / 2, img.width * r, img.height * r);
  } else {
    const mots = nom.split(' ');
    const sz = fit(nom, (PORTRAIT ? W * .8 : W * .32), 110 * k, 900);
    const tw = measure(nom, sz, 900);
    let cx = -tw / 2;
    mots.forEach((m, i) => {
      const str = m + (i < mots.length - 1 ? ' ' : '');
      text(str, cx, 0, { size: sz, weight: 900, align: 'left', color: i === mots.length - 1 && mots.length > 1 ? T.accent : T.texte });
      cx += measure(str, sz, 900);
    });
  }
  ctx.restore();
};

// Appel à l'action : texte + bouton qui pulse.
SCENES.appel = (l, d, s) => {
  const lignes = s.lignes || [s.texte || 'Commandez maintenant'];
  let size = PORTRAIT ? 135 : 110;
  for (const ln of lignes) size = Math.min(size, fit(ln, W * .86, size, 900));
  const lh = size * 1.15 * U;
  const y0 = H * .42 - (lignes.length - 1) * lh / 2;
  lignes.forEach((ln, i) => {
    const p = eOut(prog(l, .1 + i * .15, .6 + i * .15));
    text(ln, W / 2, y0 + i * lh + (1 - p) * 40 * U, { size, weight: 900, alpha: p, color: i === lignes.length - 1 ? T.accent : T.texte });
  });
  const by = y0 + (lignes.length - .5) * lh + 150 * U;
  const pb = prog(l, .8, 1.3);
  if (pb > 0 && s.bouton) {
    const ic = s.icone ? 80 * U : 0;
    const bs = fit(s.bouton, W * .78 - ic, PORTRAIT ? 50 : 46, 800);
    const bw = measure(s.bouton, bs, 800) + 120 * U + ic, bh = 120 * U;
    const pulse = 1 + .04 * Math.sin(l * 6);
    const k = eBack(pb) * (pb >= 1 ? pulse : 1);
    ctx.save(); ctx.translate(W / 2, by); ctx.scale(k, k);
    const ring = (l * .9) % 1;
    ctx.strokeStyle = rgba(T.accent, (1 - ring) * .6); ctx.lineWidth = 4 * U;
    roundRect(-bw / 2 - ring * 30 * U, -bh / 2 - ring * 30 * U, bw + ring * 60 * U, bh + ring * 60 * U, bh); ctx.stroke();
    ctx.fillStyle = T.principal; ctx.shadowColor = T.accent; ctx.shadowBlur = 40 * U;
    roundRect(-bw / 2, -bh / 2, bw, bh, bh / 2); ctx.fill(); ctx.shadowBlur = 0;
    if (s.icone) { icone(s.icone, -bw / 2 + 60 * U + 18 * U, 0, 36 * U); text(s.bouton, ic / 2, 0, { size: bs, weight: 800 }); }
    else text(s.bouton, 0, 0, { size: bs, weight: 800 });
    ctx.restore();
  }
  if (s.detail) {
    const p = eOut(prog(l, 1.3, 1.9));
    paragraph(s.detail, W / 2, by + 150 * U, W * .84, { size: 42, weight: 500, color: T.doux, alpha: p, maxLignes: 2 });
  }
};

// Citation / avis client avec étoiles.
SCENES.avis = (l, d, s) => {
  const p0 = eOut(prog(l, 0, .6));
  text('“', W / 2, H * (PORTRAIT ? .27 : .2), { size: 300, weight: 900, color: T.principal, alpha: p0 });
  const nb = s.etoiles ?? 5;
  for (let i = 0; i < nb; i++) {
    const p = prog(l, .3 + i * .1, .7 + i * .1);
    if (p <= 0) continue;
    const x = W / 2 + (i - (nb - 1) / 2) * 80 * U, y = H * (PORTRAIT ? .36 : .33), r = 32 * U * eBack(p);
    ctx.fillStyle = '#FFC531'; ctx.beginPath();
    for (let k = 0; k < 10; k++) { const a = -Math.PI / 2 + k * Math.PI / 5, rr = k % 2 ? r * .45 : r; ctx.lineTo(x + Math.cos(a) * rr, y + Math.sin(a) * rr); }
    ctx.closePath(); ctx.fill();
  }
  const pt = eOut(prog(l, .7, 1.4));
  paragraph(s.texte || '', W / 2, H * .52 + (1 - pt) * 30 * U, W * .82, { size: PORTRAIT ? 60 : 58, weight: 600, alpha: pt, maxLignes: PORTRAIT ? 6 : 4 });
  const pa = eOut(prog(l, 1.4, 2));
  if (s.auteur) text('— ' + s.auteur, W / 2, H * (PORTRAIT ? .74 : .8), { size: 42, weight: 700, color: T.accent, alpha: pa });
};

// =====================================================================
//  TRANSITIONS  (centrées sur la frontière entre deux scènes)
// =====================================================================
// overlay : dessiné par-dessus ; transform : modifie la scène sortante/entrante.
const TRANSITIONS = {
  volet: { overlay(u) { // u : -1 → 1 (0 = frontière)
    const a = eInOut((u + 1) / 2), skew = .25 * W;
    const x0 = lerp(-W - skew, W + skew, a);
    ctx.fillStyle = T.principal;
    ctx.beginPath(); ctx.moveTo(x0, 0); ctx.lineTo(x0 + W, 0); ctx.lineTo(x0 + W - skew, H); ctx.lineTo(x0 - skew, H); ctx.closePath(); ctx.fill();
  } },
  rideau: { overlay(u) {
    const c = 1 - Math.abs(u), h = eInOut(c) * H / 2;
    ctx.fillStyle = T.principal; ctx.fillRect(0, 0, W, h); ctx.fillRect(0, H - h, W, h);
    ctx.fillStyle = T.accent; ctx.fillRect(0, h - 8 * U, W, 8 * U); ctx.fillRect(0, H - h, W, 8 * U);
  } },
  cercle: { overlay(u) {
    const c = eInOut(1 - Math.abs(u)), r = c * Math.hypot(W, H) / 2;
    ctx.fillStyle = T.principal; ctx.beginPath(); ctx.arc(W / 2, H / 2, r, 0, 6.283); ctx.fill();
  } },
  fondu: { overlay(u) { ctx.fillStyle = `rgba(0,0,0,${1 - Math.abs(u)})`; ctx.fillRect(0, 0, W, H); } },
  flash: { overlay(u) { ctx.fillStyle = `rgba(255,255,255,${Math.pow(1 - Math.abs(u), 2)})`; ctx.fillRect(0, 0, W, H); } },
  zoom: {
    transform(u) { // u < 0 : scène sortante, u > 0 : entrante
      const k = u < 0 ? lerp(1, 1.6, eIn(1 + u)) : lerp(.6, 1, eOut(u));
      ctx.translate(W / 2, H / 2); ctx.scale(k, k); ctx.translate(-W / 2, -H / 2);
      ctx.globalAlpha *= u < 0 ? 1 + u : u;
    },
    overlay(u) { ctx.fillStyle = `rgba(255,255,255,${.5 * Math.pow(1 - Math.abs(u), 3)})`; ctx.fillRect(0, 0, W, H); }
  },
  glisse: { transform(u) { ctx.translate(u < 0 ? lerp(0, -W, eIn(1 + u)) : lerp(W, 0, eOut(u)), 0); } },
  aucune: {},
};

// =====================================================================
//  CHARGEMENT ET RENDU
// =====================================================================
function initCanvas(w, h) {
  cv = document.getElementById('c');
  W = cv.width = w; H = cv.height = h;
  ctx = cv.getContext('2d');
  U = Math.min(W, H) / 1080;
  PORTRAIT = H > W * 1.1; PAYSAGE = W > H * 1.1;
}

// projet : objet JSON ; fichiers : { nom: url } pour les images (data: ou blob:)
async function charger(projet, w, h, fichiers = {}) {
  initCanvas(w, h);
  P = projet;
  T = Object.assign({}, THEME_DEFAUT, projet.theme || {});
  timeline = []; DUREE = 0;
  for (const sc of projet.scenes || []) {
    const duree = sc.duree || 3.5;
    timeline.push({ debut: DUREE, duree, scene: sc });
    DUREE += duree;
  }
  for (const k in images) delete images[k];
  await Promise.all(Object.entries(fichiers).map(([nom, url]) => new Promise(res => {
    const img = new Image();
    img.onload = () => { images[nom] = img; res(); };
    img.onerror = () => { console.warn('Image introuvable : ' + nom); res(); };
    img.src = url;
  })));
  await Promise.all([400, 600, 700, 800, 900].map(wt => document.fonts.load(`${wt} 20px Inter`)));
  return { duree: DUREE, frontieres: timeline.slice(1).map(e => e.debut) };
}

function transitionApres(i) {
  if (i < 0 || i >= timeline.length - 1) return null;
  const nom = timeline[i].scene.transition || P.transition || 'volet';
  return TRANSITIONS[nom] || TRANSITIONS.volet;
}

function dessinerScene(i, t) {
  const e = timeline[i];
  const l = t - e.debut;
  const fn = SCENES[e.scene.type];
  ctx.save();
  // transformation de transition (sortie / entrée)
  const trOut = transitionApres(i), trIn = transitionApres(i - 1);
  if (trOut && trOut.transform && l > e.duree - TR) trOut.transform((l - e.duree) / TR);
  else if (trIn && trIn.transform && l < TR) trIn.transform(l / TR);
  // fondu de sortie quand la transition ne cache pas l'écran
  if (trOut && !trOut.transform && trOut !== TRANSITIONS.volet && trOut !== TRANSITIONS.cercle && trOut !== TRANSITIONS.rideau)
    ctx.globalAlpha *= 1 - eIn(prog(l, e.duree - .35, e.duree));
  if (fn) fn(l, e.duree, e.scene);
  else text('Scène inconnue : ' + e.scene.type, W / 2, H / 2, { size: 50 });
  ctx.restore();
}

function render(t) {
  ctx.setTransform(1, 0, 0, 1, 0, 0);
  ctx.globalAlpha = 1;
  fond(t);
  const i = timeline.findIndex(e => t >= e.debut && t < e.debut + e.duree);
  const idx = i < 0 ? timeline.length - 1 : i;
  if (!timeline[idx]) return;
  dessinerScene(idx, t);
  // superpositions de transition
  timeline.forEach((sc, k) => {
    const tr = transitionApres(k);
    if (!tr || !tr.overlay) return;
    const b = sc.debut + sc.duree, u = (t - b) / TR;
    if (u > -1 && u < 1) { ctx.save(); tr.overlay(u); ctx.restore(); }
  });
  // fondu au noir final
  if (P.fonduFinal !== false) {
    const fo = prog(t, DUREE - .6, DUREE);
    if (fo > 0) { ctx.fillStyle = `rgba(0,0,0,${fo})`; ctx.fillRect(0, 0, W, H); }
  }
}

window.Moteur = { charger, render, get duree() { return DUREE; }, SCENES, TRANSITIONS, DECORS };
})();
