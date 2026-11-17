# Lane 6: catalogue version 4 (process_improvement, quality_compliance, customer_communication)

Touched: `catalog.json` (v4), `ACTION_OBJECTS` and two guards in `analysis.py`, `tests/test_vocabulary.py`. Not touched: matching.py, eligibility.py, ANALYSER_VERSION, existing tasks' patterns except stakeholders. Raw outputs: `.state/vocab2/`.
## Changes
- Catalogue: three tasks with 9 to 11 aliases each, the five transfers (exact text), the four family additions.
- Patterns: EN and DE verb and noun forms per task. Stakeholders gained two pairs (collaborate/coordinate/liaise/align/partner/
  work closely with ... teams, partners, departments; DE Zusammenarbeit/Abstimmung/Koordination/arbeiten eng mit ... Teams,
  Fachbereichen, Schnittstellen, Partnern). Singular "the team" is no object: "Work with the team", "Zusammenarbeit im Team" stay untagged.
- Guards: OTHER_ACTOR blocks "workplace/office/company/product/service that|which" and "customers|users|patients|guests can|will".
  POST_EXCLUSION accepts "not part of".
- Precision: "data quality ..." stays out of quality_compliance; "audit reports" is no audit; "customer/user" before data, records,
  accounts, permissions, table is not communication; help/serve are not communication verbs.
- Tests: 41 new positives (EN and DE), 34 negatives (look-alikes, other actors, benefit blurbs, "not part of"), a catalogue
  structure test and an evidence test (asserted work maps; intent-only, colleague-subject, seminar do not).
## Coverage, frozen pilot pool (`--at 2026-11-16T22:52:55+00:00`)
| | all, before | all, after | titles, before | titles, after |
| --- | --- | --- | --- | --- |
| jobs | 1181 | 1181 | 161 | 161 |
| duty lines (mapped) | 6447 (802) | 6494 (1217) | 886 (174) | 896 (242) |
| mapped rate | 0.124 | 0.187 | 0.196 | 0.270 |
| stakeholders / process_improvement | 141 / 0 | 244 / 189 | 31 / 0 | 50 / 54 |
| quality_compliance / customer_communication | 0 / 0 | 105 / 84 | 0 / 0 | 10 / 6 |
| partial / stretch / transferable | 63 / 37 / 3 | 94 / 52 / 18 | 17 / 7 / 1 | 33 / 7 / 4 |
| insufficient evidence; plausible | 1077; 2 | 1016; 2 | 136; 0 | 117; 0 |
No tag lost on 4866 unique duty lines; 301 gained a tag (259 had none). Extra duty lines (+47) come from lines that now split.
## Precision read (own scan of about 100 gained lines, not a labelled review)
- stakeholders and customer_communication: mostly sound; "talk with users" in product-discovery lines tags (arguably true).
- process_improvement: noise from qualification-shaped lines under duty headings ("a drive to improve processes").
- quality_compliance: sound for audits, food safety, GDPR; a bare "Qualitätssicherung" in a list and "quality controls" tag it.
- Blind-review sample: `.state/vocab2/sample.json` (80 lines, seed 23, gained tasks only).
## Concerns
Qualification leakage is existing section logic. The controller still sets ANALYSER_VERSION. Fast checks: 73 tests pass.
