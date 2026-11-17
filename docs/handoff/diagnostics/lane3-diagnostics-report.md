# Lane 3: diagnostics report

Status: DONE. Offline, read-only, standard library only. Analyser and catalogue versions untouched.

## Files
- `career_discovery/diagnostics.py` (new): `coverage_report`, `heldout_report`.
- `career_discovery/__main__.py`: `coverage` and `heldout` subcommands (no store writes; coverage never creates
  `vacancies.sqlite` and reads it only if present; `store.analyse` cache is bypassed so nothing is written).
- `tests/test_diagnostics.py` (new, 7 tests).

## Usage
    python3 -B -m career_discovery --state .state/pilot coverage [--profile ID] [--at ISO8601] [--titles REGEX]
    python3 -B -m career_discovery heldout fixtures/heldout/vacancies.json [--profile ID] [--at ISO8601]
Default profile is the first demo scenario (`technical-graduate`), as in `supply`. `--profile` accepts a demo
profile ID or a stored local profile. Default clock is now; pass `--at 2026-11-16T22:52:00+00:00` to match the baseline.

## coverage output (aggregates only)
jobs, zero_duty_jobs, one_duty_jobs, duty_lines, mapped_duty_lines, mapped_rate, task_counts, fit_counts,
lane_counts, review_reason_counts, plausible, plausible_companies, language_conflicts. Closed jobs skipped;
`jobs` counts after `deduplicate`. Duty line = requirement of kind core.

## heldout output
vacancies, duties_total, duties_detected, qualifications_total, qualification_leaks,
tasks.overall and tasks.per_task (precision, recall, f1, true_positive, predicted, expected),
language_conflicts_expected / _detected / _unexpected, misses [{id, text, expected{kind,tasks}, got{kind,tasks}}].

## Method notes
- A labelled line matches every requirement whose normalised text contains it or is contained in it. Predicted tasks
  are the union over matches; a duty is detected if any match is core; a qualification leaks if any match is core.
- Task metrics use duty lines only, micro-averaged overall (a task set per line, counted per task).
- Expected language conflict: mandatory requirement with level above the profile level for that language; detected if
  the assessment has a conflict finding with subject `language (xx)`. `_unexpected` counts other language conflicts.
- Heldout jobs: source fictional, availability fixture_open, URL under vacancies.example.

## Tests
`PYTHONPATH=tests python3 -B -m unittest tests.test_diagnostics tests.test_cli -q` passes. Plain
`-m unittest tests.test_cli` fails to import `test_documents` without `PYTHONPATH=tests` (pre-existing).
Not run: full suite, `fixtures/heldout/` (not yet present).
