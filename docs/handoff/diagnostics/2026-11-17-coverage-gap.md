# Coverage gap diagnosis

17 November 2026. Baseline: git tag `baseline-2026-11-17`, `ANALYSER_VERSION` 11, catalogue version 3.
Corpus: the 1,181 cached public listings in `.state/pilot` behind the first supply observation, assessed for the
fictional `technical-graduate` profile at the observation clock (2026-11-16 22:52 UTC).

## Findings

| # | Finding | Measure on the baseline | Kind |
| --- | --- | --- | --- |
| F1 | Duty lines rarely map to a catalogue task. | 297 of 6,482 parsed duty lines (4.6%) carry any task. Among 84 analyst, operations and support titles: 42 of 379 (11%). German duty lines almost never map. | Yield |
| F2 | Listings with no recognised duties. | 333 of 1,181 listings yield zero duties, 52 yield one. Missed headings include "You will", "Deine Rolle", "Dein Verantwortungsbereich", "Who you are", "You have", "Your experience", "You'll get". | Yield |
| F3 | `heading_kind` reads only the text before " — ", " – " or " - ". | "YOUR SKILLSET — WHAT YOU BRING TO THE TABLE" is not recognised, so the requirements that follow stay in the duties section. | Correctness |
| F4 | Qualification lines under a duties section become core duties, and `eligibility()` skips core lines except for sponsorship and work authorisation. | Two public German-care ads state "German proficiency at C2 ... hard requirement" and "Fluent in German (C2)". Both were filed as duties, so the B1 German profile showed no language conflict. | Correctness |
| F5 | `MANDATORY` misses common wording such as "hard requirement", "is a must", "essential". | Seen in the same ads. | Correctness |

Of the 188 listings left after location, seniority, employment, enrolment and German-language conflicts, 184 were
"insufficient evidence". Typical unmapped duties that match the profile's evidence: resolving escalated support
cases and root-cause analyses (troubleshoot), runbooks and knowledge-base articles (document_process), monitoring
processes and KPIs in German (report_kpis), maintaining customer data quality in German (data_quality), facilitating
training sessions with words between verb and object (teach).

The conservative fit rule stays. An unmapped duty is not evidence, so it still counts against fit. Better recall must
come from recognising more real duty wording, with precision checked, not from treating unknown duties as met.

## Held-out evaluation set

`fixtures/heldout/vacancies.json` is written independently of the vocabulary changes. Fixture authors do not read
`career_discovery/analysis.py`, `career_discovery/catalog.json` or `.state/`. Format: a JSON list of objects

    {"id": "h01", "language": "en" | "de", "company": "...", "title": "...", "locations": ["Berlin"],
     "employment": "full_time", "description": "<multi-line ad text>",
     "duties": [{"text": "<exact substring of one duty line>", "tasks": ["troubleshoot"]}],
     "qualifications": [{"text": "<exact substring of one qualification line>", "kind": "mandatory" | "preferred" | "unclear"}],
     "language_requirements": [{"language": "de" | "en", "level": "C1", "mandatory": true}]}

`tasks` uses the names in `docs/task-definitions.md` and may be empty. Every duty and qualification line in the ad
is labelled. Benefits, company and boilerplate lines are not labelled.

## Comparability

The repeat supply observation around 23 November must use the baseline method. Run it from a worktree of
`baseline-2026-11-17`, then run the new method on the same state as a separate diagnostic.

## Results after the fixes (17 November 2026, `ANALYSER_VERSION` 14, catalogue 3)

Same frozen pool (1,181 cached listings), same clock, same fictional profile. Baseline = tag `baseline-2026-11-17`.

| Measure | Baseline | Now |
| --- | --- | --- |
| Duty lines mapped to a task, whole pool | 297 of 6,482 (4.6%) | 802 of 6,447 (12.4%) |
| Same, 161 analyst, operations, support and training titles | 69 of 927 (7.4%) | 174 of 886 (19.6%) |
| Listings with no recognised duty | 333 | 193 |
| "needs review — responsibility coverage" | 392 | 244 |
| Listings with a mandatory language conflict | 59 | 78 |
| Plausible in the supply screen | 1 | 2 (gate needs 10 across 3 employers) |
| Held-out duties recognised (118 labelled) | 34 | 65 |
| Held-out task precision / recall | 0.857 / 0.054 | 0.897 / 0.232 |
| Held-out qualifications filed as duties (111) | 6 | 5 |
| Held-out mandatory language gaps flagged (17) | 9 conflicts | 12 conflicts + 5 unknown, none without a finding |

The held-out task and duty scores were measured once, before any change was made from them, and stay an
independent check. The language rows are development numbers: the language fixes (lane 5) were driven by misses
seen in the held-out file, then tested with separate wording in `tests/test_languages.py`.
A blind review of 80 newly tagged public duty lines found 0.876 precision before the loose patterns were tightened.
An independent review then reproduced eight defects in the new code (evidence overclaims, false language conflicts from duty lines, and others; see `lane-review.md`). All were fixed with tests; the stricter guards cost one held-out true positive. The demo output is identical to the baseline.

Four listings lost a baseline "strong fit". In each, the baseline had parsed only two duties; the remaining duties
are now recognised and unmatched, so the lower fit is the honest one.

## Results after the catalogue lane (17 November 2026, `ANALYSER_VERSION` 15, catalogue 4)

The owner chose to add catalogue tasks. New: `process_improvement`, `quality_compliance`, `customer_communication`,
with five transfers; `stakeholders` reworded and given wider wording. Definitions: `docs/task-definitions.md`.
Same pool, clock and profile. "v14" is commit 1daba14.

| Measure | v14 | v15 |
| --- | --- | --- |
| Duty lines mapped to a task, whole pool | 12.4% | 18.4% |
| Same, 161 analyst, operations, support and training titles | 19.6% | 26.7% |
| Listings with no recognised duty | 193 | 180 |
| Listings with a mandatory language conflict | 78 | 86 |
| Plausible in the supply screen | 2 | 2 |
| Held-out v1 task precision / recall, all tasks | 0.897 / 0.232 | 0.788 / 0.232 |
| Held-out v1 precision, catalogue-3 tasks only | 0.897 (26/29) | 0.897 (26/29) |
| Held-out v2 duties recognised (157) | 93 | 99 |
| Held-out v2 task precision / recall | 0.931 / 0.129 | 0.938 / 0.215 |
| Held-out v2 mandatory language conflicts (17) | 14 | 17 |
| Held-out v2 open (qualifier-only) requirements flagged (5) | 5 | 5 |

`fixtures/heldout-v2/` (24 ads) was written against the version 4 definitions without access to the vocabulary and
scored once on v14 before any change. Its task rows are an independent check. Its language rows are development
numbers: four language fixes were driven by its misses ("native or C2", "jeweils mindestens B2", markdown-bold
headings, bulleted language lines before any heading), then tested with separate wording.
The v1 drop is a labelling artefact: v1 was labelled before the new tasks existed, so new-task tags on v1 duties
score as false positives. Restricted to the tasks v1 knew, precision is unchanged. A blind review of new-task tags on
public lines found 0.89 precision before the look-alike guards were added. The demo output is identical to the baseline.

## Why yield is still low

After both lanes the bottleneck is evidence, not vocabulary. Of 176 listings with no hard conflict, 168 are held back
by "insufficient task evidence": their duties are now recognised, but the fictional graduate's three evidence items
cover few of them. Only eight reach a stretch or transferable fit; two are plausible, the other six wait on
responsibility coverage or an unconfirmed English working language. More catalogue tasks would not change this.
The next measurement needs richer fictional or consented profiles, which is an owner decision.
