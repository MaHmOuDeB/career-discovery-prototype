# Lane 4: vocabulary coverage
Scope: `career_discovery/analysis.py` only (ACTION_OBJECTS, TASK_PATTERNS, OTHER_ACTOR, TASK_EXCLUSION). No change to
`catalog.json`, `matching.py`, fit rules, `ANALYSER_VERSION` or the catalogue version. No new task names.
Tests first in `tests/test_vocabulary.py` (fictional lines: positives per task in EN and DE, negatives). Fast checks
`tests.test_vocabulary tests.test_parsing tests.test_matching`: 47 green, old assertions unchanged.
## Before and after (`.state/pilot`, clock 2026-11-16T22:52:55Z)
| Measure | Before | After |
| --- | --- | --- |
| Mapped duty lines, all 1,181 listings | 273 of 5,674 (4.8%) | 784 of 5,736 (13.7%) |
| Mapped duty lines, 161 analyst/ops/support/data titles | 63 of 799 (7.9%) | 167 of 810 (20.6%) |
| Unique tagged duty lines, English / German | 231 of 3,762 / 4 of 576 | 525 / 70 |
| Listings with zero duties | 253 | 224 |
| Fit: partial / stretch / transferable / strong | 21 / 12 / 2 / 1 | 49 / 43 / 5 / 1 |

393 unique lines changed tags; none lost one. Biggest task gains: report_kpis 18 to 145, troubleshoot 31 to 121,
stakeholders 4 to 103, systems_integration 1 to 64, automate 21 to 63, teach 3 to 40, configuration 0 to 24.
Outputs and blind sample (80 lines, seed 17, new tags only): `.state/vocab/` (untracked).
## Pattern families added
- ACTION_OBJECTS values are tuples of (actions, objects[, "either"]) pairs. "either" also accepts object-first order for
  German infinitives and separable verbs. `None` actions means the object compound alone is evidence.
- English verbs use explicit inflections, so "product", "developer", "automation" cannot act as verbs; actions cannot
  start inside a hyphenated word.
- EN and DE verb-family x object-family patterns for all 16 requested tasks, plus root-cause analysis, Fehleranalyse,
  Kennzahlen, Reporting, Datenqualität, Kontenabstimmung, Schulungsunterlagen, Automatisierung von Prozessen.
- OTHER_ACTOR gains German "damit, sodass, falls" and "Kunden können"; TASK_EXCLUSION gains "statt". Inquiry answering,
  bare "workshops"/"sessions" and "work with the team" are left out on purpose.
## Precision
My own read of the 80-line sample: about 85 to 90% clearly right, the rest arguable (for example "vendor documentation"
as document_process). Early drafts gave roughly 35% false tags; stems, adjacency and look-alike fixes removed most.
A blind review of `sample.json` is still needed.
## Known limits
- Fewer than 1 in 7 duty lines map; the rest is engineering, sales or management work outside the catalogue.
- Du-form prose without a bullet is not a duty under `ROLE_VERB`, which I did not touch, so German recall stays low.
- Tagged lines now pass the `tags and ROLE_VERB` test outside duty sections (zero-duty listings 253 to 224), so this
  also changes parsing yield. The controller should treat it as such when setting the versions.
- Residual noise: "resolve employee issues" maps to troubleshoot, "maintain accurate records" to data_quality,
  "documentation" in software ads to document_process, "integrations" in management lines to systems_integration.
- "Handbook" and "playbook" are not document_process: `test_semantic_only_links_to_existing_evidence` needs it unmapped.
- The 5-word window can still pair a distant verb and object. CV evidence uses the same patterns and guards.
