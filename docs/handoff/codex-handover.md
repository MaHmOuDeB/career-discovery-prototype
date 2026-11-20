# Hand-over to Codex

18 November 2026 · Europe/Berlin · starting commit `579d9ef` on `master`

## Paste into Codex

> Read AGENTS.md, then docs/handoff/codex-handover.md. Reproduce the baseline with `scripts/gates.sh`. Do task A only
> on or after 23 November 2026. Do task B in the order its steps give, and stop at the stop points it names. Commit
> each finished step locally on `master` with a clear message; do not push. Report in docs/handoff/progress.md.

## Where the project stands

- **Code:** the CLI and the local web app (`python3 -m career_discovery app`, the double-click starters) are finished.
  English and German UI, German match reasons, looking-for bar, match filter and a Continue button on every step.
- **Tests:** 194 offline tests at the start; 200 after B1, the expanded search and the 20 November review.
- **Progress (20 November):** B1 is done (held-out v3 and the v16 baselines are in progress.md). B2 has not started.
  The owner kept the expanded 15-board search (`docs/decisions.md`). Task A is still due on or after 23 November.
- **Versions:** `ANALYSER_VERSION` 16, catalogue version 4. `SUPPLY_POLICY_VERSION` is unchanged.
- **Yield:** 2 plausible listings in the 1,181-listing fictional pool, against a target of 10 from 3 companies. Read
  "Why yield is still low" and "Richer fictional profiles" in
  [the diagnosis](diagnostics/2026-11-17-coverage-gap.md) before task B.
- **Owner decisions already made:** the English-working-language and senior-title rules stay strict
  (`docs/decisions.md`). Do not loosen them or propose loosening them again without new evidence.

## Rules that matter most here

All of CLAUDE.md, AGENTS.md and docs/agent-rules.md apply. The ones most likely to be broken:

- **No push, publish, deploy or contact.** Only the owner or Claude Code pushes to GitHub.
- **Off limits:** `.state/owner-pilot`, candidate exports, the private scoring key, and the owner's app data folder
  (`~/Library/Application Support/Career Discovery`). Use fictional profiles and temporary state.
- **`.state/pilot` is read-only:** read it locally for aggregate diagnostics only, on a temporary copy. Never copy
  vacancy text from it into tracked files.
- **No tuning on held-out sets:** never read `fixtures/heldout/` or `fixtures/heldout-v2/` while changing vocabulary.
  Run them only to score a finished change.
- **Versioning:** a parsing change needs a new `ANALYSER_VERSION`; a catalogue change needs a new catalogue `version`.
- **Comparisons:** compare old and new versions on the same pool and frozen clock, `2026-11-16T22:52:55+00:00`.
- **No paid spend:** standard library only, no new dependencies, network off by default.

## Task A: repeat supply observation (on or after 23 November 2026)

This is the only task that uses the network: bounded public GETs to the 12 reviewed boards.

1. Run `scripts/repeat-supply.sh`. It refuses to run before 23 November, builds a worktree of tag
   `baseline-2026-11-17` in `.state/baseline-worktree` and measures with the frozen method. It then runs the current
   method as a separate read-only `coverage` diagnostic. Do not pass `--force`.
2. If a board fails, record which one and why. Do not swap in other boards or retry outside the script's bounds.
3. Copy the printed summary into a new progress.md entry and the "Open work" section of docs/handoff/README.md:
   - corpus size, plausible and actionable counts;
   - `gate_met_this_snapshot`, `comparison_ready`;
   - new and repeat listings since the first observation, and `both_snapshots_meet_gate`.
   Aggregate numbers only; the full outputs stay in `.state/repeat-supply/`.
4. Do not change any code in this task. If the baseline worktree fails to run, stop and report.

Done when: progress.md and the handoff README hold the dated result, and the commit touches only those docs.

## Task B: vocabulary lane (can start now)

Goal: better duty recognition on analyst, operations and support ads, plus CV-side wording for `stakeholders`,
`customer_communication` and `process_improvement`. About 49 relevant listings list five or more duties but have at
most one recognised. This is the remaining lever on yield.

### B1. New held-out labels first (before any tuning)

- Write `fixtures/heldout-v3/` in a fresh context that has never read `career_discovery/catalog.json`,
  `career_discovery/analysis.py` or the earlier held-out sets. It may read `docs/task-definitions.md` only.
- Follow the format and README style of `fixtures/heldout-v2/`. Write 24 fictional ads in English and German:
  at least 16 analyst, operations or support titles and some unrelated controls. Label every duty and
  qualification line.
- Also write `fixtures/heldout-v3/evidence.json`: about 30 fictional past-tense CV lines, each labelled with its
  expected tasks (including negatives). Cover the three CV-side tasks above.
- Add a small scorer for the CV lines (a `heldout` option or a script next to `profile-yield.py`) that uses the same
  tagging the matcher uses (`evidence_tags` in `matching.py`). Add a unit test for the scorer.
- Score v16 on v3 and record the numbers before changing any vocabulary. Commit.

**Stop point:** B1 is done once the v16 baseline numbers for v3 are committed.

### B2. Tune

- Develop only on the fictional pool and your own made-up example lines:
  - the pool: aggregate `coverage` output on a temporary copy of `.state/pilot`;
  - the example lines: written as new unit tests in `tests/test_vocabulary.py`, with positives and negatives.
- Do not open the held-out sets while tuning.
- Change patterns in `analysis.py` and `catalog.json`. Raise `ANALYSER_VERSION` to 17, and the catalogue version too
  if `catalog.json` changes.

### B3. Compare and decide

Run v16 (a worktree at `579d9ef`) and v17 on the same clock:

- `python3 -B -m career_discovery demo` (it should be identical, or every difference explained);
- `heldout` on `fixtures/heldout`, `fixtures/heldout-v2` and `fixtures/heldout-v3`;
- the CV-line scorer on `fixtures/heldout-v3/evidence.json`;
- `coverage --at 2026-11-16T22:52:55+00:00` on a copy of `.state/pilot`;
- `python3 -B scripts/profile-yield.py`.

Keep v17 only if task precision does not fall on any held-out set and recall rises on v3. Otherwise revert the
vocabulary, keep the tests that document the misses, and report why.

### B4. Write it up

- Add a dated `ANALYSER_VERSION` 17 section to the diagnosis, with a before/after table like the v15 one.
- Add one entry to `docs/decisions.md`.
- Add one entry to progress.md.
- Update the test count and `ANALYSER_VERSION` in CLAUDE.md and docs/handoff/README.md.
- If a new reason sentence appears in the code, add its German line to
  `career_discovery/web/i18n/reasons.de.json` (`tests/test_reasons.py` enforces this).

Done when: gates pass, the numbers are in the diagnosis, and the commit history shows B1 before any tuning commit.

## Not for Codex (owner or volunteers)

- **C. Real starter runs:** double-click `Start Career Discovery.bat` on a Windows PC and
  `Start Career Discovery.command` on a fresh Mac. Codex may run `scripts/starter-check.sh` (offline lint) but
  cannot replace a real run.
- **D. Human pilot:**
  - the owner confirms the profile and completes the 26 blind judgements in `docs/handoff/validation/`;
  - then three to five consenting volunteers do paired sessions, following `docs/pilot.md`.
  Recruiting or contacting anyone needs separate owner authorization.

## Reporting back

At the end, give the owner five lines:
- status of A and B;
- the commits;
- the headline numbers: plausible count, and held-out precision and recall for v16 against v17;
- any concerns.

The owner or Claude Code reviews the commits and pushes them.
