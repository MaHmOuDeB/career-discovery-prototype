import { api, applyStatic, errorBox, h, icon, loadLanguage, say, t } from './util.js';
import { cvView, detailsView, jobsView } from './views-profile.js';
import { applicationsView, dataView, matchesView } from './views-work.js';

const STEPS = [
  { id: 'cv', label: () => t('step.cv') },
  { id: 'details', label: () => t('step.details') },
  { id: 'jobs', label: () => t('step.jobs') },
  { id: 'matches', label: () => t('step.matches') },
];
const PAGES = { cv: cvView, details: detailsView, jobs: jobsView, matches: matchesView, applications: applicationsView, data: dataView };
const ctx = { state: null, generation: 0, go, refresh, alive: () => true, rerender: () => render() };

function go(route) { location.hash = `#/${route}`; }

async function refresh() {
  ctx.state = await api('GET', '/api/state');
  return ctx.state;
}

function currentRoute() {
  const route = location.hash.replace(/^#\/?/, '');
  return PAGES[route] ? route : (ctx.state?.step || 'cv');
}

function renderSteps(route) {
  const reach = STEPS.findIndex((s) => s.id === ctx.state.step);
  const nav = document.getElementById('steps');
  nav.replaceChildren(h('ol', { class: 'steps' }, STEPS.map((step, i) => {
    const current = step.id === route;
    const done = i < reach || (i === reach && !current && ctx.state.step === 'matches');
    const body = [h('span', { class: 'num', 'aria-hidden': 'true' }, done && !current ? icon('check') : String(i + 1)), step.label()];
    const props = { class: `step${done ? ' done' : ''}`, 'aria-current': current ? 'step' : null };
    return h('li', {}, i <= reach
      ? h('a', { ...props, href: `#/${step.id}` }, body)
      : h('span', { ...props, 'aria-disabled': 'true' }, body));
  })));
  for (const id of ['applications', 'data']) {
    const link = document.getElementById(`nav-${id}`);
    if (id === route) link.setAttribute('aria-current', 'page'); else link.removeAttribute('aria-current');
  }
}

async function render() {
  const main = document.getElementById('main');
  const mine = ++ctx.generation;
  ctx.alive = () => mine === ctx.generation;
  try {
    await refresh();
  } catch (err) {
    main.replaceChildren(errorBox(err), h('button', { type: 'button', class: 'btn primary', onclick: render }, t('error.retry')));
    return;
  }
  const route = currentRoute();
  renderSteps(route);
  const view = h('div', {});
  main.replaceChildren(view);
  try {
    await PAGES[route](view, ctx);
  } catch (err) {
    view.append(errorBox(err));
  }
  if (ctx.alive() && route !== ctx.lastRoute) main.focus({ preventScroll: true });
  ctx.lastRoute = route;
}

function setupLanguageSwitch() {
  for (const btn of document.querySelectorAll('.lang')) {
    btn.addEventListener('click', async () => {
      try { localStorage.setItem('cd-lang', btn.dataset.lang); } catch { /* storage may be blocked */ }
      await loadLanguage(btn.dataset.lang);
      markLanguage();
      render();
    });
  }
}

function markLanguage() {
  for (const btn of document.querySelectorAll('.lang')) btn.setAttribute('aria-pressed', String(btn.dataset.lang === document.documentElement.lang));
}

function initialLanguage() {
  try {
    const saved = localStorage.getItem('cd-lang');
    if (saved === 'en' || saved === 'de') return saved;
  } catch { /* storage may be blocked */ }
  return (navigator.language || 'en').toLowerCase().startsWith('de') ? 'de' : 'en';
}

async function start() {
  await loadLanguage(initialLanguage());
  applyStatic(document);
  markLanguage();
  setupLanguageSwitch();
  document.querySelector('.skip').addEventListener('click', (event) => {
    event.preventDefault();
    document.getElementById('main').focus();
  });
  window.addEventListener('hashchange', render);
  window.addEventListener('unhandledrejection', () => say(t('error.generic')));
  render();
}

start();
