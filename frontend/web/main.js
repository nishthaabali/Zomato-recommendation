// Standalone entry point: mounts the same page component Streamlit mounts (./app.js), but feeds it from the
// JSON API instead of Streamlit. The component receives the same `data` shape and reports searches through
// setTriggerValue; here those become fetch() calls.
//
//   GET  {apiBase}/api/meta       -> search-independent page data (once, at load)
//   POST {apiBase}/api/recommend  -> {prefs, view} for one search

import mount from './app.js';

const API = String((window.RR_CONFIG || {}).apiBase || '').replace(/\/+$/, '');
const SEARCH_TIMEOUT_MS = 60000;   // the server gives the LLM up to 45 s, plus retries
const META_ATTEMPTS = 4;           // a sleeping/cold-starting backend can need a few seconds

const host = document.getElementById('app').attachShadow({ mode: 'open' });
host.innerHTML = '<link rel="stylesheet" href="app.css">';

let meta = null;
let state = { prefs: null, view: null, error: false, served: 0 };

const sleep = (ms) => new Promise((r) => setTimeout(r, ms));
const pageStyle = 'min-height:100vh;display:flex;align-items:center;justify-content:center;flex-direction:column;gap:16px;'
  + 'background:#0e0e11;color:#e4e1e6;font-family:Inter,system-ui,sans-serif;text-align:center;padding:24px';

function showStatus(html) {
  let el = host.getElementById('rr-status');
  if (!el) {
    el = document.createElement('div');
    el.id = 'rr-status';
    host.appendChild(el);
  }
  el.setAttribute('style', pageStyle);
  el.innerHTML = html;
  return el;
}

function hideStatus() {
  const el = host.getElementById('rr-status');
  if (el) el.remove();
}

async function getJson(path, { method = 'GET', body, timeout = 15000 } = {}) {
  const ctrl = new AbortController();
  const timer = setTimeout(() => ctrl.abort(), timeout);
  try {
    const res = await fetch(`${API}${path}`, {
      method,
      signal: ctrl.signal,
      headers: body ? { 'Content-Type': 'application/json' } : undefined,
      body: body ? JSON.stringify(body) : undefined,
    });
    if (!res.ok) throw new Error(`HTTP ${res.status}`);
    return await res.json();
  } finally {
    clearTimeout(timer);
  }
}

function render() {
  mount({ data: { ...meta, ...state }, parentElement: host, setTriggerValue: onTrigger });
}

async function onTrigger(name, payload) {
  if (name === 'reset') {
    state = { prefs: { ...meta.defaults }, view: null, error: false, served: Date.now() };
    render();
    return;
  }
  if (name !== 'submit') return;
  try {
    const { prefs, view } = await getJson('/api/recommend', { method: 'POST', body: payload, timeout: SEARCH_TIMEOUT_MS });
    state = { prefs, view, error: false, served: payload.nonce };
  } catch (err) {
    console.error('Search failed:', err);
    // Keep any earlier results on screen; the page shows its "Something went wrong" banner.
    state = { ...state, error: true, served: payload.nonce };
  }
  render();
}

async function start() {
  if (!API) {
    showStatus('<h1 style="font-size:20px;margin:0">Not configured</h1>'
      + '<p style="margin:0;color:#a1a1aa">The API address is missing. Set API_BASE_URL when building the site.</p>');
    return;
  }
  showStatus('<div style="width:32px;height:32px;border:3px solid #2a2a32;border-top-color:#e23744;border-radius:50%;animation:rr-spin 1s linear infinite"></div>'
    + '<style>@keyframes rr-spin{to{transform:rotate(360deg)}}</style>'
    + '<p style="margin:0;color:#a1a1aa" id="rr-status-text">Loading restaurants…</p>');
  for (let attempt = 1; attempt <= META_ATTEMPTS; attempt++) {
    try {
      meta = await getJson('/api/meta');
      break;
    } catch (err) {
      console.error(`Could not load page data (attempt ${attempt}):`, err);
      if (attempt === META_ATTEMPTS) {
        const el = showStatus('<h1 style="font-size:20px;margin:0">We could not reach the restaurant service</h1>'
          + '<p style="margin:0;color:#a1a1aa">Please check your connection and try again.</p>'
          + '<button id="rr-retry" type="button" style="background:#e23744;color:#fff;border:0;border-radius:12px;padding:10px 20px;font-weight:600;cursor:pointer">Try again</button>');
        el.querySelector('#rr-retry').addEventListener('click', start);
        return;
      }
      const text = host.getElementById('rr-status-text');
      if (text) text.textContent = 'Waking up the server…';
      await sleep(1500 * attempt);
    }
  }
  state.prefs = { ...meta.defaults };
  hideStatus();
  render();
}

start();
