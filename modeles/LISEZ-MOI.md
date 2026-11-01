# Modèles de vidéos motion design

Chaque vidéo est décrite dans un **fichier JSON** (dans `projets/`) : une liste de scènes
avec leurs textes, couleurs et durées. Pas besoin de coder : tu copies un modèle,
tu changes les textes, et tu lances le rendu.

## Démarrage rapide

```bash
cd modeles
cp projets/promo-produit.json projets/ma-video.json   # 1. copie un modèle
# 2. modifie projets/ma-video.json (textes, prix, couleurs…)
node rendu.js projets/ma-video.json --apercu          # 3. images de contrôle (rapide)
node rendu.js projets/ma-video.json --format tous     # 4. vidéos MP4 dans sortie/
```

Aperçu en direct : ouvre `moteur.html` dans Chrome, clique sur **Ouvrir un projet** et
sélectionne ton JSON (et ses images en même temps).

**Options de `rendu.js`** : `--format tiktok|youtube|carre|post|tous` (plusieurs : `tiktok,youtube`),
`--fps 30`, `--apercu` (ou `--apercu 2,5.5` pour des instants précis), `--muet`, `--sortie dossier/`.

Il faut : Node.js, Playwright (Chromium), ffmpeg, et Python 3 + numpy pour la musique automatique.

## Modèles fournis

| Fichier | Contenu | Style |
|---|---|---|
| `promo-produit.json` | Titre choc → badge -30 % et prix → avantages → bouton WhatsApp | rouge, particules, volet |
| `nouvel-arrivage.json` | Titre → 3 photos produits (Ken Burns) → contacts | grille, glisse, musique afro |
| `presentation-entreprise.json` | Logo → services → chiffres → avis client → contacts | formes, volet/cercle |
| `collection-luxe.json` | Collection → photos encadrées → promo → réservation | doré, dégradé, fondu, ambiance luxe |

Les vidéos obtenues (format TikTok) sont dans [`exemples/`](exemples/).

## Structure d'un projet

```json
{
  "marque": "MING Store",
  "theme": { "fond": "#07070a", "principal": "#A3192F", "accent": "#E0344F",
             "texte": "#ffffff", "doux": "#bdbdc4", "decor": "particules" },
  "transition": "volet",
  "audio": { "musique": "auto", "ambiance": "energique" },
  "scenes": [ { "type": "titre", "duree": 3, "lignes": ["GRANDE", "PROMO"] } ]
}
```

- **decor** (fond animé) : `particules`, `grille`, `formes`, `degrade`, `uni`
- **transition** (globale ou par scène, vers la scène suivante) :
  `volet`, `rideau`, `cercle`, `fondu`, `flash`, `zoom`, `glisse`, `aucune`
- **audio.musique** : `"auto"` (musique originale générée et calée sur les transitions),
  un fichier (`"musique/ma-musique.mp3"`) ou `false`.
  **audio.ambiance** : `energique`, `douce`, `luxe`, `afro`. **audio.bpm** : tempo (optionnel).
  **audio.voix** : fichier de voix off (la musique baisse automatiquement quand la voix parle) ;
  **audio.volumeMusique** : 0 à 1.
- **fonduFinal** : `false` pour supprimer le fondu au noir de la fin.

## Types de scènes

| type | Réglages |
|---|---|
| `logo` | `texte` (sinon `marque`), `sousTitre`, `image` (fichier logo) |
| `titre` | `lignes` (liste), `surtitre`, `sousTitre`, `accent` (n° de ligne en couleur, défaut : la dernière), `taille` |
| `liste` | `titre`, `elements` : textes, ou objets `{ "texte", "detail", "icone" }` |
| `promo` | `remise`, `etiquette`, `produit`, `ancienPrix`, `prix`, `mention` |
| `image` | `fichier`, `legende`, `detail`, `mouvement` (`zoom-avant`, `zoom-arriere`, `gauche`, `droite`), `cadre` (true/false) |
| `chiffres` | `titre`, `elements` : `{ "valeur", "prefixe", "suffixe", "decimales", "label" }` |
| `avis` | `texte`, `auteur`, `etoiles` |
| `contact` | `titre`, `elements` : `{ "icone", "titre", "valeurs": [...] }`, `pied`, `marque` (false pour cacher le logo) |
| `appel` | `lignes`, `bouton`, `icone`, `detail` |

Chaque scène a aussi `duree` (secondes) et `transition`.

**Icônes** : `whatsapp`, `instagram`, `tiktok`, `facebook`, `telephone`, `email`, `lieu`, `web`,
`coche`, `etoile`, `camion` — ou n'importe quel texte court (ex. `"1"`, `"A"`).

Les textes s'adaptent tout seuls à chaque format (taille réduite ou retour à la ligne s'ils sont trop longs).

## Ajouter un nouveau type de scène

Dans `moteur.js`, ajoute une fonction `SCENES.monType = (l, d, s) => { … }` :
`l` = temps écoulé dans la scène, `d` = sa durée, `s` = ses réglages JSON.
Les outils `text()`, `paragraph()`, `fit()`, `carte()`, `icone()`, `prog()` et `eOut()` sont disponibles.
