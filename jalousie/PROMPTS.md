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
