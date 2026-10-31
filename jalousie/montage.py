"""Assemble la vidéo d'annonce « À bas la jalousie » (Kinshasa -> Angola -> Bruxelles).

Usage : python3 montage.py [--horizontal]
Clips attendus dans clips/clip1.mp4 ... clip4.mp4 (un fond provisoire est utilisé s'ils manquent).
"""
import os, subprocess, sys, tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
HORIZ = "--horizontal" in sys.argv
W, H = (1920, 1080) if HORIZ else (1080, 1920)
FPS = 30
FONT = "/usr/share/fonts/opentype/inter/InterDisplay-Black.otf"
FONT2 = "/usr/share/fonts/opentype/inter/InterDisplay-Bold.otf"
XF = 0.4  # durée des transitions
OUT = os.path.join(HERE, f"Jeremie_A_bas_la_jalousie_{W}x{H}.mp4")

# (clip, durée, lignes de texte, couleurs du fond provisoire)
SCENES = [
    ("clip1.mp4", 3.2, ["KINSHASA", "RDC", "DÉPART"], ("0xF7A541", "0x2A6F8F")),
    ("clip2.mp4", 3.0, ["ANGOLA", "ESCALE"], ("0x3FC1C9", "0xC2552B")),
    ("clip3.mp4", 3.0, ["BRUXELLES", "ARRIVÉE"], ("0xF28C8C", "0x2B2D5C")),
    ("clip4.mp4", 2.4, [], ("0x1B1B2F", "0xE0A34A")),
]
POSTER_DUR = 4.4


def run(cmd):
    subprocess.run(cmd, check=True)


def typewriter(lines, start=0.25, per_char=0.06):
    """drawtext qui écrit chaque ligne lettre par lettre (gros titre puis sous-titres)."""
    f, t = [], start
    big, small = int(W * 0.13 if not HORIZ else W * 0.075), int(W * 0.05 if not HORIZ else W * 0.03)
    y = H * 0.30
    for i, line in enumerate(lines):
        size = big if i == 0 else small
        font = FONT if i == 0 else FONT2
        for k in range(1, len(line) + 1):
            end = t + per_char if k < len(line) else 999
            f.append(
                f"drawtext=fontfile={font}:text='{line[:k]}':fontsize={size}:fontcolor=white"
                f":x=(w-tw)/2:y={y:.0f}:shadowcolor=black@0.55:shadowx=3:shadowy=3"
                f":enable='between(t,{t:.3f},{end:.3f})'"
            )
            t += per_char
        y += size * 1.05
    return f


def scene_file(tmp, i, clip, dur, lines, colors):
    path = os.path.join(HERE, "clips", clip)
    out = os.path.join(tmp, f"s{i}.mp4")
    if os.path.exists(path):
        src = ["-i", path]
        base = (f"[0:v]scale={W}:{H}:force_original_aspect_ratio=increase,crop={W}:{H},"
                f"fps={FPS},trim=0:{dur},setpts=PTS-STARTPTS")
    else:  # fond provisoire en dégradé + mention du clip à générer
        src = ["-f", "lavfi", "-i",
               f"gradients=s={W}x{H}:c0={colors[0]}:c1={colors[1]}:x0=0:y0=0:x1={W}:y1={H}:d={dur}:r={FPS}:speed=0.02"]
        base = (f"[0:v]drawtext=fontfile={FONT2}:text='{clip} à générer':fontsize={int(W*0.035)}"
                f":fontcolor=white@0.6:x=(w-tw)/2:y=h*0.85")
    vf = ",".join([base, "vignette=PI/5"] + typewriter(lines) + ["format=yuv420p"]) + "[v]"
    run(["ffmpeg", "-v", "error", "-y", *src, "-filter_complex", vf, "-map", "[v]",
         "-t", str(dur), "-c:v", "libx264", "-crf", "18", "-preset", "fast", out])
    return out


def poster_file(tmp):
    out = os.path.join(tmp, "poster.mp4")
    img = os.path.join(HERE, "affiche.jpg")
    n = int(POSTER_DUR * FPS)
    pw = int(W * (0.98 if not HORIZ else 0.70))
    small = int(W * (0.042 if not HORIZ else 0.026))
    cta_y = int(H * (0.70 if not HORIZ else 0.86))
    date_y = int(H * (0.24 if not HORIZ else 0.05))
    fc = (
        # fond : l'affiche agrandie et floutée
        f"[0:v]scale={W}:{H}:force_original_aspect_ratio=increase,crop={W}:{H},gblur=sigma=30,"
        f"eq=brightness=-0.12,loop={n}:1:0,fps={FPS},trim=0:{POSTER_DUR}[bg];"
        # premier plan : l'affiche nette avec un zoom lent
        f"[0:v]scale={pw*2}:-2,loop={n}:1:0,fps={FPS},trim=0:{POSTER_DUR},"
        f"zoompan=z='1+0.0009*on':x='iw/2-iw/zoom/2':y='ih/2-ih/zoom/2':d=1:s={pw}x{int(pw*359/828)//2*2}:fps={FPS}[fg];"
        f"[bg][fg]overlay=(W-w)/2:(H-h)/2,"
        f"drawtext=fontfile={FONT}:text='20.12.2026':fontsize={int(small*1.8)}:fontcolor=white"
        f":x=(w-tw)/2:y={date_y}:alpha='min(1,max(0,(t-0.4)/0.4))',"
        f"drawtext=fontfile={FONT2}:text='LA MADELEINE · BRUXELLES':fontsize={small}:fontcolor=white"
        f":x=(w-tw)/2:y={date_y}+{int(small*2.2)}:alpha='min(1,max(0,(t-0.7)/0.4))',"
        f"drawbox=x={(W-int(W*0.62))//2}:y={cta_y-int(small*0.5)}:w={int(W*0.62)}:h={int(small*2)}"
        f":color=0xE4202A@1:t=fill:enable='gte(t,1.2)',"
        f"drawtext=fontfile={FONT}:text='RÉSERVEZ VOS PLACES':fontsize={small}:fontcolor=white"
        f":x=(w-tw)/2:y={cta_y}:enable='gte(t,1.2)',"
        f"fade=t=out:st={POSTER_DUR-0.5}:d=0.5,format=yuv420p[v]"
    )
    run(["ffmpeg", "-v", "error", "-y", "-i", img, "-filter_complex", fc, "-map", "[v]",
         "-t", str(POSTER_DUR), "-c:v", "libx264", "-crf", "18", "-preset", "fast", out])
    return out


def main():
    with tempfile.TemporaryDirectory() as tmp:
        files = [scene_file(tmp, i, *s) for i, s in enumerate(SCENES)] + [poster_file(tmp)]
        durs = [s[1] for s in SCENES] + [POSTER_DUR]
        trans = ["fadewhite", "zoomin", "fadewhite", "fade"]
        inputs, fc, prev, off = [], [], "[0:v]", 0.0
        for f in files:
            inputs += ["-i", f]
        for i in range(1, len(files)):
            off += durs[i - 1] - XF
            label = f"[x{i}]"
            fc.append(f"{prev}[{i}:v]xfade=transition={trans[i-1]}:duration={XF}:offset={off:.3f}{label}")
            prev = label
        total = sum(durs) - XF * (len(files) - 1)
        music = os.path.join(HERE, "musique.wav")
        audio = ["-i", music] if os.path.exists(music) else ["-f", "lavfi", "-i", "anullsrc=r=44100:cl=stereo"]
        na = len(files)
        # voix off et bruitages ElevenLabs (voir elevenlabs.py), ajoutés s'ils existent
        voix, sfx = os.path.join(HERE, "voix_off.wav"), os.path.join(HERE, "bruitages.wav")
        mus = f"[{na}:a]aformat=sample_rates=44100:channel_layouts=stereo,atrim=0:{total:.3f}"
        layers = []
        if os.path.exists(sfx):
            audio += ["-i", sfx]
            na_s = na + 1
            mus += ",volume=0.7"
            layers.append(f"[{na_s}:a]aformat=sample_rates=44100:channel_layouts=stereo,volume=0.9[sfx]")
        if os.path.exists(voix):
            audio += ["-i", voix]
            na_v = na + 1 + (1 if os.path.exists(sfx) else 0)
            layers.append(f"[{na_v}:a]aformat=sample_rates=44100:channel_layouts=stereo,asplit=2[vo][vkey]")
        if layers:
            fc += layers
            fc.append(f"{mus}[mus0]")
            if os.path.exists(voix):  # la musique (et les bruitages) baissent quand la voix parle
                bed = "[mus0][sfx]amix=inputs=2:normalize=0[bed0]" if os.path.exists(sfx) else "[mus0]anull[bed0]"
                fc.append(bed)
                fc.append("[bed0][vkey]sidechaincompress=threshold=0.03:ratio=6:attack=20:release=350[bed]")
                fc.append("[bed][vo]amix=inputs=2:normalize=0,alimiter=limit=0.95[mixa]")
            else:
                fc.append("[mus0][sfx]amix=inputs=2:normalize=0,alimiter=limit=0.95[mixa]")
            fc.append(f"[mixa]atrim=0:{total:.3f},afade=t=out:st={total-0.8:.3f}:d=0.8[a]")
        else:
            fc.append(f"{mus},afade=t=out:st={total-0.8:.3f}:d=0.8[a]")
        run(["ffmpeg", "-v", "error", "-y", *inputs, *audio, "-filter_complex", ";".join(fc),
             "-map", prev, "-map", "[a]", "-t", f"{total:.3f}", "-c:v", "libx264", "-crf", "19",
             "-preset", "medium", "-pix_fmt", "yuv420p", "-c:a", "aac", "-b:a", "192k",
             "-movflags", "+faststart", OUT])
    print(f"OK -> {OUT} ({total:.1f} s)")


if __name__ == "__main__":
    main()
