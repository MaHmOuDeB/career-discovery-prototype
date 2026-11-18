import { EMPLOYMENT } from './views-profile.js';
import { api, busy, button, download, emptyState, errorBox, fmtDate, h, icon, langName, notice, safeUrl, reasonText, say, statusText, t, textOf } from './util.js';

const FIT = {
  actionable: () => t('fit.good'),
  'verify first': () => t('fit.look'),
  excluded: () => t('fit.no'),
};
const FIT_KIND = { actionable: '', 'verify first': 'warn', excluded: 'danger' };
const STATUS = {
  saved: () => t('status.saved'), applied: () => t('status.applied'), interview: () => t('status.interview'),
  offer: () => t('status.offer'), rejected: () => t('status.rejected'), withdrawn: () => t('status.withdrawn'),
};
const LANG_STATE = { met: () => t('lang.met'), unknown: () => t('lang.unknown'), conflict: () => t('lang.conflict') };
const LANG_KIND = { met: '', unknown: 'plain', conflict: 'danger' };
const WORKPLACE = { remote: () => t('work.remote'), hybrid: () => t('work.hybrid'), onsite: () => t('work.onsite'), on_site: () => t('work.onsite') };

function pref(name, fallback) {
  try { const v = localStorage.getItem(`cd-${name}`); return v === null ? fallback : v === '1'; } catch { return fallback; }
}
function setPref(name, value) {
  try { localStorage.setItem(`cd-${name}`, value ? '1' : '0'); } catch { /* storage may be blocked */ }
}

export async function matchesView(root, ctx) {
  root.append(h('h1', { text: t('matches.title') }), h('p', { class: 'lead', text: t('matches.intro') }));
  if (!ctx.state.profile.confirmed) {
    root.append(emptyState(t('matches.needProfileTitle'), t('matches.needProfile'), button(t('matches.toDetails'), () => ctx.go('details'), 'primary')));
    return;
  }
  const opts = { hide: pref('hide-lang', false), title: pref('compare-title', false), excluded: pref('show-excluded', false) };
  const results = h('div', { 'aria-live': 'polite' });
  const toggle = (key, label, hint) => {
    const box = h('input', { type: 'checkbox', checked: opts[key] });
    box.addEventListener('change', () => { opts[key] = box.checked; setPref({ hide: 'hide-lang', title: 'compare-title', excluded: 'show-excluded' }[key], box.checked); load(); });
    return h('label', { class: 'check' }, box, label, hint ? h('span', { class: 'sr', text: hint }) : null);
  };
  const filter = h('input', { type: 'search', id: 'f-filter', maxlength: '100', placeholder: t('matches.filterPlaceholder') });
  let timer;
  filter.addEventListener('input', () => { clearTimeout(timer); timer = setTimeout(() => load(), 350); });
  opts.clear = () => { filter.value = ''; load(); filter.focus(); };
  root.append(lookingFor(ctx), h('div', { class: 'card' },
    h('div', { class: 'field' }, h('label', { for: 'f-filter', text: t('matches.filterLabel') }), filter),
    toggle('hide', t('matches.hideLang')), toggle('title', t('matches.compareTitle')), toggle('excluded', t('matches.showExcluded'))), results);
  let request = 0;
  const load = async () => {
    const sequence = ++request;
    results.replaceChildren(h('p', { role: 'status', text: t('matches.loading') }), h('progress', { 'aria-label': t('matches.loading') }));
    const words = filter.value.trim();
    opts.q = words;
    const query = `mode=${opts.title ? 'both' : 'task'}&limit=50&duties=1&excluded=${opts.excluded ? 1 : 0}&hide_language_conflicts=${opts.hide ? 1 : 0}`
      + (words ? `&q=${encodeURIComponent(words)}` : '');
    try {
      const data = await api('GET', `/api/matches?${query}`);
      if (!ctx.alive() || sequence !== request) return;
      results.replaceChildren(...drawResults(data, ctx, opts));
      api('POST', '/api/summary/seen', {}).catch(() => {});
    } catch (err) {
      if (!ctx.alive() || sequence !== request) return;
      results.replaceChildren(err.code === 'profile_not_ready'
        ? emptyState(t('matches.needProfileTitle'), err.message, button(t('matches.toDetails'), () => ctx.go('details'), 'primary'))
        : errorBox(err));
    }
  };
  await load();
  api('GET', '/api/families').then((f) => { if (ctx.alive() && f.families?.length) root.append(families(f.families)); }).catch(() => {});
}

function lookingFor(ctx) {
  const box = h('div', { class: 'card' }, h('h2', { class: 'label', text: t('matches.lookingFor') }), h('p', { role: 'status', text: t('matches.loading') }));
  const list = (items) => (items && items.length ? items.join(', ') : t('matches.notSet'));
  const kinds = Object.fromEntries(EMPLOYMENT);
  api('GET', '/api/profile').then(({ profile: p }) => {
    if (!ctx.alive()) return;
    const langs = Object.entries(p.languages || {}).map(([code, level]) => `${langName(code)} ${level}`);
    box.replaceChildren(h('h2', { class: 'label', text: t('matches.lookingFor') }),
      h('ul', { class: 'facts' },
        h('li', { text: t('matches.places', { list: list(p.locations) }) }),
        h('li', { text: t('matches.remote', { list: list(p.remote_regions) }) }),
        h('li', { text: t('matches.kinds', { list: list((p.employment || []).map((k) => (kinds[k] ? kinds[k]() : k))) }) }),
        h('li', { text: t('matches.langs', { list: list(langs) }) })),
      h('p', { class: 'hint', text: t('matches.changeHint') }),
      h('div', { class: 'row' }, button(t('matches.change'), () => ctx.go('details'))));
  }).catch(() => box.remove());
  return box;
}

function families(list) {
  return h('details', { class: 'card' }, h('summary', { text: t('matches.familiesTitle') }), h('p', { class: 'hint', text: t('matches.familiesHint') }),
    h('ul', { class: 'list' }, list.map((f) => h('li', {}, h('b', { text: f.label }),
      Array.isArray(f.aliases) && f.aliases.length ? h('span', { class: 'muted', text: ` · ${f.aliases.slice(0, 4).join(', ')}` }) : null))));
}

function drawResults(data, ctx, opts) {
  const out = [];
  const task = data.results?.task || {};
  const lanes = ['actionable', 'verify first', ...(opts.excluded ? ['excluded'] : [])];
  const shown = lanes.reduce((n, l) => n + (task[l]?.length || 0), 0);
  const c = data.counts?.task || {};
  const found = lanes.reduce((n, l) => n + (data.shown?.task?.[l] ?? 0), 0);
  if (opts.q && found) {
    out.push(h('p', { class: 'muted', role: 'status', text: found === 1 ? t('matches.filterOne', { q: opts.q }) : t('matches.filterCount', { n: found, q: opts.q }) }));
  } else if (opts.q) {
    out.push(emptyState(t('matches.emptyTitle'), t('matches.filterNone', { q: opts.q }), button(t('matches.filterClear'), opts.clear, 'primary')));
    return out;
  } else out.push(h('p', { class: 'muted', text: t('matches.counts', { good: c.actionable ?? 0, look: c['verify first'] ?? 0 }) }));
  if (!shown) {
    out.push(emptyState(t('matches.emptyTitle'), ctx.state.jobs.stored ? t('matches.emptyBody') : t('matches.emptyNoJobs'),
      button(t('matches.toJobs'), () => ctx.go('jobs'), 'primary')));
  }
  const heading = { actionable: () => t('matches.laneGood'), 'verify first': () => t('matches.laneLook'), excluded: () => t('matches.laneNo') };
  for (const lane of lanes) {
    if (!task[lane]?.length) continue;
    out.push(h('h2', { text: heading[lane]() }), ...task[lane].map((card) => cardView(card, lane, ctx)));
  }
  if (opts.title && data.results?.title) {
    out.push(h('h2', { text: t('matches.titleSearch') }), h('p', { class: 'hint', text: t('matches.titleHint') }));
    const t2 = data.results.title;
    const groups = Array.isArray(t2) ? [t2] : Object.values(t2).filter(Array.isArray);
    const cards = groups.flat();
    if (!cards.length) out.push(h('p', { class: 'muted', text: t('matches.titleNone') }));
    for (const card of cards) out.push(cardView(card, card.lane || 'verify first', ctx, true));
  }
  return out;
}

function place(card) {
  const list = (card.locations || []).map((l) => (typeof l === 'string' ? l : l?.city || l?.name || l?.label || '')).filter(Boolean);
  return list.join(', ');
}

function ageText(days) {
  if (days == null) return t('card.ageUnknown');
  if (days <= 0) return t('card.ageToday');
  return days === 1 ? t('card.ageOne') : t('card.ageMany', { n: days });
}

const RECHECKABLE = new Set(['greenhouse', 'ashby']);

function findingText(f) {
  const quote = f.excerpt ? `“${f.excerpt}”` : '';
  if (f.state === 'preferred') return quote ? t('card.niceToHave', { text: quote }) : '';
  return [quote, reasonText(textOf(f))].filter(Boolean).join(' — ');
}

function availability(card, redo) {
  const box = h('p', { class: 'small' });
  const ok = card.checked_at && /^(open|available|active|live|verified)/i.test(card.availability || '');
  if (!card.checked_at) box.append(h('span', { class: 'badge plain', text: t('card.notChecked') }));
  else if (ok) box.append(h('span', { class: 'badge', text: t('card.confirmedOpen', { date: fmtDate(card.checked_at) }) }));
  else box.append(h('span', { class: 'badge warn', text: t('card.checkedOn', { date: fmtDate(card.checked_at), state: statusText(card.availability) }) }));
  if (card.verification_reason) box.append(' ', h('span', { class: 'muted', text: reasonText(card.verification_reason) }));
  if (RECHECKABLE.has(card.source)) box.append(' ', button([icon('refresh'), t('card.recheck')], redo, 'quiet'));
  return box;
}

function languages(card) {
  const langs = card.language_summary?.languages || {};
  const rows = Object.entries(langs).filter(([, v]) => v.asked || v.state === 'conflict').map(([code, v]) => h('li', {},
    t('card.langLine', { lang: langName(code), asked: v.asked || t('card.notStated'), yours: v.yours || t('card.notStated') }), ' ',
    h('span', { class: `badge ${LANG_KIND[v.state] ?? 'plain'}`, text: (LANG_STATE[v.state] || (() => ''))() })));
  return rows.length ? h('ul', { class: 'facts' }, rows) : h('p', { class: 'small muted', text: t('card.noLang') });
}

function pairs(list, gap) {
  return list.map((p) => h('div', { class: `pair${gap ? ' gap' : ''}` },
    h('p', { class: 'small' }, h('b', { text: t('card.adSays') }), ' ', h('q', { text: p.ad }),
      p.kind === 'transferable' ? [' ', h('span', { class: 'badge plain', text: t('card.related') })] : null),
    p.cv ? h('p', { class: 'small' }, h('b', { text: t('card.cvSays') }), ' ', h('q', { text: p.cv })) : null));
}

function cardView(card, lane, ctx, titleOnly = false) {
  const root = h('article', { class: 'card' });
  const build = () => {
    const url = safeUrl(card.apply_url || card.url);
    const wording = card.wording || { supported: [], missing: [] };
    // Finding states from the matcher: conflict (hard stop), unknown or preferred (check first), met (nothing to do).
    const findings = (card.findings || []).filter((f) => f && f.state !== 'met').map((f) => ({ text: findingText(f), conflict: f.state === 'conflict' })).filter((f) => f.text);
    const conflicts = findings.filter((f) => f.conflict).map((f) => f.text);
    const toCheck = findings.filter((f) => !f.conflict).map((f) => f.text);
    if (card.language_summary?.conflict && !conflicts.length) conflicts.push(t('card.langConflict'));
    const place2 = place(card);
    const work = (WORKPLACE[card.workplace] || (() => ''))();
    const where = [place2, work].filter(Boolean).join(' · ');
    const children = [
      h('p', {}, h('span', { class: `badge ${FIT_KIND[lane] ?? 'warn'}`, text: (FIT[lane] || FIT['verify first'])() })),
      h('h3', { text: card.title }),
      ...(card.search_excerpt ? [h('blockquote', { text: card.search_excerpt })] : []),
      h('p', { class: 'muted', text: [card.company, where].filter(Boolean).join(' · ') }),
      h('ul', { class: 'facts' }, h('li', { text: card.salary || t('card.payNotStated') }),
        h('li', { text: card.deadline ? t('card.deadline', { date: fmtDate(card.deadline) }) : t('card.noDeadline') }), h('li', { text: ageText(card.age_days) })),
      availability(card, async (e) => {
        try {
          const r = await busy(e.currentTarget, () => api('POST', '/api/matches/recheck', { job_key: card.job_key }));
          Object.assign(card, { availability: r.availability, checked_at: r.checked_at, verification_reason: r.reason });
          say(t('card.rechecked')); redraw();
        } catch (err) { root.append(errorBox(err)); }
      }),
      h('h4', { class: 'label', text: t('card.languages') }), languages(card),
    ];
    if (wording.supported.length) {
      children.push(h('h4', { class: 'label', text: t('card.whyFits') }), ...pairs(wording.supported.slice(0, 3), false));
    } else if (!titleOnly) children.push(h('p', { class: 'small muted', text: t('card.noWhy') }));
    if (conflicts.length) children.push(h('div', { class: 'alert danger' }, icon('warn'), h('div', {}, h('b', { text: t('card.conflicts') }), h('ul', {}, conflicts.map((c) => h('li', { text: c }))))));
    if (toCheck.length) children.push(h('h4', { class: 'label', text: t('card.checkFirst') }), h('ul', {}, toCheck.map((c) => h('li', { text: c }))));
    if (wording.supported.length > 3 || wording.missing.length) {
      children.push(h('details', {}, h('summary', { text: t('card.wordingTitle') }),
        wording.supported.length > 3 ? pairs(wording.supported.slice(3), false) : null,
        wording.missing.length ? [h('p', { class: 'label', text: t('card.missingTitle') }), pairs(wording.missing, true)] : null));
    }
    children.push(actions(card, url, redraw, root, ctx));
    return children;
  };
  const redraw = () => root.replaceChildren(...build());
  redraw();
  return root;
}

function actions(card, url, redraw, root, ctx) {
  const note = h('div', {});
  const saved = card.application;
  const save = saved
    ? h('span', { class: 'badge' }, icon('check'), ' ', t('card.inApplications', { status: (STATUS[saved.status || saved] || (() => ''))() }))
    : button([icon('bookmark'), t('card.save')], async (e) => {
      try { await busy(e.currentTarget, () => api('POST', '/api/applications', { job_key: card.job_key, status: 'saved' })); card.application = 'saved'; say(t('card.savedMsg')); redraw(); } catch (err) { note.replaceChildren(errorBox(err)); }
    });
  const open = url ? h('a', { class: 'btn', href: url, target: '_blank', rel: 'noopener noreferrer' }, t('card.open'), icon('external')) : null;
  const send = async (verdict, reason) => {
    try {
      await api('POST', '/api/feedback', { job_key: card.job_key, verdict, ...(reason ? { reason } : {}) });
      note.replaceChildren(notice('info', t('feedback.thanks')));
    } catch (err) { note.replaceChildren(errorBox(err)); }
  };
  const why = () => {
    const id = `why-${card.job_key}`;
    const box = h('input', { type: 'text', id, placeholder: t('feedback.reasonPlaceholder') });
    note.replaceChildren(h('label', { for: id, text: t('feedback.reasonLabel') }), box,
      h('div', { class: 'row tight' }, button(t('feedback.send'), () => send('not_for_me', box.value.trim())), button(t('feedback.skip'), () => send('not_for_me'), 'quiet')));
    box.focus();
  };
  return h('div', {}, h('div', { class: 'row' }, open, save),
    h('div', { class: 'row tight', role: 'group', 'aria-label': t('feedback.group') },
      button(t('feedback.useful'), () => send('useful'), 'quiet'), button(t('feedback.notForMe'), why, 'quiet'), button(t('feedback.newToMe'), () => send('new_to_me'), 'quiet')), note);
}

export async function applicationsView(root, ctx) {
  root.append(h('h1', { text: t('apps.title') }), h('p', { class: 'lead', text: t('apps.intro') }));
  const [summary, list] = await Promise.all([api('GET', '/api/summary'), api('GET', '/api/applications')]);
  const stat = (n, label) => h('div', { class: 'stat' }, h('b', { text: String(n) }), label);
  root.append(h('h2', { text: t('apps.weekTitle') }), h('div', { class: 'grid' },
    stat(summary.applied_this_week, t('apps.appliedWeek')), stat(summary.follow_ups_due.length, t('apps.followUps')),
    stat(summary.interviews.length, t('apps.interviews')), stat(summary.new_matches, t('apps.newMatches'))));
  const named = (title, rows, datefield) => rows.length ? h('div', { class: 'card' }, h('h3', { text: title }), h('ul', { class: 'list' },
    rows.map((r) => h('li', { text: `${r.title} · ${r.company}${r[datefield] ? ` · ${fmtDate(r[datefield])}` : ''}` })))) : null;
  root.append(...[named(t('apps.followUps'), summary.follow_ups_due, 'follow_up_on'), named(t('apps.interviews'), summary.interviews, 'follow_up_on')].filter(Boolean));
  if (summary.new_matches > 0) root.append(h('p', {}, button(t('apps.seeNew'), () => ctx.go('matches'))));
  if (!list.items.length) {
    root.append(emptyState(t('apps.emptyTitle'), t('apps.emptyBody'), button(t('apps.toMatches'), () => ctx.go('matches'), 'primary')));
    return;
  }
  const errors = h('div', {});
  root.append(h('h2', { text: t('apps.listTitle') }), errors, ...list.items.map((row) => appRow(row, ctx, errors)),
    h('div', { class: 'row' }, button(t('apps.export'), async (e) => {
      try { await busy(e.currentTarget, () => download('/api/applications/export.csv', 'applications.csv')); } catch (err) { errors.replaceChildren(errorBox(err)); }
    })));
}

function appRow(row, ctx, errors) {
  const id = row.job_key.replace(/\W/g, '');
  const status = h('select', { id: `s-${id}` }, Object.keys(STATUS).map((k) => h('option', { value: k, selected: k === row.status }, STATUS[k]())));
  const applied = h('input', { type: 'date', id: `a-${id}`, value: row.applied_on || '' });
  const follow = h('input', { type: 'date', id: `f-${id}`, value: row.follow_up_on || '' });
  const notes = h('textarea', { id: `n-${id}`, value: row.notes || '' });
  const url = safeUrl(row.url);
  const fields = h('div', {});
  const save = button(t('apps.save'), async (e) => {
    fields.replaceChildren();
    const body = { job_key: row.job_key, status: status.value, notes: notes.value };
    if (applied.value && applied.value !== (row.applied_on || '')) body.applied_on = applied.value;
    else if (row.applied_on) body.applied_on = row.applied_on;
    if (follow.value !== (row.follow_up_on || '') && follow.value) body.follow_up_on = follow.value;
    try { await busy(e.currentTarget, () => api('POST', '/api/applications', body)); say(t('apps.saved')); ctx.rerender(); } catch (err) {
      for (const m of Object.values(err.fields || {})) fields.append(h('p', { class: 'field-error', role: 'alert', text: m }));
      if (!Object.keys(err.fields || {}).length) fields.append(errorBox(err));
    }
  });
  const remove = button(t('apps.remove'), async () => {
    if (!confirm(t('apps.removeConfirm'))) return;
    try { await api('DELETE', `/api/applications?job_key=${encodeURIComponent(row.job_key)}`); ctx.rerender(); } catch (err) { errors.replaceChildren(errorBox(err)); }
  }, 'danger quiet');
  return h('article', { class: 'card' }, h('h3', { text: row.title }), h('p', { class: 'muted', text: row.company }),
    row.follow_up_due ? h('p', {}, h('span', { class: 'badge warn', text: t('apps.followDue') })) : null,
    h('div', { class: 'field' }, h('label', { for: status.id, text: t('apps.status') }), status),
    h('div', { class: 'field' }, h('label', { for: applied.id, text: t('apps.appliedOn') }), applied),
    h('div', { class: 'field' }, h('label', { for: follow.id, text: t('apps.followUpOn') }), follow),
    h('div', { class: 'field' }, h('label', { for: notes.id, text: t('apps.notes') }), notes), fields,
    h('div', { class: 'row tight' }, save, url ? h('a', { class: 'btn quiet', href: url, target: '_blank', rel: 'noopener noreferrer' }, t('card.open'), icon('external')) : null, remove));
}

export async function dataView(root, ctx) {
  root.append(h('h1', { text: t('data.title') }), h('p', { class: 'lead', text: t('data.intro') }));
  const errors = h('div', {});
  root.append(h('div', { class: 'card' }, h('h2', { text: t('data.where') }), h('p', {}, h('code', { text: ctx.state.data_dir })), h('p', { class: 'hint', text: t('data.whereHint') })));
  root.append(h('div', { class: 'card' }, h('h2', { text: t('data.downloadTitle') }), h('p', { text: t('data.downloadBody') }),
    button(t('data.download'), async (e) => {
      try { await busy(e.currentTarget, () => download('/api/export', 'career-discovery-export.json')); } catch (err) { errors.replaceChildren(errorBox(err)); }
    }, 'primary')));
  const word = h('input', { type: 'text', id: 'confirm-word', autocomplete: 'off', autocapitalize: 'off' });
  const del = button(t('data.delete'), async (e) => {
    try {
      await busy(e.currentTarget, () => api('POST', '/api/data/delete', { confirm: 'DELETE' }));
      say(t('data.deleted'));
      ctx.go('cv');
      ctx.rerender();
    } catch (err) { errors.replaceChildren(errorBox(err)); }
  }, 'danger solid', { disabled: true });
  word.addEventListener('input', () => { del.disabled = word.value !== 'DELETE'; });
  root.append(h('div', { class: 'card' }, h('h2', { text: t('data.deleteTitle') }), h('p', { text: t('data.deleteBody') }),
    h('label', { for: 'confirm-word', text: t('data.typeToConfirm') }), word, h('div', { class: 'row tight' }, del)));
  root.append(h('div', { class: 'card' }, h('h2', { text: t('data.closeTitle') }), h('p', { text: t('data.closeBody') }),
    button(t('data.close'), async () => {
      try {
        await api('POST', '/api/shutdown', {});
        root.replaceChildren(h('h1', { text: t('data.closedTitle') }), h('p', { text: t('data.closedBody') }));
      } catch (err) { errors.replaceChildren(errorBox(err)); }
    })), errors);
}
