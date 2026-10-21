// Builds the static site for Vercel (or any static host) into frontend/dist/.
//
//   API_BASE_URL=https://your-api.up.railway.app npm run build:web
//
// dist/
//   index.html, main.js          standalone entry point (web/)
//   app.js                       the page component, copied unchanged from src/ (shared with Streamlit)
//   app.css                      Tailwind build of the Stitch theme
//   config.js                    window.RR_CONFIG = { apiBase }
//   app/static/img/*.jpg         photos from ../static/img (same URLs the API returns, so nothing is rewritten)

import { execFileSync } from 'node:child_process';
import { cpSync, existsSync, mkdirSync, readdirSync, rmSync, writeFileSync } from 'node:fs';
import { dirname, join, resolve } from 'node:path';
import { fileURLToPath } from 'node:url';

const frontend = resolve(dirname(fileURLToPath(import.meta.url)), '..');
const dist = join(frontend, 'dist');
const images = resolve(frontend, '..', 'static', 'img');

function fail(message) {
  console.error(`\nbuild:web failed: ${message}\n`);
  process.exit(1);
}

// --- API address ---------------------------------------------------------------------------------------
const onVercel = Boolean(process.env.VERCEL);
let apiBase = (process.env.API_BASE_URL || '').trim().replace(/\/+$/, '');
if (!apiBase) {
  if (onVercel) fail('API_BASE_URL is not set. Add it in the Vercel project settings (your Railway URL).');
  apiBase = 'http://localhost:8000';
  console.log(`API_BASE_URL not set; using ${apiBase} (local development).`);
}
try {
  const url = new URL(apiBase);
  if (!/^https?:$/.test(url.protocol)) throw new Error('not http(s)');
  if (onVercel && url.protocol !== 'https:') fail(`API_BASE_URL must be https:// in production (got ${apiBase}).`);
} catch (err) {
  if (err.message?.startsWith?.('not http')) fail(`API_BASE_URL must start with http:// or https:// (got ${apiBase}).`);
  fail(`API_BASE_URL is not a valid URL: ${apiBase}`);
}

// --- Assets --------------------------------------------------------------------------------------------
if (!existsSync(images) || readdirSync(images).filter((f) => f.endsWith('.jpg')).length === 0) {
  fail(`photos not found in ${images}. The build copies them from the repo's static/img folder, so the Vercel `
    + 'project must be allowed to read files outside its Root Directory '
    + '(Project Settings > General > "Include source files outside of the Root Directory in the Build Step").');
}

rmSync(dist, { recursive: true, force: true });
mkdirSync(join(dist, 'app', 'static', 'img'), { recursive: true });

// Tailwind (run through node so it works the same on Windows, macOS and Vercel's Linux builders).
const tailwindCli = join(frontend, 'node_modules', 'tailwindcss', 'lib', 'cli.js');
if (!existsSync(tailwindCli)) fail('tailwindcss is not installed. Run `npm install` in frontend/ first.');
execFileSync(process.execPath, [tailwindCli, '-c', join(frontend, 'tailwind.config.js'),
  '-i', join(frontend, 'src', 'input.css'), '-o', join(dist, 'app.css'), '--minify'], { cwd: frontend, stdio: 'inherit' });

cpSync(join(frontend, 'web', 'index.html'), join(dist, 'index.html'));
cpSync(join(frontend, 'web', 'main.js'), join(dist, 'main.js'));
cpSync(join(frontend, 'src', 'app.js'), join(dist, 'app.js'));
cpSync(images, join(dist, 'app', 'static', 'img'), { recursive: true });
writeFileSync(join(dist, 'config.js'), `window.RR_CONFIG = ${JSON.stringify({ apiBase })};\n`);

console.log(`\nBuilt ${dist}\n  API: ${apiBase}\n  files: ${readdirSync(dist).join(', ')}`);
