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
