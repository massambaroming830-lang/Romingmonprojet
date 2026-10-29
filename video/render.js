// Rend animation.html en MP4.
// Usage : node render.js <largeur> <hauteur> <sortie.mp4> [fps] [--frames t1,t2,...] [--page extrait.html --audio extrait.wav]
const { chromium } = require('playwright');
const { spawn } = require('child_process');
const path = require('path');

(async () => {
  const [w, h, out, fpsArg] = process.argv.slice(2);
  const W = +w, H = +h, FPS = +(fpsArg || 30);
  const stillsIdx = process.argv.indexOf('--frames');
  const stills = stillsIdx > 0 ? process.argv[stillsIdx + 1].split(',').map(Number) : null;
  const opt = (name, def) => { const i = process.argv.indexOf(name); return i > 0 ? process.argv[i + 1] : def; };
  const PAGE = opt('--page', 'animation.html'), AUDIO = opt('--audio', 'music.wav');

  const browser = await chromium.launch();
  const page = await browser.newPage({ viewport: { width: W, height: H } });
  const url = 'file://' + path.resolve(__dirname, PAGE) + `?w=${W}&h=${H}&render=1`;
  await page.goto(url);
  await page.evaluate(() => window.ready);
  const duration = await page.evaluate(() => window.DURATION);

  const grab = async t => {
    const b64 = await page.evaluate(t => { window.render(t); return document.getElementById('c').toDataURL('image/png').split(',')[1]; }, t);
    return Buffer.from(b64, 'base64');
  };

  if (stills) {
    const fs = require('fs');
    for (const t of stills) fs.writeFileSync(`${out}_${t}.png`, await grab(t));
    await browser.close();
    return;
  }

  const ff = spawn('ffmpeg', ['-y', '-f', 'image2pipe', '-framerate', String(FPS), '-i', '-',
    '-i', path.resolve(__dirname, AUDIO), '-shortest',
    '-c:v', 'libx264', '-preset', 'veryfast', '-crf', '18', '-pix_fmt', 'yuv420p',
    '-c:a', 'aac', '-movflags', '+faststart', out], { stdio: ['pipe', 'inherit', 'inherit'] });

  const total = Math.round(duration * FPS);
  for (let i = 0; i < total; i++) {
    const buf = await grab(i / FPS);
    if (!ff.stdin.write(buf)) await new Promise(r => ff.stdin.once('drain', r));
  }
  ff.stdin.end();
  await new Promise(r => ff.on('close', r));
  await browser.close();
})();
