const store = { code: 'en', dict: {}, fallback: {}, reasons: null };
const token = document.querySelector('meta[name="cd-token"]')?.content || '';

function lookup(key, vars) {
  const raw = store.dict[key] ?? store.fallback[key] ?? key;
  return vars ? raw.replace(/\{(\w+)\}/g, (_, name) => String(vars[name] ?? '')) : raw;
}

export const t = (key, vars) => lookup(key, vars);

export function langCode() { return store.code; }

export async function loadLanguage(code) {
  const load = async (c) => (await fetch(`i18n/${c}.json`)).json();
  if (!Object.keys(store.fallback).length) store.fallback = await load('en');
  store.dict = code === 'en' ? store.fallback : await load(code);
  store.reasons = code === 'de' ? await loadReasons() : null;
  store.code = code;
  document.documentElement.lang = code;
  applyStatic(document);
}

// The matcher writes its reasons in English. In German, each known sentence is swapped for its entry in
// i18n/reasons.de.json; an unknown sentence stays English. tests/test_reasons.py mirrors this logic.
const SENTENCE = /(?<=[.!?])\s+(?=[A-Z(])/;

async function loadReasons() {
  try {
    const data = await (await fetch('i18n/reasons.de.json')).json();
    const sentences = data.sentences.map(([en, de]) => {
      const names = [];
      const source = en.split(/(\{\w+\})/).map((part) => {
        const slot = /^\{(\w+)\}$/.exec(part);
        if (slot) { names.push(slot[1]); return '(.+?)'; }
        return part.replace(/[.*+?^${}()|[\]\\]/g, '\\$&');
      }).join('');
      return { re: new RegExp(`^${source}$`), names, de };
    });
    return { sentences, values: data.values || {} };
  } catch { return null; }
}

function reasonValue(name, raw) {
  return store.reasons.values[name]?.[raw] ?? raw;
}

export function reasonText(text) {
  if (!text || !store.reasons) return text || '';
  return text.split(SENTENCE).map((sentence) => {
    for (const entry of store.reasons.sentences) {
      const found = entry.re.exec(sentence);
      if (found) return entry.de.replace(/\{(\w+)\}/g, (_, name) => reasonValue(name, found[entry.names.indexOf(name) + 1]));
    }
    return sentence;
  }).join(' ');
}

export function statusText(state) {
  return (store.reasons && store.reasons.values.status?.[state]) || state || '';
}

export function applyStatic(root) {
  const map = [['data-i18n', null], ['data-i18n-aria-label', 'aria-label'], ['data-i18n-title', 'title'],
    ['data-i18n-placeholder', 'placeholder']];
  for (const [attr, target] of map) {
    for (const el of root.querySelectorAll(`[${attr}]`)) {
      const text = lookup(el.getAttribute(attr));
      if (target) el.setAttribute(target, text); else el.textContent = text;
    }
  }
  document.title = t('app.name');
}

export function h(tag, props, ...kids) {
  const el = document.createElement(tag);
  for (const [k, v] of Object.entries(props || {})) {
    if (v == null || v === false) continue;
    if (k === 'class') el.className = v;
    else if (k === 'text') el.textContent = v;
    else if (k.startsWith('on')) el.addEventListener(k.slice(2), v);
    else if (['value', 'checked', 'disabled', 'selected', 'max'].includes(k)) el[k] = v;
    else if (k !== 'style') el.setAttribute(k, v === true ? '' : v);
  }
  append(el, kids);
  return el;
}

function append(el, kids) {
  for (const kid of kids) {
    if (kid == null || kid === false) continue;
    if (Array.isArray(kid)) append(el, kid);
    else el.append(kid instanceof Node ? kid : document.createTextNode(String(kid)));
  }
}

export function icon(name) {
  const span = document.createElement('span');
  span.innerHTML = `<svg class="icon" aria-hidden="true" focusable="false"><use href="#i-${name}"></use></svg>`;
  return span.firstChild;
}

export class ApiError extends Error {
  constructor(status, code, message, fields) {
    super(message);
    Object.assign(this, { status, code, fields: fields || {} });
  }
}

export async function api(method, path, body) {
  const opts = { method, headers: { 'X-CD-Token': token } };
  if (body instanceof FormData) opts.body = body;
  else if (body !== undefined) {
    opts.headers['Content-Type'] = 'application/json';
    opts.body = JSON.stringify(body);
  }
  let res;
  try { res = await fetch(path, opts); } catch { throw new ApiError(0, 'network', t('error.network')); }
  let data = null;
  try { data = await res.json(); } catch { data = null; }
  if (!res.ok) {
    const err = data?.error || {};
    throw new ApiError(res.status, err.code || 'internal_error', err.message || t('error.generic'), err.fields);
  }
  return data;
}

export async function download(path, fallbackName) {
  const res = await fetch(path, { headers: { 'X-CD-Token': token } });
  if (!res.ok) {
    let err = {};
    try { err = (await res.json()).error || {}; } catch { err = {}; }
    throw new ApiError(res.status, err.code || 'internal_error', err.message || t('error.generic'));
  }
  const blob = await res.blob();
  const match = /filename\*?=(?:UTF-8'')?"?([^";]+)"?/i.exec(res.headers.get('Content-Disposition') || '');
  const link = h('a', { href: URL.createObjectURL(blob), download: match ? decodeURIComponent(match[1]) : fallbackName });
  document.body.append(link);
  link.click();
  link.remove();
  setTimeout(() => URL.revokeObjectURL(link.href), 10000);
}

export function say(message) {
  const box = document.getElementById('status');
  box.textContent = message;
  clearTimeout(say.timer);
  say.timer = setTimeout(() => { box.textContent = ''; }, 6000);
}

export function errorBox(err) {
  const fields = Object.values(err.fields || {});
  return h('div', { class: 'alert danger', role: 'alert' }, icon('warn'),
    h('div', {}, h('p', { text: err.message || t('error.generic') }), fields.map((m) => h('p', { class: 'small', text: m }))));
}

export function notice(kind, text) {
  return h('div', { class: `alert ${kind}`, role: kind === 'danger' ? 'alert' : null }, icon(kind === 'info' ? 'info' : 'warn'), h('p', { text }));
}

export function emptyState(titleText, bodyText, action) {
  return h('div', { class: 'card empty' }, h('h2', { text: titleText }), h('p', { class: 'muted', text: bodyText }), action);
}

export async function busy(button, task) {
  button.disabled = true;
  button.setAttribute('aria-busy', 'true');
  try { return await task(); } finally { button.disabled = false; button.removeAttribute('aria-busy'); }
}

export function button(label, onclick, kind = '', extra = {}) {
  return h('button', { type: 'button', class: `btn ${kind}`.trim(), onclick, ...extra }, label);
}

export function fmtDate(value) {
  if (!value) return '';
  const day = /^\d{4}-\d{2}-\d{2}$/.test(value);
  const date = new Date(day ? `${value}T12:00:00Z` : value);
  if (Number.isNaN(date.getTime())) return value;
  return new Intl.DateTimeFormat(store.code, { dateStyle: 'medium', timeZone: day ? 'UTC' : 'Europe/Berlin' }).format(date);
}

export function safeUrl(value) {
  try {
    const url = new URL(value);
    return ['http:', 'https:'].includes(url.protocol) ? url.href : null;
  } catch { return null; }
}

export function textOf(item) {
  if (typeof item === 'string') return item;
  if (item && typeof item === 'object') {
    for (const key of ['message', 'text', 'summary', 'reason', 'label', 'detail']) {
      if (typeof item[key] === 'string') return item[key];
    }
  }
  return '';
}

export function langName(code) {
  const names = { de: t('lang.de'), en: t('lang.en'), fr: t('lang.fr'), es: t('lang.es'), it: t('lang.it'),
    pt: t('lang.pt'), nl: t('lang.nl'), pl: t('lang.pl'), tr: t('lang.tr'), ar: t('lang.ar'), ru: t('lang.ru'),
    uk: t('lang.uk'), zh: t('lang.zh'), hi: t('lang.hi') };
  return names[code] || String(code).toUpperCase();
}
export const LANG_CODES = ['de', 'en', 'fr', 'es', 'it', 'pt', 'nl', 'pl', 'tr', 'ar', 'ru', 'uk', 'zh', 'hi'];
export const LEVELS = ['A1', 'A2', 'B1', 'B2', 'C1', 'C2'];

export const LEVEL_LABEL = {
  A1: () => t('level.A1'), A2: () => t('level.A2'), B1: () => t('level.B1'),
  B2: () => t('level.B2'), C1: () => t('level.C1'), C2: () => t('level.C2'),
};
export const LEVEL_GUIDE = {
  A1: () => t('guide.A1'), A2: () => t('guide.A2'), B1: () => t('guide.B1'),
  B2: () => t('guide.B2'), C1: () => t('guide.C1'), C2: () => t('guide.C2'),
};
