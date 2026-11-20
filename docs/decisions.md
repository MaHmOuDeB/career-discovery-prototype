# Implementation decisions

## Reuse and exclusions

| Existing component | Decision |
| --- | --- |
| Company ATS scanner | Adapted the documented Greenhouse and Ashby endpoints and the idea of a curated allowlist. Rewrote normalisation, status tracking, robots handling, rate limits and the storage boundary. |
| Feed watcher | Adapted the idea of snapshots and change counts. The old watcher, schedules, settings and private watchlist are outside this project. |
| Personal prefilter | Reused the categories that needed checking, such as language, eligibility and seniority. Replaced title vetoes, personal thresholds and company-plus-title deduplication. |
| Intake workflow | Adapted the official-link availability check and the distinction between a repost and another requisition. Application folders, email and trackers remain outside the prototype. |
| Candidate fact base and CV craft | Adapted scoped evidence, known gaps and responsibilities-first matching. Wrote independent fictional profiles and a new schema. |
| Docproof and CV panel | Read as references for traceability and regression cases. The prototype has no Docproof dependency, CV-generation step or reviewer agents. |
| BA, StepStone, LinkedIn and Apify | Excluded from the initial source mix. The prototype works with local CSV and documented employer feeds. |

## Choices and limits

- Python standard library and SQLite keep the prototype runnable without a dependency install. Poppler is optional for direct PDF extraction. The installed Homebrew Python’s XML module failed to load on this Mac, so DOCX falls back to the existing macOS Python process for bounded, local XML parsing. No system configuration was changed.
- Profile JSON is reviewed by the candidate. Existing CV imports are cached by fingerprint and a changed document returns the profile to draft. Evidence state and the source locator remain separate. Evaluations with real CVs need candidate consent.
- Jobs use exact canonical URLs and source-scoped IDs. Similar titles can be flagged separately. Terms for redistribution and all custom employer-hosted verification remain outside this local pilot.
- Greenhouse and Ashby requests use the documented public endpoints. Ashby’s API host returned HTTP 401 for its robots file in this environment. The bounded exception is limited to its documented unauthenticated job-board path and follows the unavailable-resource treatment in [RFC 9309](https://www.rfc-editor.org/rfc/rfc9309.html#name-unavailable-status). Actual access failures remain visible, and no credentials are used.
- The task catalogue and ad parser are conservative starter heuristics with English and German coverage. Descriptions vary widely. A review flag can reflect a real limitation of the parser as well as incomplete employer or candidate information. The live audit led to added regression cases for job-ad sections, leadership context, incomplete responsibilities, alternative conditions and mandatory scope.
- The semantic option exchanges fictional data through files and requires review. Direct model integrations, ESCO, embeddings and a shared index remain deferred pending measured value and a viable source pool.
- CLI defaults are offline. Public refresh and verification use explicit commands. No APIs billed for inference or sourcing are configured.

## First recorded pilot on 16 November 2026

- Two official ATS formats were parsed across 12 responding boards. The snapshot contained 1,181 listed records before candidate screening.
- The final screen left one review-only listing for the fictional graduate scenario. It required substantive prior knowledge-systems and stakeholder enablement experience. It was unsuitable as a clear early-career recommendation. The Germany-wide location variant left the same entry. The initial exploratory screen had overcounted due to incomplete responsibility parsing and was superseded.
- Two separate sample application paths corroborated the verifier, one on Greenhouse and one on Ashby. These were network-path smoke tests and were outside the graduate shortlist.
- The fictional benchmark found 12 of 18 relevant job recommendations for task-based matching and 5 of 10 for the title baseline. The cap was five per profile and both methods sometimes returned fewer. One synthetic reviewed transfer proposal added evidence to a recommendation without changing these counts.
- The repeat supply snapshot and consenting-participant evaluation remain unmeasured.

## Targeted sourcing follow-up

Eight additional employer boards returned 117 listings. They were kept in a separate local corpus so the original board mix stays comparable for a repeat observation. The targeted corpus produced zero actionable matches for the fictional graduate. Allowing internships and temporary roles produced the same result. The role descriptions exposed missing section headings, combined mandatory and preferred language clauses, and internship types obscured by full-time schedule metadata. The corrected parser applies to cached ATS records. The original corpus still produces one review-only case and zero actionable results.

The follow-up added reason counts to the supply report, a comparability check for elapsed time and identical settings, and a blind reviewer deck with a separate method key. The last offline run passed 45 tests. The pilot deck was exercised with a fictional profile and live public job links.

## Private owner test

The approved master CV was parsed in the local private state. A mechanical check confirmed that every extracted item had an exact source paragraph after contact-pattern removal. Personal excerpts and draft preferences were retained only in that state. No profile confirmation was recorded.

The test surfaced sparse vocabulary coverage. The extraction verb list and task aliases were broadened, and the task ranking now holds insufficiently covered roles with two independently evidenced responsibilities in review only. The title baseline retains its original eligibility treatment. The real-CV comparison used the same 1,298 cached listings and the same verification clock for each method. The changes did not produce a task-based review candidate for this case. Synthetic precision counts stayed the same. The offline suite passed 48 tests.

The original employer snapshot was re-analysed with the updated catalogue at its original observation time so the later like-for-like check stays possible. This re-analysis is still the first observation.

## Two independent reviews on 17 November 2026

The first review led to changes in mixed requirements, scoped tenure, evidence attribution, repeated-task scoring, seniority review, availability status and pilot diagnostics. The second reproduced further eligibility, attribution and availability errors. Its fixes separate mandatory minimums from preferences, retain remaining explicit conditions, check the candidate's role in the stated task, preserve duration operators, and require an enabled application control from a recent, exact employer listing. Older automatic proof is downgraded when loaded. The final offline suite passed 63 tests.

The benchmark recheck corroborated five Greenhouse application controls. Nineteen Ashby application URLs responded but remained unverified, and two expired controls stayed closed. The first 12-board supply observation remains below the minimum. The local review and benchmark are complete. Human usefulness and live supply still require independent ratings and a repeat observation.

## Coverage-gap lane on 17 November 2026

The low supply yield was reproduced on the cached public pool: about 5% of duty lines mapped to any task, a third
of listings yielded no duties, and qualification lines under duty headings bypassed the eligibility checks, so two
German C2 requirements produced no conflict. The analyser now recognises more section headings (both sides of dash
headings), keeps qualifications out of duties, recognises duty wording in English and German, and gives every
mandatory language line a finding. `ANALYSER_VERSION` is 14; the catalogue is unchanged at version 3.

Unmapped duties still count against fit. Treating them as neutral would raise yield but would let roles whose main
duties are outside the catalogue look like strong fits, so it was not done. Qualifier-only language wording
("fließend", "native") still infers no CEFR level and stays unknown, as the earlier rule set out; an inferred level
would exclude listings on an assumption, and both outcomes keep a listing out of the actionable lane.

Evaluation uses a held-out set of 24 labelled fictional ads written without access to the vocabulary, plus a blind
precision review of newly tagged public lines. Results and limits are in
[the diagnosis](handoff/diagnostics/2026-11-17-coverage-gap.md). The supply baseline stays frozen at git tag
`baseline-2026-11-17`; `scripts/repeat-supply.sh` runs the repeat observation from that tag.

## Catalogue version 4 on 17 November 2026

The owner chose to add catalogue tasks for the dominant unmapped duty themes. `process_improvement`,
`quality_compliance` and `customer_communication` were added with five transfers whose reasons say what still needs
checking; `stakeholders` was reworded. `ANALYSER_VERSION` is 15. A second held-out set (`fixtures/heldout-v2/`) was
labelled against the new definitions before tuning. Mapped duty lines rose from 12.4% to 18.4%, but plausible
listings stayed at 2: the fictional profile's evidence, not the catalogue, now limits yield. Look-alike wording
(code review, contract renewals, data quality, title-case benefit subheadings) is vetoed per task rather than by
loosening the fit rule.

## Analyser version 16 and richer fictional profiles on 17 November 2026

`ANALYSER_VERSION` is 16: onboarding sessions or calls for new customers now count as `onboard`, with no held-out
regression. Richer fictional profiles (`fixtures/supply-profiles.json`, `scripts/profile-yield.py`) showed that five
times the evidence leaves plausible listings at 2. Location supply, out-of-profile titles, duty recognition on
relevant titles and the strict plausible rule limit yield, not profile evidence. The diagnosis has the table.

## Plausible-count rules stay strict (owner, 17 November 2026)

The owner chose to keep "English working language unconfirmed" and the senior-title signal in the plausible count:
"Keep them strict". Measured on the frozen pool and clock, dropping both raised plausible listings from 2 to 4 for the
scenario graduate and to 8 for the rich fictional profile, still below the gate of 10 listings from 3 employers. The
regained listings were German-written ads with no stated language level and "Senior" titles. `SUPPLY_POLICY_VERSION`
stays unchanged, so the 23 November repeat stays comparable. The rules affect only the supply count; the app still
shows such jobs for review.

## Expanded search with three extra boards stays (owner, 20 November 2026)

Codex added an optional "12 boards plus 3" search on Find jobs: Trading 212, bunch and Upvest on Ashby
(`career_discovery/trial-boards.json`), picked for Berlin operations roles. Codex marked them reviewed itself and queried
them once outside its brief; in that trial they added 121 listings and none passed the supply screen for the fictional
graduate. The owner kept the feature: "if you believe this new feature that Codex added is useful, then keep it". The
standard button and the supply observation still use only the 12 boards in `career_discovery/boards.json`, so the
23 November repeat stays comparable. The extra boards use the same request bounds and send nothing about the user.
