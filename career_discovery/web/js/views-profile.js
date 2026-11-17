import { LANG_CODES, LEVELS, LEVEL_GUIDE, LEVEL_LABEL, api, busy, button, errorBox, fmtDate, h, langName, notice, reasonText, say, t } from './util.js';

const EVIDENCE_STATE = {
  cv_stated: () => t('cv.state.cv'),
  user_confirmed: () => t('cv.state.you'),
  inferred: () => t('cv.state.check'),
  missing: () => t('cv.state.missing'),
};

export async function cvView(root, ctx) {
  root.append(h('h1', { text: t('cv.title') }), h('p', { class: 'lead', text: t('cv.intro') }));
  const body = h('div', {});
  root.append(body);
  // Stay on this step after an upload so the user reviews what was found before moving on.
  const review = () => (location.hash === '#/cv' ? ctx.rerender() : ctx.go('cv'));
  if (!ctx.state.profile.exists) { body.append(uploadPanel(ctx, review)); return; }
  await renderEvidence(body, ctx);
}

function uploadPanel(ctx, after, replacing = false) {
  const progress = h('div', { hidden: true }, h('p', { role: 'status', text: t('cv.reading') }), h('progress', { 'aria-label': t('cv.reading') }));
  const errors = h('div', {});
  const input = h('input', { type: 'file', class: 'sr', accept: '.docx,.pdf', tabindex: '-1', 'aria-hidden': 'true' });
  const send = async (file) => {
    if (!file) return;
    errors.replaceChildren();
    progress.hidden = false;
    try {
      const form = new FormData();
      form.append('file', file);
      await api('POST', '/api/profile/cv', form);
      say(t('cv.done'));
      await after();
    } catch (err) { errors.append(errorBox(err)); } finally { progress.hidden = true; }
  };
  input.addEventListener('change', () => send(input.files[0]));
  const pick = button(replacing ? t('cv.replace') : t('cv.choose'), () => input.click(), replacing ? '' : 'primary');
  const zone = h('div', { class: 'dropzone' }, h('p', { text: t('cv.drop') }), pick, input, h('p', { class: 'hint', text: t('cv.formats') }));
  zone.addEventListener('dragover', (e) => { e.preventDefault(); zone.classList.add('over'); });
  zone.addEventListener('dragleave', () => zone.classList.remove('over'));
  zone.addEventListener('drop', (e) => { e.preventDefault(); zone.classList.remove('over'); send(e.dataTransfer.files[0]); });
  const parts = [zone, progress, errors];
  if (!replacing) {
    parts.push(h('p', { class: 'muted', text: t('cv.noCvIntro') }),
      button(t('cv.noCv'), async (e) => {
        try { await busy(e.currentTarget, () => api('POST', '/api/profile/new', { replace: false })); await after(); } catch (err) { errors.append(errorBox(err)); }
      }));
  }
  return h('div', {}, parts);
}

async function renderEvidence(body, ctx) {
  const data = await api('GET', '/api/profile');
  const items = data.profile.evidence || [];
  const errors = h('div', {});
  const again = () => ctx.rerender();
  const usable = items.filter((e) => e.state === 'cv_stated' || e.state === 'user_confirmed').length;
  body.append(h('div', { class: 'card' },
    data.cv ? h('p', {}, h('b', { text: t('cv.file') }), ' ', data.cv.name) : h('p', { text: t('cv.noFile') }),
    h('p', { class: 'muted', text: t('cv.count', { n: usable }) })));
  if (!items.length) body.append(notice('info', t('cv.empty')));
  const act = (action, id, text) => api('POST', '/api/profile/evidence', { action, id, text }).then(again).catch((err) => errors.replaceChildren(errorBox(err)));
  const list = h('ul', { class: 'list' }, items.map((item) => evidenceRow(item, act)));
  if (items.length) body.append(h('h2', { text: t('cv.listTitle') }), h('p', { class: 'hint', text: t('cv.listHint') }), list);
  body.append(errors, addForm(act));
  body.append(h('details', {}, h('summary', { text: t('cv.moreOptions') }),
    uploadPanel(ctx, again, true),
    button(t('cv.startOver'), async () => {
      if (!confirm(t('cv.startOverConfirm'))) return;
      try { await api('POST', '/api/profile/new', { replace: true }); await again(); } catch (err) { errors.replaceChildren(errorBox(err)); }
    }, 'danger')));
  body.append(h('div', { class: 'row' }, button(t('cv.next'), () => ctx.go('details'), 'primary')));
}

function evidenceRow(item, act) {
  const view = h('li', {});
  const show = () => {
    const stateKind = item.state === 'inferred' ? 'warn' : '';
    view.replaceChildren(
      h('p', {}, item.text),
      h('p', { class: 'src' }, h('span', { class: `badge ${stateKind}`, text: (EVIDENCE_STATE[item.state] || (() => item.state))() }), ' ',
        item.locator ? t('cv.source', { line: item.locator }) : ''),
      h('div', { class: 'row tight' },
        item.state === 'inferred' ? button(t('cv.keep'), () => act('keep', item.id)) : null,
        button(t('cv.edit'), edit),
        button(t('cv.remove'), () => act('remove', item.id), 'danger quiet')));
  };
  const edit = () => {
    const box = h('textarea', { id: `edit-${item.id}`, value: item.text });
    view.replaceChildren(h('label', { for: box.id, text: t('cv.editLabel') }), box,
      h('div', { class: 'row tight' }, button(t('cv.save'), () => act('edit', item.id, box.value.trim())), button(t('cv.cancel'), show, 'quiet')));
    box.focus();
  };
  show();
  return view;
}

function addForm(act) {
  const box = h('textarea', { id: 'add-evidence', placeholder: t('cv.addPlaceholder') });
  return h('div', { class: 'card' }, h('label', { for: 'add-evidence', text: t('cv.addLabel') }), h('p', { class: 'hint', text: t('cv.addHint') }), box,
    h('div', { class: 'row tight' }, button(t('cv.add'), () => { if (box.value.trim()) act('add', null, box.value.trim()); })));
}

export const EMPLOYMENT = [
  ['full_time', () => t('emp.full_time')], ['part_time', () => t('emp.part_time')], ['internship', () => t('emp.internship')],
  ['working_student', () => t('emp.working_student')], ['freelance', () => t('emp.freelance')], ['contract', () => t('emp.contract')],
  ['temporary', () => t('emp.temporary')], ['trainee', () => t('emp.trainee')],
];
const splitList = (text) => text.split(/[,\n;]/).map((s) => s.trim()).filter(Boolean);

export async function detailsView(root, ctx) {
  root.append(h('h1', { text: t('details.title') }), h('p', { class: 'lead', text: t('details.intro') }));
  let profile;
  try { profile = (await api('GET', '/api/profile')).profile; } catch (err) {
    if (err.code !== 'no_profile') throw err;
    root.append(notice('info', t('details.needCv')), button(t('details.toCv'), () => ctx.go('cv'), 'primary'));
    return;
  }
  const errs = {};
  const field = (name, ...kids) => { const slot = h('div', {}); errs[name] = slot; return h('div', { class: 'field' }, kids, slot); };
  const langRows = h('div', {});
  const addRow = (code = 'de', level = 'B1') => {
    const codes = LANG_CODES.includes(code) ? LANG_CODES : [...LANG_CODES, code];
    const row = h('div', { class: 'lang-row' },
      h('select', { 'aria-label': t('details.langName') }, codes.map((c) => h('option', { value: c, selected: c === code }, langName(c)))),
      h('select', { 'aria-label': t('details.langLevel') }, LEVELS.map((l) => h('option', { value: l, selected: l === level }, LEVEL_LABEL[l]()))),
      button(t('details.removeLang'), () => row.remove(), 'quiet'));
    langRows.append(row);
  };
  Object.entries(profile.languages || {}).forEach(([c, l]) => addRow(c, l));
  const guide = h('details', {}, h('summary', { text: t('details.guideTitle') }), h('ul', { class: 'list' }, LEVELS.map((l) => h('li', {}, h('b', { text: l }), ' ', LEVEL_GUIDE[l]()))));
  const cities = h('input', { type: 'text', id: 'f-cities', value: (profile.locations || []).join(', ') });
  const remote = h('input', { type: 'text', id: 'f-remote', value: (profile.remote_regions || []).join(', ') });
  const titles = h('input', { type: 'text', id: 'f-titles', value: (profile.search_titles || []).join(', ') });
  const emp = EMPLOYMENT.map(([id, label]) => ({ id, box: h('input', { type: 'checkbox', checked: (profile.employment || []).includes(id) }), label }));
  const tri = (value) => (value === true ? 'true' : value === false ? 'false' : '');
  const select = (id, current, yes, no) => h('select', { id }, h('option', { value: '', selected: current === '' }, t('details.noAnswer')),
    h('option', { value: 'true', selected: current === 'true' }, yes), h('option', { value: 'false', selected: current === 'false' }, no));
  const sponsor = select('f-sponsor', tri(profile.needs_sponsorship), t('details.sponsorYes'), t('details.sponsorNo'));
  const grad = select('f-grad', tri(profile.recent_graduate), t('details.gradYes'), t('details.gradNo'));
  const form = h('form', { novalidate: true },
    field('languages', h('p', { class: 'label', text: t('details.languages') }), h('p', { class: 'hint', text: t('details.languagesHint') }), langRows,
      button(t('details.addLang'), () => addRow('en', 'B2'), 'quiet'), guide),
    field('locations', h('label', { for: 'f-cities', text: t('details.cities') }), h('p', { class: 'hint', text: t('details.citiesHint') }), cities),
    field('remote_regions', h('label', { for: 'f-remote', text: t('details.remote') }), h('p', { class: 'hint', text: t('details.remoteHint') }), remote),
    field('employment', h('fieldset', {}, h('legend', { text: t('details.employment') }),
      h('div', { class: 'checks' }, emp.map((e) => h('label', { class: 'check' }, e.box, e.label()))))),
    field('search_titles', h('label', { for: 'f-titles', text: t('details.titles') }), h('p', { class: 'hint', text: t('details.titlesHint') }), titles),
    field('needs_sponsorship', h('label', { for: 'f-sponsor', text: t('details.sponsor') }), sponsor),
    field('recent_graduate', h('label', { for: 'f-grad', text: t('details.grad') }), grad));
  const result = h('div', {});
  const save = button(t('details.confirm'), async (e) => {
    result.replaceChildren();
    Object.values(errs).forEach((slot) => slot.replaceChildren());
    const languages = {};
    for (const row of langRows.children) languages[row.children[0].value] = row.children[1].value;
    const tv = (v) => (v === '' ? null : v === 'true');
    const payload = {
      languages, locations: splitList(cities.value), remote_regions: splitList(remote.value).map((c) => c.toUpperCase()),
      employment: emp.filter((x) => x.box.checked).map((x) => x.id), search_titles: splitList(titles.value),
      needs_sponsorship: tv(sponsor.value), recent_graduate: tv(grad.value),
    };
    try {
      await busy(e.currentTarget, async () => { await api('PUT', '/api/profile', payload); await api('POST', '/api/profile/confirm', {}); });
      say(t('details.saved'));
      // With jobs already stored the matches are redone straight away, so go there; otherwise fetch jobs first.
      ctx.go((await ctx.refresh()).jobs?.stored ? 'matches' : 'jobs');
    } catch (err) {
      for (const [name, message] of Object.entries(err.fields || {})) errs[name]?.append(h('p', { class: 'field-error', role: 'alert', text: message }));
      result.append(errorBox({ message: err.message }));
      if (err.status === 422 && !Object.keys(err.fields || {}).length) result.append(button(t('details.toCv'), () => ctx.go('cv')));
    }
  }, 'primary');
  root.append(h('div', { class: 'card' }, form), result, h('div', { class: 'row' }, save));
}

const BOARD_STATUS = {
  refreshed: () => t('jobs.board.refreshed'), cached: () => t('jobs.board.cached'), unavailable: () => t('jobs.board.unavailable'),
  budget: () => t('jobs.board.budget'), superseded: () => t('jobs.board.superseded'),
};

export async function jobsView(root, ctx) {
  root.append(h('h1', { text: t('jobs.title') }), h('p', { class: 'lead', text: t('jobs.intro') }));
  const summary = h('div', { class: 'card' });
  const live = h('div', {});
  const importBox = h('div', {});
  const stats = async () => {
    const jobs = (await ctx.refresh()).jobs;
    summary.replaceChildren(jobs.stored
      ? h('p', {}, t('jobs.stored', { n: jobs.stored }), ' ', jobs.last_fetched ? t('jobs.lastFetched', { date: fmtDate(jobs.last_fetched) }) : '')
      : h('p', { text: t('jobs.none') }));
    // The next step is the main action once jobs are stored; before that, reading the boards is.
    next.hidden = !jobs.stored;
    go.className = jobs.stored ? 'btn' : 'btn primary';
  };
  const go = button(t('jobs.refresh'), (e) => start(e.currentTarget), 'primary');
  const next = button(t('jobs.next'), () => ctx.go('matches'), 'primary', { hidden: true });
  await stats();
  const poll = async () => {
    while (ctx.alive()) {
      const st = await api('GET', '/api/jobs/refresh');
      drawProgress(live, st);
      if (st.status !== 'running') { go.disabled = false; await stats(); return; }
      await new Promise((r) => setTimeout(r, 1000));
    }
  };
  const start = async (btn) => {
    try { await api('POST', '/api/jobs/refresh', {}); } catch (err) { if (err.code !== 'refresh_running') { live.replaceChildren(errorBox(err)); return; } }
    btn.disabled = true;
    poll().catch((err) => { live.replaceChildren(errorBox(err)); go.disabled = false; });
  };
  const csv = h('input', { type: 'file', accept: '.csv', id: 'f-csv', class: 'sr' });
  csv.addEventListener('change', async () => {
    if (!csv.files[0]) return;
    const form = new FormData();
    form.append('file', csv.files[0]);
    try { const r = await api('POST', '/api/jobs/import', form); importBox.replaceChildren(notice('info', t('jobs.imported', { n: r.imported }))); await stats(); } catch (err) { importBox.replaceChildren(errorBox(err)); }
  });
  root.append(summary, h('div', { class: 'row' }, go), live,
    h('details', {}, h('summary', { text: t('jobs.csvTitle') }), h('p', { class: 'hint', text: t('jobs.csvHint') }),
      button(t('jobs.csvChoose'), () => csv.click()), csv, importBox),
    h('div', { class: 'row' }, next));
  if (ctx.state.refresh?.status === 'running') { go.disabled = true; poll().catch(() => { go.disabled = false; }); }
  else if (ctx.state.refresh?.status === 'done') drawProgress(live, ctx.state.refresh);
}

function drawProgress(live, st) {
  const parts = [];
  if (st.status === 'running') {
    parts.push(h('p', { role: 'status', text: t('jobs.progress', { done: st.done, total: st.total }) }),
      h('progress', { max: st.total || 1, value: st.done, 'aria-label': t('jobs.progressLabel') }));
  } else if (st.status === 'error') {
    parts.push(notice('danger', st.error || t('error.generic')));
  } else if (st.status === 'done') {
    parts.push(notice('info', t('jobs.done')));
  }
  if (st.boards?.length) {
    parts.push(h('ul', { class: 'list' }, st.boards.map((b) => h('li', {}, h('b', { text: b.company || b.board }), ': ',
      (BOARD_STATUS[b.status] || (() => b.status))(), b.count != null ? ` (${b.count})` : '', b.reason ? ` ${reasonText(b.reason)}` : ''))));
  }
  live.replaceChildren(...parts);
}
