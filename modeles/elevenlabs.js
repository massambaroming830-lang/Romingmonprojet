// =====================================================================
//  Voix off ElevenLabs
//  Chaque scène peut avoir un texte "voix" : il est lu par une voix ElevenLabs,
//  et la durée de la scène s'allonge si la phrase est plus longue que prévu.
//
//  Clé API : variable d'environnement ELEVENLABS_API_KEY
//  (ElevenLabs → Profil → API Keys ; permission « Text to Speech » requise,
//   « Voices : lecture » pour lister les voix).
//
//  Lister les voix disponibles :  node elevenlabs.js --liste
// =====================================================================
const { spawnSync } = require('child_process');
const crypto = require('crypto');
const fs = require('fs');
const path = require('path');

const API = 'https://api.elevenlabs.io/v1';
const VOIX_DEFAUT = 'JBFqnCBsd6RMkjVDRZzb';   // voix prédéfinie d'ElevenLabs ; change-la avec "voix" dans le JSON
const MODELE_DEFAUT = 'eleven_multilingual_v2';  // parle très bien français

function cle() {
  const k = process.env.ELEVENLABS_API_KEY;
  if (!k) throw new Error('Variable ELEVENLABS_API_KEY absente (ta clé API ElevenLabs).');
  return k;
}

async function appel(url, options = {}) {
  const r = await fetch(API + url, { ...options, headers: { 'xi-api-key': cle(), ...(options.headers || {}) } });
  if (!r.ok) {
    let msg = await r.text();
    try { const j = JSON.parse(msg); msg = (j.detail && (j.detail.message || j.detail)) || msg; } catch (e) {}
    throw new Error(`ElevenLabs ${r.status} : ${typeof msg === 'string' ? msg : JSON.stringify(msg)}`);
  }
  return r;
}

async function listerVoix() {
  const j = await (await appel('/voices')).json();
  return j.voices.map(v => ({ id: v.voice_id, nom: v.name, labels: v.labels || {} }));
}

// Accepte un identifiant de voix ou un nom (« Charlotte »)
async function resoudreVoix(v) {
  if (!v) return VOIX_DEFAUT;
  if (/^[A-Za-z0-9]{20}$/.test(v)) return v;
  const trouvee = (await listerVoix()).find(x => x.nom.toLowerCase().startsWith(v.toLowerCase()));
  if (!trouvee) throw new Error(`Voix « ${v} » introuvable dans ton compte ElevenLabs (node elevenlabs.js --liste).`);
  return trouvee.id;
}

function dureeAudio(f) {
  const r = spawnSync('ffprobe', ['-v', 'error', '-show_entries', 'format=duration', '-of', 'csv=p=0', f], { encoding: 'utf8' });
  return +r.stdout.trim() || 0;
}

// Génère les voix de toutes les scènes, ajuste les durées et crée une piste unique.
// Retourne le chemin du fichier .wav de la voix off (ou null s'il n'y a aucun texte).
async function voixOff(projet, dossierCache, nom) {
  const scenes = projet.scenes || [];
  if (!scenes.some(s => s.voix)) return null;
  const cfg = Object.assign({}, (projet.audio || {}).elevenlabs);
  const voiceId = await resoudreVoix(cfg.voix);
  const modele = cfg.modele || MODELE_DEFAUT;
  const reglages = {
    stability: cfg.stabilite ?? 0.45, similarity_boost: cfg.similarite ?? 0.8,
    style: cfg.style ?? 0.35, use_speaker_boost: true, speed: cfg.vitesse ?? 1.0,
  };
  fs.mkdirSync(dossierCache, { recursive: true });

  const morceaux = [];
  let debut = 0;
  for (let i = 0; i < scenes.length; i++) {
    const s = scenes[i];
    s.duree = s.duree || 3.5;
    if (s.voix) {
      const corps = {
        text: s.voix, model_id: modele, voice_settings: reglages, language_code: cfg.langue || 'fr',
        // contexte : la voix garde la même intonation d'une phrase à l'autre
        previous_text: scenes.slice(0, i).map(x => x.voix).filter(Boolean).join(' ') || undefined,
        next_text: scenes.slice(i + 1).map(x => x.voix).filter(Boolean).join(' ') || undefined,
      };
      const hash = crypto.createHash('sha1').update(JSON.stringify([voiceId, corps])).digest('hex').slice(0, 12);
      const fichier = path.join(dossierCache, `${nom}_${i + 1}_${hash}.mp3`);
      if (!fs.existsSync(fichier)) {   // déjà généré = pas de crédits dépensés à nouveau
        process.stdout.write(`🎙  Voix scène ${i + 1} : « ${s.voix} »\n`);
        const r = await appel(`/text-to-speech/${voiceId}?output_format=mp3_44100_128`, {
          method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(corps),
        });
        fs.writeFileSync(fichier, Buffer.from(await r.arrayBuffer()));
      }
      const d = dureeAudio(fichier);
      const decalage = s.voixDecalage ?? 0.35;
      // la scène dure au moins le temps de la phrase + une respiration
      const mini = decalage + d + (s.voixPause ?? 0.45);
      if (s.duree < mini) s.duree = +mini.toFixed(2);
      morceaux.push({ fichier, debut: debut + decalage });
    }
    debut += s.duree;
  }

  // Assemble toutes les phrases sur une seule piste
  const sortie = path.join(dossierCache, `${nom}_voix.wav`);
  const entrees = morceaux.flatMap(m => ['-i', m.fichier]);
  const filtres = morceaux.map((m, k) => `[${k}:a]aresample=44100,aformat=channel_layouts=stereo,adelay=${Math.round(m.debut * 1000)}:all=1[v${k}]`);
  filtres.push(morceaux.map((m, k) => `[v${k}]`).join('') + `amix=inputs=${morceaux.length}:normalize=0,apad,atrim=0:${debut.toFixed(3)}[out]`);
  const r = spawnSync('ffmpeg', ['-y', '-loglevel', 'error', ...entrees, '-filter_complex', filtres.join(';'), '-map', '[out]', sortie], { stdio: 'inherit' });
  if (r.status !== 0) throw new Error('Assemblage de la voix off impossible');
  return sortie;
}

module.exports = { voixOff, listerVoix };

if (require.main === module && process.argv.includes('--liste')) {
  listerVoix().then(v => {
    for (const x of v) console.log(`${x.id}  ${x.nom.padEnd(28)} ${Object.values(x.labels).join(', ')}`);
  }).catch(e => { console.error('✘ ' + e.message); process.exit(1); });
}
