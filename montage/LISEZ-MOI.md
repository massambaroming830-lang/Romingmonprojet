# Outil de montage

Assemble tes vidéos et photos (rushs au téléphone, vidéos des modèles, anciennes pubs…)
en une seule vidéo prête pour TikTok, YouTube ou Instagram. Tout se décrit dans un fichier JSON.

```bash
cd montage
node montage.js exemple.json                    # → sortie/exemple_tiktok.mp4
node montage.js exemple.json --format youtube   # même montage en horizontal
```

Il faut ffmpeg et ffprobe.

## Ce que fait l'outil

- **Découpe** des vidéos (`debut`, `fin`) et **vitesse** (`vitesse`: 0.5 = ralenti, 2 = accéléré)
- **Photos animées** (effet Ken Burns) : `duree` + `mouvement`
- **Mise au format automatique** : une vidéo horizontale dans un format vertical
  (et inversement) avec `remplissage` = `flou` (fond flouté, par défaut), `recadrer` ou `noir`
- **Transitions** entre clips
- **Textes** superposés avec apparition/disparition en fondu
- **Musique** en boucle avec fondus, et **baisse automatique** quand une voix parle
- **Voix off** séparée

## Structure du fichier

```json
{
  "format": "tiktok",                  // tiktok | youtube | carre | post | 1280x720
  "fps": 30,
  "remplissage": "flou",
  "transition": { "type": "fondu", "duree": 0.5 },   // transition par défaut
  "sonDesClips": true,                 // false = couper le son de toutes les vidéos
  "sortie": "sortie/ma-video_{format}.mp4",
  "clips": [
    { "fichier": "rushs/clip1.mp4", "debut": 2, "fin": 6, "son": true, "volume": 1 },
    { "fichier": "photos/produit.jpg", "duree": 3, "mouvement": "zoom-avant",
      "transition": { "type": "glisse-gauche", "duree": 0.4 } },
    { "fichier": "../modeles/sortie/promo-produit_tiktok.mp4", "transition": "cercle" }
  ],
  "textes": [
    { "texte": "Nouvel arrivage", "debut": 0.5, "fin": 3, "position": "haut",
      "taille": 64, "couleur": "white", "couleurFond": "black@0.55" }
  ],
  "voix": { "fichier": "voix.wav", "debut": 0, "volume": 1 },
  "musique": { "fichier": "musique.mp3", "volume": 0.5, "debut": 0,
               "fonduEntree": 0.5, "fonduSortie": 2, "baisserSousVoix": true }
}
```

(Les commentaires `//` ci-dessus sont des explications : ne les mets pas dans ton vrai fichier JSON.)

- **position** du texte : `haut`, `centre`, `bas`. `"fond": false` pour enlever le bandeau.
  Couleurs : nom (`white`, `yellow`) ou code `0xA3192F` ; `@0.8` = transparence.
  Pour aller à la ligne dans un texte : `\n`.
- **mouvement** (photos) : `zoom-avant`, `zoom-arriere`, `gauche`, `droite`.
- **Transitions** : `fondu`, `noir`, `blanc`, `dissoudre`, `glisse-gauche`, `glisse-droite`,
  `glisse-haut`, `glisse-bas`, `volet-gauche`, `volet-droite`, `volet-haut`, `volet-bas`,
  `cercle`, `cercle-ferme`, `zoom`, `pixel`, `flou`, `rideau`, `diagonale`, `radial`,
  `coupe` (coupe franche, sans transition).

## Exemple fourni

`exemple.json` remonte la vidéo MING Store existante en une version courte de 17 s :
logo → photo animée → routes (vidéo horizontale, fond flouté) → contacts, avec deux textes
et une musique afro (`exemple/musique-afro.m4a`, générée par `modeles/musique.py`).
Résultat : [`exemple/resultat_tiktok.mp4`](exemple/resultat_tiktok.mp4).

## Astuce : modèles + montage

1. Crée tes animations (intro, promo, contacts) avec `modeles/rendu.js`.
2. Monte-les avec tes vraies vidéos de produits grâce à `montage.js`.
