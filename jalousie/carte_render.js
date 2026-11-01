// Exporte carte.html en 3 clips (scènes 2, 3 et 4) dans clips/anim{2,3,4}_<L>x<H>.mp4
// Usage : node carte_render.js 1080 1920   |   node carte_render.js 1920 1080
// Aperçu d'images : node carte_render.js 1080 1920 --frames 1,4,7
const { chromium } = require('playwright');
const { spawn } = require('child_process');
const path = require('path');
const fs = require('fs');

const W = +process.argv[2] || 1080, H = +process.argv[3] || 1920, FPS = 30;
const SCENES = [[2, 0, 3.0], [3, 3.0, 6.0], [4, 6.0, 8.4]];

(async () => {
  const browser = await chromium.launch();
  const page = await browser.newPage({ viewport: { width: W, height: H } });
  await page.goto('file://' + path.resolve(__dirname, 'carte.html') + `?w=${W}&h=${H}&render=1`);
  await page.evaluate(() => window.ready);
  const grab = async t => Buffer.from(await page.evaluate(t => {
    window.render(t); return document.getElementById('c').toDataURL('image/png').split(',')[1];
  }, t), 'base64');

  const fi = process.argv.indexOf('--frames');
  if (fi > 0) {
    for (const t of process.argv[fi + 1].split(',').map(Number)) fs.writeFileSync(`/tmp/carte_${t}.png`, await grab(t));
    return browser.close();
  }

  fs.mkdirSync(path.resolve(__dirname, 'clips'), { recursive: true });
  for (const [n, a, b] of SCENES) {
    const out = path.resolve(__dirname, 'clips', `anim${n}_${W}x${H}.mp4`);
    const ff = spawn('ffmpeg', ['-v', 'error', '-y', '-f', 'image2pipe', '-framerate', String(FPS), '-i', '-',
      '-c:v', 'libx264', '-preset', 'veryfast', '-crf', '18', '-pix_fmt', 'yuv420p', out], { stdio: ['pipe', 'inherit', 'inherit'] });
    for (let i = 0; i < Math.round((b - a) * FPS); i++) {
      const buf = await grab(a + i / FPS);
      if (!ff.stdin.write(buf)) await new Promise(r => ff.stdin.once('drain', r));
    }
    ff.stdin.end();
    await new Promise(r => ff.on('close', r));
    console.log('OK ->', out);
  }
  await browser.close();
})();
