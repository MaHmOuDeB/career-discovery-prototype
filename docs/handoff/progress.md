# Progress log

Newest entry first. Each entry: date, what is done, what is open, the exact next step.

## 2026-11-20 — saved-job comparison, README screenshots, release 0.3.0

- My applications compares two or three saved jobs side by side (`GET /api/applications/compare?key=…&key=…`), one entry
  per ad duty. Built by a subagent from a brief, reviewed: repeated `key` parameters instead of comma-split JSON keys, the
  card's availability badge reused, a duty the CV backs not repeated as missing. 205 offline tests.
- README screenshots in `docs/images/`, taken with headless Chrome from a fictional state (rich fictional profile from
  `fixtures/supply-profiles.json`, the 24 demo vacancies). They show no real person or vacancy.
- Fixes found in the screenshots: "From your CV: Added by you" on items the user added; a gap above the first heading in a
  card.

## 2026-11-20 — owner keeps the expanded search; README feature list; release 0.2.0

- The owner kept Codex's expanded 15-board search (`docs/decisions.md`). Two tests now cover it: the expanded group
  reads exactly the three shipped extra boards, and an unknown group is 422 with no request.
- README: a "What the app does" section covering every page; API docs for `group`, `duties`, `search_excerpt` and
  `trial`. Version 0.2.0 with CHANGELOG.md. 200 offline tests.
- Next step unchanged: task A on or after 23 November; B2 when wanted.

## 2026-11-20 — review of the Codex commits before pushing

- Removed a hard-coded special case in the duty search: the query "Kundenprobleme lösen" was hand-mapped to
  `troubleshoot`. Phrases the analyser does not tag belong in vocabulary work (task B2, `ANALYSER_VERSION` 17).
- Note: the three trial boards (Trading 212, bunch, Upvest) were added and queried without an owner review of the
  boards; the brief allowed network use only for task A. They stay behind the optional expanded search.

## 2026-11-18 — local Chrome walkthrough

Used a disposable Chrome profile and temporary app state with a fictional candidate and 24 demo jobs. Reproduced a keyboard skip link changing the current page, misleading literal-match wording for translated searches, and a missing CSV option for retaining vacancy descriptions. Fixed all three and clarified the two employer-board choices in English and German. Re-tested Find jobs keyboard focus, description retention off by default, opt-in CSV import, German duty search finding the imported English listing, saving a match to Applications, and switching the interface to German. All four gates passed (198 tests).

## 2026-11-18 — expanded web search and bilingual duty filter

- Find jobs offers an optional 15-board search. The extra Ashby boards are Trading 212, bunch and Upvest, selected for Berlin operations roles. Complete refreshes with a confirmed profile report fresh additional employer vacancy URLs and plausible matches. Incomplete comparisons are indicated.
- Trial-only public feed check against a temporary copy of the original fictional pool: 67 + 28 + 26 = 121 additional vacancy URLs. Zero passed the existing plausible screen for the fictional scenario graduate. This used the earlier baseline snapshot and is separate from the 23 November observation.
- Matches searches title, company, location and recognised core duties, with English/German task recognition and a quoted duty. Search operates within the existing fit lanes. All four gates passed (198 tests).
- Proposed follow-up: compare shortlisted roles by confirmed CV evidence, unresolved mandatory requirements and closing date.

## 2026-11-18 — B1 complete at the v16 stop point

- Reproduced all four offline gates on `837167f` (194 tests). After B1 all four passed with 195 tests on Python 3.14.7. Web-app tests required local loopback access.
- Two fresh contexts independently authored 24 fictional ads (12 EN, 12 DE, 18 target roles and six controls) and 30 fictional CV lines using only the task definitions. Labels were fixed before scoring. The scorer uses the matcher's `evidence_tags`.
- v16 / catalogue 4, v3 vacancy tasks: precision **1.000**, recall **0.143** (8 correct, 8 predicted, 56 expected). Detected 16/72 duties, with 0/48 qualifications leaking into duties. Both expected language conflicts were detected, plus one unexpected conflict.
- v3 CV tasks: precision **0.818**, recall **0.225** (9 correct, 11 predicted, 40 expected). Reproduce with `python3 -B scripts/score-evidence.py fixtures/heldout-v3/evidence.json` and `python3 -B -m career_discovery heldout fixtures/heldout-v3/vacancies.json --at 2026-11-16T22:52:55+00:00`.
- Stopped before B2. The last recorded pool yield is 2 plausible out of 1,181. Task A is due on or after 23 November 2026. No repeat observation or v17 comparison has been run.

## 2026-11-18 — hand-over to Codex

- `docs/handoff/codex-handover.md` holds the open work as briefs: A (repeat supply check on or after 23 November),
  B (vocabulary lane, held-out v3 labels before tuning), C and D (owner and volunteers only).
- Starting commit `579d9ef`, 194 tests, `ANALYSER_VERSION` 16, catalogue 4. Next step: task B1.

## 2026-11-17 — owner feedback from trying the app

- Matches page: a "What you are looking for" bar (places, remote countries, kinds of work, languages) with a Change
  button. Saving details now returns to the matches when jobs are stored, since matches are redone on save.
- Matches page: a filter box for words in the job title, company or place. The API takes `q` and returns `shown`
  counts, so the filter covers every stored job, not just the first 50 (`docs/web-app/api.md`).
- Find jobs page: a primary "Continue to your matches" button at the bottom once jobs are stored, like the other steps.
- 194 offline tests. Browser check with fictional data: filter count, empty state and Clear, Change → save → matches,
  German, 375 px, no console errors.

## 2026-11-17 — analyser 16, plainer reasons, richer fictional profiles

- Plainer English reasons: language names instead of codes ("The profile lists German at B1"), and the
  `verified_requirements` jargon removed from the reason ("Check what the employer means by this line."). The German
  table follows.
- `ANALYSER_VERSION` 16: "onboarding sessions/calls … for new customers" now tags `onboard`. Held-out comparison in the
  diagnosis: v1 identical, v2 +1 correct tag, demo and pilot coverage unchanged.
- Richer fictional profiles (`fixtures/supply-profiles.json`, `scripts/profile-yield.py`): 15 evidence items instead of 3
  keeps plausible at 2. Evidence is not the main limit. See "Richer fictional profiles" in the diagnosis.

Open
1. Vocabulary lane: duty recognition on analyst, operations and support titles; CV-side wording for `stakeholders`,
   `customer_communication`, `process_improvement`. New held-out labels before tuning.
2. Decided by the owner: both plausible-count rules stay strict (see `docs/decisions.md`).
3. Repeat supply observation on or after 23 November (`scripts/repeat-supply.sh`, from the baseline tag).
4. Real starter runs on Windows and a fresh Mac; consented profiles and the human pilot.

## 2026-11-17 — German match reasons

- The German interface now shows the matcher's reason sentences in German. `career_discovery/web/i18n/reasons.de.json`
  maps each fixed English sentence (placeholders like `{code}`) to German; `reasonText()` in `web/js/util.js` swaps
  them sentence by sentence and leaves an unknown sentence in English. Matcher output is unchanged.
- `tests/test_reasons.py` reads every reason the code writes (AST scan of eligibility, matching, sources, network,
  models) and fails when a sentence has no German entry. A new reason sentence needs a line in that file.
- 193 offline tests. Browser check with fictional data in German and English: correct text, no console errors.

## 2026-11-17 — local web app v1 done

Owner chose a local web app (spec and owner picks: `docs/web-app/spec.md`). Done and pushed:
- Backend `career_discovery/webapp.py` + `webapi.py` (API contract `docs/web-app/api.md`), tracker table, `salary.py`.
- Interface `career_discovery/web/` (guided steps, matches, tracker, data page; English and German).
- Starters `Start Career Discovery.command` / `.bat` / `start.sh` (Python 3.12+ or uv); README "Use the app" section.
- Independent security review (`docs/web-app/security-review.md`): 1 HIGH, 1 MEDIUM, 4 LOW, all fixed with tests
  (one-time launch link + HttpOnly SameSite=Strict session cookie, CSV formula guard, timeouts, temp cleanup,
  delete-all scope, folder permissions, recheck lock).
- Controller browser walkthrough with fictional data found and fixed 5 UI defects (CV review skipped after upload,
  hard conflicts never shown as conflicts, Recheck on unsupported sources, findings without context, stray "null").
- 188 offline tests; CI runs tests, demo, help and an app smoke start on Ubuntu, macOS and Windows.

Open
1. A real run of the starters on a Windows laptop and a fresh Mac (Gatekeeper/SmartScreen prompts, uv install path).
2. Analyser gap seen in the walkthrough: "Ran onboarding sessions for new customers" tags `teach`, not `onboard`.
   Fixing it changes parsing: needs `ANALYSER_VERSION` 16 and a held-out comparison.
3. Done in the entry above: German match reasons.
4. Items 1–3 of the catalogue-lane entry below (repeat supply on or after 23 November, owner decision on profiles, pilot).

## 2026-11-17 — Windows support and CI

- GitHub Actions (`.github/workflows/tests.yml`) runs the tests, demo and help on Ubuntu, macOS and Windows with
  Python 3.14 on every push. Windows found one real bug: no system time-zone database, so `Europe/Berlin` failed in
  `matching.py`. `berlin_date` now falls back to the EU summer-time rule; `tests/test_timezone.py` checks it against
  the database where it exists and with fixed switch dates everywhere. Other fixes: cross-platform bounded PDF extraction, UTF-8 for all text I/O, private JSON replaced after
  the temp file closes. Report: `diagnostics/windows-portability-report.md`. 129 tests.
- On Windows, files are not owner-only (README says so); PDF import needs Poppler on PATH.

## 2026-11-17 — published as a public GitHub repo (owner's decision)

- Public at https://github.com/MaHmOuDeB/career-discovery-prototype, branch `master` and tag `baseline-2026-11-17`.
- Before the first push the author email was rewritten to the GitHub noreply address, so every commit hash changed.
  Old to new: b3520ec→d42206b (baseline tag), a55047a→a1f6f2e, b0e4c77→f7185a1, 8aa8a20→5e8e210, ff13b96→9e23968,
  1daba14→b31bf4f (v14), 8dde75e→fe95b2b (v15). A local backup bundle of the old history is in `.state/backup/`.
- MIT licence added. A pre-publication scan found no CV content, contact data, secrets or copied ad text in tracked files.
- Agents still do not push; the owner pushes or authorises each push.

Next step: unchanged (repeat supply on or after 23 November; owner decision on richer profiles).

## 2026-11-17 — catalogue lane complete (owner chose "add catalogue tasks")

Done
- Catalogue version 4: `process_improvement`, `quality_compliance`, `customer_communication`, five transfers,
  `stakeholders` reworded (`docs/task-definitions.md`). `ANALYSER_VERSION` 15. Report: `diagnostics/lane6-catalogue-report.md`.
- Second held-out set `fixtures/heldout-v2/` (24 ads, 157 duties), scored once on v14 before tuning.
- Language fixes found on v2: "native or C2" / "B2 or C1" stay one path, "jeweils/each at least B2" shares the level,
  markdown-bold headings are headings, bulleted CEFR language lines before any heading are mandatory.
- Per-task vetoes for look-alikes (code review, contract renewals, data quality, title-case benefit subheadings).
- Results in the diagnosis ("Results after the catalogue lane"): mapped duties 12.4% → 18.4%, v2 precision/recall
  0.931/0.129 → 0.938/0.215, v2 language conflicts 17 of 17. v1 precision on its own tasks unchanged at 0.897.
- 117 offline tests pass; demo output identical to the baseline.

Finding: plausible stays at 2. 168 of 176 listings without a hard conflict lack task evidence for the fictional
profile; the catalogue no longer limits yield. No listing became newly plausible, so no plausibility review was needed.

Open
1. Repeat supply observation on or after 23 November 2026: `scripts/repeat-supply.sh`. Record its summary here.
2. Owner decision: evaluate with richer fictional or consented profiles (the only remaining lever on yield).
3. Human pilot steps in the handoff need the owner and volunteers.

Next step: item 1 on or after 23 November; item 2 waits for the owner.

## 2026-11-17 — coverage-gap lane complete

Done (commits on the checked-out branch, after tag `baseline-2026-11-17`)
- Cause of the low yield reproduced and fixed in the analyser; `ANALYSER_VERSION` 14, catalogue unchanged at 3.
  Numbers, method and limits: [diagnostics/2026-11-17-coverage-gap.md](diagnostics/2026-11-17-coverage-gap.md).
  Per-lane agent reports sit next to it (`lane1` parsing, `lane3` diagnostics, `lane4` vocabulary, `lane5` languages,
  `lane-review` independent review).
- New: `coverage` and `heldout` CLI commands, `fixtures/heldout/` (24 independent labelled fictional ads),
  `scripts/gates.sh`, `scripts/repeat-supply.sh`, `AGENTS.md`, `docs/agent-rules.md`, `docs/task-definitions.md`.
- 110 offline tests pass; the demo output is identical to the baseline.

Independent review: 8 reproduced findings in `diagnostics/lane-review.md`, all fixed with tests (`ANALYSER_VERSION` 14).

Open
1. Repeat supply observation on or after 23 November 2026: run `scripts/repeat-supply.sh` (bounded public GETs to
   the 12 reviewed boards). It refuses to run earlier. Record its printed summary here and in the handoff.
2. Owner decision on yield (see "Why yield is still low" in the diagnosis): add catalogue tasks for unmapped duty
   themes such as process improvement and customer communication, or evaluate with richer fictional or consented
   profiles. Either change needs a catalogue version bump and a fresh held-out set or blind precision review.
3. Human pilot steps in the handoff are unchanged and need the owner and volunteers.

Rules that keep later results comparable
- Never tune on `fixtures/heldout/`. If it is used for development, write a new held-out set before claiming results.
- Compare analyser versions on the same frozen pool and clock: `coverage --at 2026-11-16T22:52:55+00:00` on
  `.state/pilot`, against a worktree of the baseline tag.

Next step: item 1 on or after 23 November; item 2 waits for the owner.
