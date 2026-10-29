// Montage « parole » : minutage de chaque mot dit dans sources/parole.mp4 (secondes).
// Transcription Whisper + horodatage par un modèle de reconnaissance vocale, vérifié à la main.
// Chaque groupe = un sous-titre à l'écran ; "hl" = mots mis en couleur.
// Le contenu entre les accolades est du JSON (lu aussi par montage_audio.py).
window.MONTAGE = {
 "clip": 14.02,
 "outro": 2.2,
 "groups": [
  {"hl": [],            "words": [["NE", 0.30], ["CHERCHE", 0.62], ["PAS", 0.98]]},
  {"hl": ["PARFAIT"],   "words": [["À", 1.12], ["ÊTRE", 1.20], ["PARFAIT", 1.42]]},
  {"hl": [],            "words": [["NE", 1.88], ["CHERCHE", 1.96], ["PAS", 2.22]]},
  {"hl": ["ENTREPRISE"],"words": [["À", 2.40], ["RENDRE", 2.46], ["TON", 2.66], ["ENTREPRISE", 2.80]]},
  {"hl": ["PARFAITE"],  "words": [["PARFAITE", 3.04]]},
  {"hl": ["CRÉER"],     "words": [["AVANT", 3.42], ["DE", 3.62], ["LA", 3.70], ["CRÉER", 3.78]]},
  {"hl": ["ENTREPRISES"], "words": [["LA", 4.50], ["PLUPART", 4.66], ["DES", 4.98], ["ENTREPRISES", 5.14]]},
  {"hl": ["ADMIRES"],   "words": [["QUE", 5.62], ["TU", 5.70], ["ADMIRES", 5.82], ["AUJOURD'HUI", 6.38]]},
  {"hl": ["ATTENDU"],   "words": [["N'ONT", 6.74], ["PAS", 6.88], ["ATTENDU", 7.10]]},
  {"hl": ["PARFAITES"], "words": [["QU'ELLES", 7.42], ["SOIENT", 7.74], ["PARFAITES", 7.90]]},
  {"hl": ["SORTIR"],    "words": [["AVANT", 8.50], ["DE", 8.60], ["LES", 8.68], ["FAIRE", 8.76], ["SORTIR", 8.98]]},
  {"hl": ["LENDEMAIN"], "words": [["DU", 9.62], ["JOUR", 9.80], ["AU", 10.08], ["LENDEMAIN", 10.30]]},
  {"hl": [],            "words": [["TU", 11.80], ["SAIS,", 12.00]]},
  {"hl": ["ERREURS"],   "words": [["ON", 12.40], ["APPREND", 12.50], ["DE", 12.78], ["NOS", 12.88], ["ERREURS", 13.00]]},
  {"hl": ["PLUS"],      "words": [["ON", 13.40], ["DEVIENT", 13.50], ["PLUS…", 13.86]]}
 ],
 "photos": [
  {"name": "NIKE",      "t": 4.50, "box": [65, 50, 445, 268]},
  {"name": "STARBUCKS", "t": 5.14, "box": [580, 25, 1032, 390]},
  {"name": "DIOR",      "t": 5.82, "box": [108, 310, 452, 620]},
  {"name": "COCA-COLA", "t": 6.38, "box": [575, 405, 988, 658]}
 ],
 "hits": [1.42, 3.04, 7.90, 13.00, 14.30]
};
