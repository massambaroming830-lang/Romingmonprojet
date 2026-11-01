#!/usr/bin/env node
// =====================================================================
//  Exporte un projet (fichier JSON) en vidéo MP4.
//
//  node rendu.js projets/promo-produit.json                 → format TikTok
//  node rendu.js projets/promo-produit.json --format tous   → TikTok + YouTube + carré + post
//  node rendu.js projets/promo-produit.json --apercu        → quelques images PNG pour vérifier
//
//  Options : --format tiktok|youtube|carre|post|tous   --fps 30   --sortie dossier/
//            --apercu [t1,t2,...]   --muet   --sans-voix
//  Voix off : ajoute "voix": "texte" aux scènes ; elle est générée par ElevenLabs
//  (clé dans la variable ELEVENLABS_API_KEY). Voir elevenlabs.js.
//  Requis : Node.js, Playwright (Chromium), ffmpeg ; Python 3 + numpy pour la musique auto.
// =====================================================================
const { chromium } = require('playwright');
const { spawn, spawnSync } = require('child_process');
const fs = require('fs');
const path = require('path');

const FORMATS = { tiktok: [1080, 1920], youtube: [1920, 1080], carre: [1080, 1080], post: [1080, 1350] };
const MIME = { '.png': 'image/png', '.jpg': 'image/jpeg', '.jpeg': 'image/jpeg', '.webp': 'image/webp', '.gif': 'image/gif', '.svg': 'image/svg+xml' };

const args = process.argv.slice(2);
const opt = (nom, def) => { const i = args.indexOf('--' + nom); if (i < 0) return def; const v = args[i + 1]; return v && !v.startsWith('--') ? v : true; };
const fichierProjet = args.find(a => a.endsWith('.json'));
if (!fichierProjet) {
  console.log('Usage : node rendu.js <projet.json> [--format tiktok|youtube|carre|post|tous] [--apercu] [--muet]');
  process.exit(1);
}
const projet = JSON.parse(fs.readFileSync(fichierProjet, 'utf8'));
const dossierProjet = path.dirname(path.resolve(fichierProjet));
const nom = path.basename(fichierProjet, '.json');
const fps = +opt('fps', projet.fps || 30);
const formatOpt = opt('format', projet.format || 'tiktok');
const formats = formatOpt === 'tous' ? Object.keys(FORMATS) : String(formatOpt).split(',');
const sortie = path.resolve(opt('sortie', path.join(dossierProjet, '..', 'sortie')));
fs.mkdirSync(sortie, { recursive: true });

// Toutes les images citées dans le projet (logo, photos), converties en data: URL
function imagesDuProjet() {
  const noms = new Set();
  if (projet.theme && projet.theme.logo) noms.add(projet.theme.logo);
  for (const s of projet.scenes || []) {
    for (const k of ['image', 'fichier']) if (s[k]) noms.add(s[k]);
    if (typeof s.marque === 'string') noms.add(s.marque);
  }
  if (projet.marque) noms.add(projet.marque);
  const out = {};
  for (const n of noms) {
    const p = path.resolve(dossierProjet, n);
    const mime = MIME[path.extname(n).toLowerCase()];
    if (!mime) continue;
    if (!fs.existsSync(p)) { console.warn(`⚠ Image introuvable : ${n} (un emplacement « Votre photo ici » sera affiché)`); continue; }
    out[n] = `data:${mime};base64,` + fs.readFileSync(p).toString('base64');
  }
  return out;
}

// Prépare la bande-son : musique (fichier ou générée) + voix off éventuelle
function preparerAudio(duree, frontieres) {
  if (opt('muet')) return null;
  const audio = projet.audio || {};
  let musique = null;
  if (audio.musique && audio.musique !== 'auto') {
    musique = path.resolve(dossierProjet, audio.musique);
    if (!fs.existsSync(musique)) { console.warn('⚠ Musique introuvable : ' + audio.musique); musique = null; }
  } else if (audio.musique !== false) {
    musique = path.join(sortie, `${nom}_musique.wav`);
    const r = spawnSync('python3', [path.join(__dirname, 'musique.py'), musique, '--duree', String(duree),
      '--ambiance', audio.ambiance || 'energique', '--transitions', frontieres.join(','),
      ...(audio.bpm ? ['--bpm', String(audio.bpm)] : [])], { stdio: 'inherit' });
    if (r.status !== 0) { console.warn('⚠ Musique non générée (python3 + numpy requis)'); musique = null; }
  }
  const voix = audio.voix ? path.resolve(dossierProjet, audio.voix) : null;
  return { musique, voix: voix && fs.existsSync(voix) ? voix : null, volume: audio.volumeMusique ?? (voix ? 0.45 : 1) };
}

function argsAudio(a, duree) {
  if (!a || (!a.musique && !a.voix)) return { inputs: [], map: [] };
  const inputs = [], filtres = [];
  let n = 1;
  if (a.musique) { inputs.push('-stream_loop', '-1', '-i', a.musique); filtres.push(`[${n}:a]atrim=0:${duree},afade=t=out:st=${Math.max(0, duree - 1.5)}:d=1.5,volume=${a.volume}[m]`); n++; }
  if (a.voix) { inputs.push('-i', a.voix); filtres.push(`[${n}:a]aresample=44100,aformat=channel_layouts=stereo,apad,atrim=0:${duree}[v]`); n++; }
  let sortieA;
  if (a.musique && a.voix) {
    // la musique baisse automatiquement quand la voix parle
    filtres.push('[v]asplit=2[v1][v2]', '[m][v1]sidechaincompress=threshold=0.03:ratio=8:attack=20:release=400[md]', '[md][v2]amix=inputs=2:normalize=0[a]');
    sortieA = '[a]';
  } else sortieA = a.musique ? '[m]' : '[v]';
  return { inputs, map: ['-filter_complex', filtres.join(';'), '-map', '0:v', '-map', sortieA, '-c:a', 'aac', '-b:a', '192k'] };
}

(async () => {
  // Voix off ElevenLabs (avant tout : elle peut allonger les scènes)
  if (!opt('muet') && !opt('sans-voix') && !opt('apercu') && (projet.scenes || []).some(s => s.voix)) {
    try {
      const voix = await require('./elevenlabs').voixOff(projet, path.join(sortie, 'voix'), nom);
      if (voix) { projet.audio = Object.assign({}, projet.audio, { voix }); console.log('✔ Voix off ElevenLabs : ' + voix); }
    } catch (e) {
      console.warn('⚠ Voix off non générée — ' + e.message + '\n  La vidéo sera faite sans voix.');
    }
  }
  const fichiers = imagesDuProjet();
  const browser = await chromium.launch();
  let audio;
  for (const f of formats) {
    const [W, H] = FORMATS[f] || f.split('x').map(Number);
    if (!W || !H) { console.warn('Format inconnu : ' + f); continue; }
    const page = await browser.newPage({ viewport: { width: W, height: H } });
    page.on('console', m => { if (m.type() === 'warning' || m.type() === 'error') console.warn('  [page] ' + m.text()); });
    await page.goto('file://' + path.join(__dirname, 'moteur.html') + '?render=1');
    const info = await page.evaluate(([p, w, h, fi]) => Moteur.charger(p, w, h, fi), [projet, W, H, fichiers]);
    const grab = async (t, type = 'image/png') => Buffer.from(await page.evaluate(([t, type]) => {
      Moteur.render(t); return document.getElementById('c').toDataURL(type, 0.95).split(',')[1];
    }, [t, type]), 'base64');

    const apercu = opt('apercu');
    if (apercu) {
      // par défaut : le milieu de chaque scène
      let instants = typeof apercu === 'string' ? apercu.split(',').map(Number) : [];
      if (!instants.length) { let d = 0; for (const s of projet.scenes) { instants.push(+(d + (s.duree || 3.5) * .7).toFixed(2)); d += s.duree || 3.5; } }
      for (const t of instants) {
        const fp = path.join(sortie, `${nom}_${f}_${t}s.png`);
        fs.writeFileSync(fp, await grab(t));
        console.log('Aperçu : ' + fp);
      }
      await page.close();
      continue;
    }

    if (audio === undefined) audio = preparerAudio(info.duree, info.frontieres);
    const out = path.join(sortie, `${nom}_${f}.mp4`);
    const a = argsAudio(audio, info.duree);
    const ff = spawn('ffmpeg', ['-y', '-loglevel', 'error', '-f', 'image2pipe', '-framerate', String(fps), '-i', '-', ...a.inputs,
      ...a.map, '-t', String(info.duree), '-c:v', 'libx264', '-preset', 'veryfast', '-crf', '18', '-pix_fmt', 'yuv420p',
      '-movflags', '+faststart', out], { stdio: ['pipe', 'inherit', 'inherit'] });
    const total = Math.round(info.duree * fps);
    const debut = Date.now();
    for (let i = 0; i < total; i++) {
      const buf = await grab(i / fps);
      if (!ff.stdin.write(buf)) await new Promise(r => ff.stdin.once('drain', r));
      if (i % fps === 0) process.stdout.write(`\r${f} : ${Math.round(i / total * 100)} %   `);
    }
    ff.stdin.end();
    const code = await new Promise(r => ff.on('close', r));
    console.log(`\r${code === 0 ? '✔' : '✘'} ${out}  (${info.duree.toFixed(1)} s, ${((Date.now() - debut) / 1000).toFixed(0)} s de rendu)`);
    await page.close();
  }
  await browser.close();
})();
