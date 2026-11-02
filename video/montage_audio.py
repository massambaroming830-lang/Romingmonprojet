"""Bande-son du montage « parole » : uniquement la voix d'origine, nettoyée et mise en avant
(coupe des graves parasites, voix plus présente, compression douce, volume TikTok), puis silence
sur l'écran de fin.
Usage : python3 montage_audio.py   (lit sources/parole.mp4 et montage_timings.js, écrit montage.wav)"""
import json, subprocess

src = open('montage_timings.js').read()
M = json.loads(src[src.index('{'): src.rindex('}') + 1])
DUR = M['clip'] + M['outro']

voice = ','.join([
    f"atrim=0:{M['clip']}",
    'highpass=f=80',                                   # grondements, bruit de manipulation
    'equalizer=f=3000:t=q:w=1.2:g=4',                  # intelligibilité de la parole
    'acompressor=threshold=-22dB:ratio=3:attack=10:release=150:makeup=4',
    f"afade=t=out:st={M['clip'] - 0.08}:d=0.08",       # évite un clic à la coupe
    'loudnorm=I=-14:TP=-1.5:LRA=11',
    'aresample=44100',
    f'apad=whole_dur={DUR}',
])
subprocess.run(['ffmpeg', '-v', 'error', '-y', '-i', 'sources/parole.mp4', '-vn', '-ac', '2', '-af', voice, 'montage.wav'], check=True)
print('montage.wav', round(DUR, 2), 's')
