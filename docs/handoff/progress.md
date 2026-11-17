# Progress log

Newest entry first. Each entry: date, what is done, what is open, the exact next step.

## 2026-11-17 — coverage-gap lane started

Done
- Baseline reproduced: 63 offline tests pass and the demo runs. The code is in a local git repository, baseline tagged
  `baseline-2026-11-17`.
- Cause of the low yield reproduced on the cached public corpus: see
  [diagnostics/2026-11-17-coverage-gap.md](diagnostics/2026-11-17-coverage-gap.md) (findings F1 to F5).
- Added `scripts/gates.sh`, `docs/agent-rules.md`, `docs/task-definitions.md` and `AGENTS.md`.

Plan for this lane (status in brackets)
1. [in progress] Parsing correctness: F3, F4, F5 and the missed headings in F2. Files: `career_discovery/analysis.py`,
   `career_discovery/eligibility.py`, tests.
2. [in progress] Held-out fictional set `fixtures/heldout/vacancies.json`, written without reading the vocabulary.
3. [in progress] `coverage` and `heldout` diagnostics commands: `career_discovery/diagnostics.py`, CLI, tests.
4. [pending] Vocabulary recall (F1): English and German duty wording for the existing tasks, precision checked.
5. [pending] Bump `ANALYSER_VERSION` to 12 and the catalogue version to 4. Measure baseline against new on the same
   frozen pool and clock, plus the held-out set. Record the numbers in the diagnosis file.
6. [pending] Update the handoff, decisions and README.

Step 2 and 3 done. Held-out baseline (tag `baseline-2026-11-17`, technical-graduate, 24 ads): 34 of 118 duties
detected, task precision 0.857 (6 of 7), recall 0.054, 6 of 111 qualifications leak into duties, 9 of 17 mandatory
language conflicts detected. Keep the held-out file out of every tuning brief; score it only at step 5.

Step 1 done and committed (b0e4c77): 80 tests pass; zero-duty listings in the cached corpus fell from 333 to 253.
Step 4 in progress: vocabulary in `analysis.py`/`catalog.json`, tests in `tests/test_vocabulary.py`, report in
`diagnostics/lane4-vocabulary-report.md`, precision sample in `.state/vocab/sample.json` for a blind check. If this
step was interrupted, check `git status`; uncommitted vocabulary edits are the work in progress.

Next step (old note): finish step 1, run `scripts/gates.sh`, commit, then start step 4.
