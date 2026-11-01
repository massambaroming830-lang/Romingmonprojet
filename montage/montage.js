#!/usr/bin/env node
// =====================================================================
//  Outil de montage vidéo (basé sur ffmpeg)
//  Assemble des vidéos et des photos décrites dans un fichier JSON :
//  découpe, recadrage vertical/horizontal, transitions, textes, musique.
//
//  node montage.js exemple.json
//  node montage.js exemple.json --format youtube      (remplace le format du JSON)
//  Requis : ffmpeg et ffprobe.
// =====================================================================
const { spawnSync } = require('child_process');
const fs = require('fs');
const os = require('os');
const path = require('path');

const FORMATS = { tiktok: [1080, 1920], youtube: [1920, 1080], carre: [1080, 1080], post: [1080, 1350] };
const IMAGES = ['.jpg', '.jpeg', '.png', '.webp', '.bmp'];
// Noms de transitions en français → filtres xfade de ffmpeg (les noms ffmpeg marchent aussi)
const TRANSITIONS = {
  fondu: 'fade', noir: 'fadeblack', blanc: 'fadewhite', dissoudre: 'dissolve',
  'glisse-gauche': 'slideleft', 'glisse-droite': 'slideright', 'glisse-haut': 'slideup', 'glisse-bas': 'slidedown',
  'volet-gauche': 'wipeleft', 'volet-droite': 'wiperight', 'volet-haut': 'wipeup', 'volet-bas': 'wipedown',
  cercle: 'circleopen', 'cercle-ferme': 'circleclose', zoom: 'zoomin', pixel: 'pixelize', flou: 'hblur',
  rideau: 'vertopen', diagonale: 'diagtl', radial: 'radial', coupe: null, aucune: null,
};
const POLICE = path.join(__dirname, '..', 'modeles', 'polices', 'Inter-Bold.otf');

const args = process.argv.slice(2);
const opt = (nom, def) => { const i = args.indexOf('--' + nom); return i < 0 ? def : args[i + 1]; };
const fichierJSON = args.find(a => a.endsWith('.json'));
if (!fichierJSON) { console.log('Usage : node montage.js <montage.json> [--format tiktok|youtube|carre|post]'); process.exit(1); }
const M = JSON.parse(fs.readFileSync(fichierJSON, 'utf8'));
const base = path.dirname(path.resolve(fichierJSON));
const chemin = f => path.resolve(base, f);

const format = opt('format', M.format || 'tiktok');
const [W, H] = FORMATS[format] || String(format).split('x').map(Number);
const FPS = M.fps || 30;
const REMPLI = M.remplissage || 'flou';   // flou | recadrer | noir
const trDefaut = M.transition || { type: 'fondu', duree: 0.5 };
const tmp = fs.mkdtempSync(path.join(os.tmpdir(), 'montage-'));

function sonde(f) {
  const r = spawnSync('ffprobe', ['-v', 'error', '-show_entries', 'format=duration:stream=codec_type,width,height', '-of', 'json', f], { encoding: 'utf8' });
  if (r.status !== 0) throw new Error('Fichier illisible : ' + f);
  const j = JSON.parse(r.stdout);
  const v = j.streams.find(s => s.codec_type === 'video') || {};
  return { duree: +j.format.duration || 0, son: j.streams.some(s => s.codec_type === 'audio'), w: v.width, h: v.height };
}
const num = x => (+x).toFixed(3);

// Mise au format : remplit W×H selon le mode choisi
function cadrage(entree, sortie, mode, w = W, h = H) {
  if (mode === 'recadrer')
    return `[${entree}]scale=${w}:${h}:force_original_aspect_ratio=increase,crop=${w}:${h},setsar=1[${sortie}]`;
  if (mode === 'noir')
    return `[${entree}]scale=${w}:${h}:force_original_aspect_ratio=decrease,pad=${w}:${h}:(ow-iw)/2:(oh-ih)/2:black,setsar=1[${sortie}]`;
  // flou : la vidéo entière au centre, une version floutée et agrandie derrière
  return `[${entree}]split=2[${sortie}a][${sortie}b];` +
    `[${sortie}a]scale=${Math.round(w / 4)}:${Math.round(h / 4)}:force_original_aspect_ratio=increase,crop=${Math.round(w / 4)}:${Math.round(h / 4)},gblur=sigma=12,scale=${w}:${h},eq=brightness=-0.12[${sortie}f];` +
    `[${sortie}b]scale=${w}:${h}:force_original_aspect_ratio=decrease[${sortie}c];` +
    `[${sortie}f][${sortie}c]overlay=(W-w)/2:(H-h)/2,setsar=1[${sortie}]`;
}

// Mouvement « Ken Burns » pour les photos
function mouvement(type, d) {
  const n = Math.max(1, Math.round(d * FPS));
  const z = { 'zoom-avant': `1+0.15*on/${n}`, 'zoom-arriere': `1.15-0.15*on/${n}` }[type] || '1.12';
  const x = { gauche: `(iw-iw/zoom)*(1-on/${n})`, droite: `(iw-iw/zoom)*on/${n}` }[type] || 'iw/2-(iw/zoom/2)';
  return `zoompan=z='${z}':x='${x}':y='ih/2-(ih/zoom/2)':d=${n}:s=${W}x${H}:fps=${FPS}`;
}

const inputs = [], filtres = [], clips = [];
M.clips.forEach((c, i) => {
  const f = chemin(c.fichier);
  if (!fs.existsSync(f)) throw new Error('Fichier introuvable : ' + c.fichier);
  const estImage = IMAGES.includes(path.extname(f).toLowerCase());
  const vitesse = c.vitesse || 1;
  let duree, son = false;
  if (estImage) {
    duree = c.duree || 3;
    inputs.push('-loop', '1', '-framerate', String(FPS), '-t', num(duree), '-i', f);
    // photo mise au format en 2× puis animée (évite les tremblements du zoom)
    filtres.push(cadrage(`${i}:v`, `p${i}`, c.remplissage || REMPLI, W * 2, H * 2));
    filtres.push(`[p${i}]${mouvement(c.mouvement || 'zoom-avant', duree)},trim=duration=${num(duree)},setpts=PTS-STARTPTS,format=yuv420p[v${i}]`);
  } else {
    const info = sonde(f);
    const debut = c.debut || 0, fin = Math.min(c.fin || info.duree, info.duree);
    duree = (fin - debut) / vitesse;
    son = info.son && c.son !== false && M.sonDesClips !== false;
    inputs.push('-ss', num(debut), '-t', num(fin - debut), '-i', f);
    filtres.push(`[${i}:v]setpts=(PTS-STARTPTS)/${vitesse},fps=${FPS}[r${i}]`);
    filtres.push(cadrage(`r${i}`, `q${i}`, c.remplissage || REMPLI));
    filtres.push(`[q${i}]format=yuv420p[v${i}]`);
    if (son) {
      const atempo = vitesse !== 1 ? `,atempo=${Math.min(2, Math.max(0.5, vitesse))}` : '';
      filtres.push(`[${i}:a]asetpts=PTS-STARTPTS${atempo},aresample=48000,aformat=channel_layouts=stereo,volume=${c.volume ?? 1},apad,atrim=duration=${num(duree)}[a${i}]`);
    }
  }
  if (!son) filtres.push(`anullsrc=r=48000:cl=stereo,atrim=duration=${num(duree)}[a${i}]`);
  clips.push({ duree });
});

// Enchaînement avec transitions (xfade pour l'image, acrossfade pour le son)
let v = 'v0', a = 'a0', t = clips[0].duree;
for (let i = 1; i < clips.length; i++) {
  const tr = M.clips[i].transition ?? trDefaut;
  const o = typeof tr === 'string' ? { type: tr } : tr;
  const nomTr = o.type in TRANSITIONS ? TRANSITIONS[o.type] : o.type;
  const d = nomTr ? Math.min(o.duree || 0.5, clips[i - 1].duree / 2, clips[i].duree / 2) : 0;
  if (nomTr) {
    filtres.push(`[${v}][v${i}]xfade=transition=${nomTr}:duration=${num(d)}:offset=${num(t - d)}[x${i}]`);
    filtres.push(`[${a}][a${i}]acrossfade=d=${num(d)}[y${i}]`);
  } else {
    filtres.push(`[${v}][v${i}]concat=n=2:v=1:a=0[x${i}]`);
    filtres.push(`[${a}][a${i}]concat=n=2:v=0:a=1[y${i}]`);
  }
  v = `x${i}`; a = `y${i}`; t += clips[i].duree - d;
}
const total = t;

// Textes superposés
(M.textes || []).forEach((tx, k) => {
  const fichierTexte = path.join(tmp, `texte${k}.txt`);
  fs.writeFileSync(fichierTexte, tx.texte);
  const taille = Math.round((tx.taille || 64) * Math.min(W, H) / 1080);
  const d0 = tx.debut || 0, d1 = tx.fin ?? total, f = 0.3;
  const y = { haut: `h*0.12`, centre: `(h-text_h)/2`, bas: `h*0.80-text_h` }[tx.position || 'bas'] || tx.position;
  const alpha = `if(lt(t,${d0 + f}),(t-${d0})/${f},if(gt(t,${d1 - f}),(${d1}-t)/${f},1))`;
  const boite = tx.fond === false ? '' : `:box=1:boxcolor=${tx.couleurFond || 'black@0.55'}:boxborderw=${Math.round(taille * 0.4)}`;
  filtres.push(`[${v}]drawtext=fontfile='${(tx.police ? chemin(tx.police) : POLICE).replace(/'/g, "\\'")}':textfile='${fichierTexte}':` +
    `fontsize=${taille}:fontcolor=${tx.couleur || 'white'}:line_spacing=${Math.round(taille * 0.25)}:x=(w-text_w)/2:y=${y}` +
    `${boite}:alpha='${alpha}':enable='between(t,${d0},${d1})'[t${k}]`);
  v = `t${k}`;
});

// Musique et voix off
let n = M.clips.length;
const pistes = [`[${a}]`];
if (M.voix) {
  const vx = typeof M.voix === 'string' ? { fichier: M.voix } : M.voix;
  inputs.push('-i', chemin(vx.fichier));
  filtres.push(`[${n}:a]aresample=48000,aformat=channel_layouts=stereo,adelay=${Math.round((vx.debut || 0) * 1000)}:all=1,volume=${vx.volume ?? 1}[vx]`);
  pistes.push('[vx]'); n++;
}
if (M.musique) {
  const mu = typeof M.musique === 'string' ? { fichier: M.musique } : M.musique;
  inputs.push('-stream_loop', '-1', '-ss', num(mu.debut || 0), '-i', chemin(mu.fichier));
  const fo = mu.fonduSortie ?? 2;
  filtres.push(`[${n}:a]aresample=48000,aformat=channel_layouts=stereo,atrim=duration=${num(total)},volume=${mu.volume ?? 0.6},` +
    `afade=t=in:d=${mu.fonduEntree ?? 0.5},afade=t=out:st=${num(Math.max(0, total - fo))}:d=${fo}[mu]`);
  if (mu.baisserSousVoix !== false && pistes.length) {
    // la musique baisse automatiquement quand on parle (son des clips + voix off)
    filtres.push(`${pistes.join('')}amix=inputs=${pistes.length}:normalize=0,asplit=2[pa][pb]`);
    filtres.push(`[mu][pb]sidechaincompress=threshold=0.02:ratio=10:attack=15:release=500[mud]`);
    filtres.push(`[pa][mud]amix=inputs=2:normalize=0[audio]`);
  } else filtres.push(`${pistes.join('')}[mu]amix=inputs=${pistes.length + 1}:normalize=0[audio]`);
} else filtres.push(`${pistes.join('')}amix=inputs=${pistes.length}:normalize=0[audio]`);
filtres.push(`[audio]alimiter=limit=0.95,atrim=duration=${num(total)}[aout]`);
filtres.push(`[${v}]trim=duration=${num(total)}[vout]`);

const sortie = path.resolve(base, opt('sortie', M.sortie ? M.sortie.replace('{format}', format) : `montage_${format}.mp4`));
fs.mkdirSync(path.dirname(sortie), { recursive: true });
const script = path.join(tmp, 'filtres.txt');
fs.writeFileSync(script, filtres.join(';\n'));
console.log(`Montage : ${M.clips.length} clips, ${total.toFixed(1)} s, ${W}×${H} → ${sortie}`);
const r = spawnSync('ffmpeg', ['-y', '-hide_banner', '-loglevel', 'error', '-stats', ...inputs, '-filter_complex_script', script,
  '-map', '[vout]', '-map', '[aout]', '-c:v', 'libx264', '-preset', 'veryfast', '-crf', '19', '-pix_fmt', 'yuv420p', '-r', String(FPS),
  '-c:a', 'aac', '-b:a', '192k', '-movflags', '+faststart', sortie], { stdio: 'inherit' });
if (r.status === 0) console.log('✔ ' + sortie);
else { console.error('✘ Échec ffmpeg — filtres dans ' + script); process.exit(1); }
fs.rmSync(tmp, { recursive: true, force: true });
