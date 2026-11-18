# Progress log

Newest entry first. Each entry: date, what is done, what is open, the exact next step.

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
