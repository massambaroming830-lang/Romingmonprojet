# Romingmonprojet

Vidéos motion design de **MING Store** (import & export entre la Chine, Dubaï, la Turquie
et les pays africains).

| Dossier | Contenu |
|---|---|
| [`modeles/`](modeles/LISEZ-MOI.md) | **Modèles de vidéos motion design** : une vidéo = un fichier JSON (promo, nouvel arrivage, présentation, collection luxe…), 6 styles (classique, néon, minimal, pop, wax, luxe), voix off ElevenLabs, export TikTok, YouTube, carré et post Instagram, musique générée |
| [`montage/`](montage/LISEZ-MOI.md) | **Outil de montage** : assembler vidéos et photos avec découpe, transitions, textes, musique et voix off |
| `video/` | La première vidéo de présentation MING Store (23 s) |

```bash
cd modeles && node rendu.js projets/promo-produit.json --format tous
cd montage && node montage.js exemple.json
```

## Première vidéo MING Store

### Vidéos (23 s, voix off française + musique originale)

| Format | Fichier |
|---|---|
| TikTok / Instagram / statut WhatsApp (vertical) | [`video/MING_Store_TikTok_1080x1920.mp4`](video/MING_Store_TikTok_1080x1920.mp4) |
| YouTube / Facebook (horizontal) | [`video/MING_Store_YouTube_1920x1080.mp4`](video/MING_Store_YouTube_1920x1080.mp4) |

Scènes : logo MING Store → « Import & Export » → routes Chine / Dubaï / Turquie → Afrique
→ « Le monde à portée de votre business » → contacts WhatsApp, Instagram et TikTok.

### Modifier et refaire la vidéo

- `video/animation.html` : l'animation (textes, couleurs, numéros). Ouvre-la dans un navigateur pour un aperçu.
- `video/music.py` : génère la musique `music_bed.wav`.
- `video/voiceover.py` : génère la voix off `voice.wav` (Kokoro TTS + espeak-ng), mixée dans `music.wav`.
- `video/render.js` : exporte en MP4 (Node.js, Playwright et ffmpeg requis).

```bash
cd video
python3 music.py music.wav
node render.js 1080 1920 MING_Store_TikTok_1080x1920.mp4
node render.js 1920 1080 MING_Store_YouTube_1920x1080.mp4
```
