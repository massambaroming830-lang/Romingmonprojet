# Romingmonprojet

Mon premier projet : la vidéo de présentation en motion design de **MING Store**
(import & export entre la Chine, Dubaï, la Turquie et les pays africains).

## Vidéos (23 s, voix off française + musique originale)

| Format | Fichier |
|---|---|
| TikTok / Instagram / statut WhatsApp (vertical) | [`video/MING_Store_TikTok_1080x1920.mp4`](video/MING_Store_TikTok_1080x1920.mp4) |
| YouTube / Facebook (horizontal) | [`video/MING_Store_YouTube_1920x1080.mp4`](video/MING_Store_YouTube_1920x1080.mp4) |

Scènes : logo MING Store → « Import & Export » → routes Chine / Dubaï / Turquie → Afrique
→ « Le monde à portée de votre business » → contacts WhatsApp, Instagram et TikTok.

## Extrait « paroles synchronisées » (26 s)

Montage dans le style « motion design typographique » : chaque mot de la voix off apparaît à l'écran
à l'instant exact où il est prononcé, avec des sous-titres karaoké (le mot dit s'allume en rouge).

| Format | Fichier |
|---|---|
| TikTok / Instagram / statut WhatsApp (vertical) | [`video/MING_Store_Extrait_TikTok_1080x1920.mp4`](video/MING_Store_Extrait_TikTok_1080x1920.mp4) |
| YouTube / Facebook (horizontal) | [`video/MING_Store_Extrait_YouTube_1920x1080.mp4`](video/MING_Store_Extrait_YouTube_1920x1080.mp4) |

- `video/extrait_audio.py` : texte de la voix off ; génère `extrait.wav` (voix + musique) et `extrait_timings.js` (minutage de chaque mot).
- `video/extrait.html` : l'animation, calée sur `extrait_timings.js`. Ouvre-la dans un navigateur et clique pour l'aperçu avec le son.

```bash
cd video
python3 extrait_audio.py kokoro-v1.0.onnx voices-v1.0.bin /usr/bin/espeak-ng
node render.js 1080 1920 MING_Store_Extrait_TikTok_1080x1920.mp4 30 --page extrait.html --audio extrait.wav
node render.js 1920 1080 MING_Store_Extrait_YouTube_1920x1080.mp4 30 --page extrait.html --audio extrait.wav
```

## Montage « parole » (16 s, vertical)

[`video/MING_Store_Montage_Parole_1080x1920.mp4`](video/MING_Store_Montage_Parole_1080x1920.mp4) : montage de la vidéo face caméra
(`video/sources/parole.mp4`) avec zooms et coupes sur le rythme de la parole, visite des photos (Nike, Starbucks, Dior,
Coca-Cola), sous-titres mot par mot, effets sur les mots clés, bruitages et écran de fin MING Store.

- `video/montage_timings.js` : minutage de chaque mot, des photos et des bruitages.
- `video/montage.html` : le montage (caméra, sous-titres, effets).
- `video/montage_audio.py` : voix d'origine + bruitages → `montage.wav`.

```bash
cd video
mkdir -p /tmp/images && ffmpeg -i sources/parole.mp4 -q:v 3 /tmp/images/%04d.jpg
python3 montage_audio.py
node render.js 1080 1920 montage_brut.mp4 30 --page montage.html --audio montage.wav --frames-dir /tmp/images
ffmpeg -i montage_brut.mp4 -c:v copy -af loudnorm=I=-14:TP=-1.5 -c:a aac -b:a 192k MING_Store_Montage_Parole_1080x1920.mp4
```

## Modifier et refaire la vidéo

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
