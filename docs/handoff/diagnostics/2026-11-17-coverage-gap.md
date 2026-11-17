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

## Why yield is still low

The parser now sees about twice as many duties, but the fictional graduate has three evidence items, and nearby
roles list five to eight duties, mostly coordination, process improvement and customer communication. About 80% of
duty lines in those titles still map to no catalogue task. Unmapped duties count against fit by design. The next
gains need a decision, not a parser fix: either add catalogue tasks for the dominant unmapped duty themes
(stakeholder coordination is covered, process improvement and customer communication are not), or evaluate with
richer fictional or consented profiles. Both change what is being measured and need the owner's call.
