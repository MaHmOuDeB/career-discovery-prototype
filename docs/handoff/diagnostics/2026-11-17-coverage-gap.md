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
Same pool, clock and profile. "v14" is commit b31bf4f.

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

## Richer fictional profiles (17 November 2026, `ANALYSER_VERSION` 16, catalogue 4)

The owner asked for everything that could be done the same day, so the evidence explanation above was tested with
fictional profiles only (consented profiles stay an owner and volunteer step). `fixtures/supply-profiles.json` holds
`technical-graduate-rich`: the scenario graduate's settings, languages and places with 15 CV-stated items
instead of 3 (a working-student support job, two internships, the capstone). `technical-graduate-rich-de-b2` is the
same with German B2. Run `python3 -B scripts/profile-yield.py`: it uses a temporary copy of `.state/pilot`, the
frozen clock `2026-11-16T22:52:55+00:00` and prints aggregate counts only.

| Measure (1181 listings) | scenario, 3 items | rich, 15 items | rich, German B2 |
| --- | --- | --- | --- |
| Tasks with evidence | 7 | 13 | 13 |
| Plausible in the supply screen | 2 | 2 | 2 |
| No conflict finding | 290 | 290 | 290 |
| … of which insufficient evidence | 259 | 251 | 251 |
| … transferable / stretch / strong fit | 3 / 8 / 0 | 10 / 8 / 0 | 10 / 8 / 0 |
| Mandatory German conflicts | 86 | 86 | 81 |

Five times the evidence does not raise yield, so evidence is not the main limit. ("No conflict finding" counts listings
without any conflict finding; the 176 above used the earlier screen's definition.) What holds the pool back:
- Location: 775 listings are outside Berlin or remote-Germany. That is supply, not a defect.
- Fit to this kind of graduate: of the 251 clear but insufficient listings, about 200 are sales, marketing,
  engineering, finance, design or other titles. Their duties are rightly outside a support and operations profile.
- Duty recognition on relevant titles: about 49 are analyst, operations or support titles. Most list five or more
  duties but have at most one recognised. This is the remaining lever.
- The plausible rule itself: even the 18 better fits are held back by "English working language unconfirmed"
  (284 listings), a senior title signal (362) or open responsibility coverage.
- Evidence-side wording: three rich-profile lines tag nothing, or only `document_process`, although they describe
  `stakeholders`, `customer_communication` and `process_improvement` work in past-tense CV wording ("Coordinated with
  product, sales and finance colleagues…", "Wrote customer emails…", "Mapped the returns workflow… proposed changes").
  These were not tuned here, so the profile does not become its own test.

Next step: a vocabulary lane for duty recognition on analyst, operations and support titles, plus CV-side wording
for the three newer tasks. Use held-out labels written before any tuning, then re-run `scripts/profile-yield.py`.
Whether the English-working-language and senior-title rules should stay strict for the plausible count is an owner
decision on the supply policy (a policy change needs a new `SUPPLY_POLICY_VERSION` and a comparability check).

## `ANALYSER_VERSION` 16 (17 November 2026)

The onboard pattern now accepts "onboarding sessions, calls, meetings, workshops or webinars for or with" new
customers, clients or users. It closes the gap seen in the web-app walkthrough, where "Ran onboarding sessions for new
customers" tagged only `teach`. Employee onboarding ("for new hires") and attending a session stay untagged.
Comparison with v15 on the same clock: demo output identical; held-out v1 identical; pilot pool coverage identical
(the pool has no such line); held-out v2 one more correct `onboard` tag, task precision / recall 0.938 / 0.215 to
0.939 / 0.220, onboard recall 0 / 5 to 1 / 5, no new false positive.
