# « À bas la jalousie » : vidéo d'annonce Kinshasa → Angola → Bruxelles

Le principe : un aigle part de Kinshasa, survole l'Angola, arrive à Bruxelles et se pose
devant La Madeleine, où se joue le spectacle. Ensuite l'affiche apparaît.
C'est un seul vol continu, filmé comme un drone qui suit l'aigle, dans une lumière dorée de coucher de soleil.

## 1. Générer les clips (Kling, Runway, Veo, Sora, Higgsfield…)

Réglages conseillés : **9:16** (Reel/TikTok), **5 s par clip**, mode « image-to-video »
quand c'est possible. Pour qu'un clip s'enchaîne avec le suivant, prends la **dernière image** du clip
comme **première image** du clip suivant.

Enregistre les fichiers sous ces noms dans `jalousie/clips/`.

### `clip1.mp4`: Kinshasa, départ
> Cinematic FPV drone shot at golden hour, flying fast and low over the Congo River in Kinshasa,
> the modern Kinshasa skyline and boulevard du 30 Juin on the bank, warm orange sunset sky,
> a majestic African fish eagle flies into frame from behind the camera and glides just above the water,
> camera follows the eagle closely, motion blur, lens flare, epic travel commercial, photorealistic, 4K.

### `clip2.mp4`: Angola
> Cinematic FPV drone shot following an African fish eagle flying fast over the Angolan coastline,
> turquoise Atlantic ocean, red cliffs of Miradouro da Lua, the eagle's wingtips skim the waves
> and splash water, golden hour sunlight, motion blur, smooth tracking shot, photorealistic, 4K.

### `clip3.mp4`: Bruxelles, arrivée
> Cinematic FPV drone shot following an eagle flying over Brussels at dusk, passing the Atomium
> then diving towards the historic city centre rooftops, warm city lights turning on,
> pink and orange sky, motion blur, fast smooth tracking shot, epic travel commercial, photorealistic, 4K.

### `clip4.mp4`: La Madeleine
> Cinematic FPV drone shot, an eagle glides down the Rue de la Madeleine in Brussels at night
> and lands on the facade sign of the theatre "La Madeleine", warm stage lights, crowd queuing at the entrance,
> camera slows down and pushes in on the entrance, photorealistic, 4K.

> **Option :** pour le clip 4, utilise **l'affiche** comme image de fin (end frame) si l'outil le permet.
> L'aigle « entre » alors dans l'affiche.

## 2. Assembler (fait automatiquement)

```bash
cd jalousie
python3 musique.py musique.wav          # bande-son originale (15 s)
python3 elevenlabs.py                    # voix off + bruitages ElevenLabs (clé ELEVENLABS_API_KEY)
python3 montage.py                       # -> Jeremie_A_bas_la_jalousie_1080x1920.mp4
python3 montage.py --horizontal          # -> version 1920x1080
```

Le montage ajoute :
- les titres qui s'écrivent lettre par lettre, comme dans la vidéo de référence :
  **KINSHASA / RDC / DÉPART**, **ANGOLA / ESCALE**, **BRUXELLES / ARRIVÉE**
- les transitions entre les clips
- la fin avec l'affiche, un léger zoom et **20.12.2026 · LA MADELEINE · BRUXELLES / RÉSERVEZ VOS PLACES**
- la musique, et si elles existent la **voix off** (`voix_off.wav`) et les **bruitages** (`bruitages.wav`)
  générés par `elevenlabs.py` ; la musique baisse automatiquement quand la voix parle

### Voix off (ElevenLabs, voix « George », modèle multilingue)
| Temps | Scène | Texte |
|---|---|---|
| 0,35 s | Kinshasa | De Kinshasa… |
| 3,0 s | Angola | en passant par l'Angola… |
| 5,6 s | Bruxelles | il arrive enfin à Bruxelles ! |
| 8,15 s | La Madeleine | Jérémie et son groupe présentent… |
| 10,25 s | Affiche | À bas la jalousie ! Le 20 décembre, à La Madeleine. Réservez vos places ! |

Bruitages : vent et battements d'ailes, cri d'aigle, whooshes aux transitions, vagues (Angola),
ambiance de ville et cloches (Bruxelles), foule devant le théâtre, impact sur l'affiche, rires et applaudissements.
Pour changer de voix : `ELEVENLABS_VOICE_ID=<id> python3 elevenlabs.py` (supprimer `audio_el/` pour tout régénérer).

Si un clip manque, le script met à sa place un fond provisoire. Tu peux donc voir le rythme de la vidéo tout de suite.

## 3. Motion TikTok (26 s, 1080x1920) : `Jeremie_A_bas_la_jalousie_motion_TikTok.mp4`

Fait uniquement à partir des vraies photos : Jérémie (tiré de l'affiche) est la star, et Christelle Business Service Dubaï
a sa séquence de soutien « Christelle Business Service Dubaï soutient l'équipe JS Production » (12,5 à 17,5 s).
Effets de caméra : Ken Burns, flashs et secousses aux coupes, flou de mouvement, grain pellicule, light leak chaud,
particules lumineuses, vignettage.

| Temps | Scène | Voix off (Kokoro, voix française ff_siwis) |
|---|---|---|
| 0 à 4,5 s | Jérémie en gros plan | Il est de retour… Jérémie et son groupe ! Préparez-vous à rire comme jamais. |
| 4,5 à 8,5 s | Titre | Le spectacle événement : À bas la jalousie ! |
| 8,5 à 12,5 s | Date et lieu | Rendez-vous le vingt décembre, au théâtre La Madeleine, à Bruxelles. |
| 12,5 à 17,5 s | Christelle Business Service Dubaï (2 photos) | Avec le soutien de Christelle Business Service Dubaï, et de l'équipe JS Production. |
| 17,5 à 26 s | Affiche + CTA | Les places partent très vite… Réservez dès maintenant ! À bas la jalousie ! On vous attend ! |

```bash
cd jalousie
python3 musique.py musique_tiktok.wav 26 17.5 4.5 8.5 12.5 17.5
python3 voix_kokoro.py kokoro-v1.0.onnx voices-v1.0.bin      # modèle : github.com/thewh1teagle/kokoro-onnx (model-files-v1.0)
python3 motion_tiktok.py
```
Musique de fond : `fond_musique.m4a` (26 premières secondes du titre fourni). Elle remplace `musique_tiktok.wav`
et baisse automatiquement sous la voix. Pour changer de musique, remplace ce fichier puis lance `python3 motion_tiktok.py --remix`.

La phonétique de la voix est écrite à la main dans `voix_kokoro.py` (pas besoin d'espeak-ng).
Pour changer un texte, modifie le texte **et** sa phonétique.

## 4. Motion « Kinshasa » (26 s, TikTok) : `Jeremie_A_bas_la_jalousie_Kinshasa_TikTok.mp4`

Dimanche 6 décembre 2026, à partir de 16h00, Centre culturel de Kinshasa / Grand Tambour (affiche `affiche_kinshasa.jpg`).
Style « interface » épuré : mots qui passent du flou au net, billet animé avec trajectoire en pointillés,
écran orange avec texte lettre par lettre, cartes-infos qui s'empilent, tarifs 10$ / 20$ / 50$ / 100$,
cartes photo avec gros titre tapé, collage final avec l'affiche, « Réservez votre place » et l'infoline.

```bash
cd jalousie
python3 voix_kokoro.py kokoro-v1.0.onnx voices-v1.0.bin kinshasa   # -> voix_kinshasa.wav
python3 motion_kinshasa.py                                          # musique : fond_musique.m4a
```
