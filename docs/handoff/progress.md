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

Next step: finish steps 1 to 3, run `scripts/gates.sh`, commit, then start step 4.
