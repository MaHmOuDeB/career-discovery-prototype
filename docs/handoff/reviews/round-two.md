# Independent second review — 17 November 2026

The local CLI implements the approved prototype workflow, but it should remain an evaluation tool with human review. Four remaining P1 classes can label unsupported eligibility, evidence or availability as ready. A tenure-expansion edge case also needs correction. Software implementation, adequate vacancy supply and human usefulness are separate completion claims.

## Scope and evidence

I read the original brief, current README and decision/pilot documents, the original source snapshot and relevant diffs, reviewer 1's findings, the remediation record, and the public/aggregate outputs. I used only fictional fixtures, in-memory network stubs and isolated temporary storage. I did not read `.state`, candidate documents, credentials or private candidate records, make network requests, or edit product source. Source locations below refer to the current project in `SCOPE.md` as inspected before the controller's second remediation.

Twelve targeted regression tests passed independently: the five matching remediation tests for language, tenure, attribution, duty formatting and review exits; four source/storage tests for corroboration, manual-check preservation, closures and legacy verification; and three evaluation tests for symmetric review pools, anonymous decks and incomplete judgements. These were targeted retests, not a second full-suite run. The controller reports the full first-remediation suite passed 62 tests.

## What the first review and fixes established

| First-review finding | Independent result |
| --- | --- |
| Mandatory language lost | The exact `German B2, C1 preferred` and Additional Information language examples now exclude B1 and allow B2. Mixed intent is still incomplete; see R2-1 and R2-2. |
| Unrelated tenure credited | SQL before/after “experience” now uses SQL months rather than generic relevant tenure. Shared minimums are covered. Qualifier preservation remains incomplete; see R2-5. |
| Other actors/hypotheses credited | The original `colleagues who…`, `whether to…` and assigned-only examples now withhold direct tags. Other common constructions still overclaim; see R2-3. |
| URL responsiveness presented as verification | Generic HTTP 200 pages, stale feed membership and wrong URLs no longer suffice. Manual opens and explicit closures survive the tested paths, and legacy URL-only verification is downgraded. Enabled application state remains unchecked; see R2-4. |
| Formatting/repetition inflated fit | The original coordinated/separate duties produce equal rank and review treatment. Repeated analysis duties no longer earn strong fit. |
| No manual resolution / seniority hold | Exact reviewed clauses resolve the tested uncertainty. Early-career Lead Analyst is held in both methods until vacancy-specific scope review. |
| Blind pilot lost diagnostics | Both methods' review lanes enter the pack. Blank ratings produce undefined rates with coverage, and fully labelled pools permit missed-positive diagnostics. The public 26-case sheet now has the required seven judgement fields. |

These fixes are substantive and match the first report. Passing their exact tests does not establish that the heuristic classes are fully resolved.

## Remaining verified defects and acceptance tests

### R2-1 — P1: a preference can still erase a mandatory minimum

**Location:** `career_discovery/analysis.py:304–310,334–341`.

**Reproduction:** Using the fictional graduate (German B1), take a fixture-open job with `Responsibilities:\n- Build dashboards.\n- Automate workflows.\nRequirements: German B2 (C1 preferred).` The parser emits the entire condition as `preferred`; the assessment is **actionable**. This differs from the now-fixed comma-only example. The controller separately identified `German at least B2, with C1 preferred` in the same class.

**Impact:** A known minimum-language conflict disappears from both ranking lanes. Similar mixed tool/preference wording must not inherit “preferred” for the whole condition solely because it contains an optional phrase.

**Bounded remedy and acceptance:** Separate optional parenthetical/asides from the main requirement while retaining its mandatory section intent. If separation is unsafe, hold the complete condition as unknown. For parenthetical, comma-with and existing comma-only variants, B1 must be excluded, B2 must satisfy the minimum, and C1 must remain optional. `German B2 required, English fluency is a plus` should retain mandatory German and optional English rather than losing either intent. Preserve the benefits exclusion test.

### R2-2 — P1: recognising one requirement can hide another unsupported condition

**Location:** `career_discovery/eligibility.py:172–185`; `career_discovery/analysis.py:323–327`.

**Reproduction:** With the same two duties and a fictional graduate having SQL evidence, `Requirements: SQL required with active security clearance.` produces only `sql: met` and an **actionable** assessment. The unknown security-clearance requirement never appears. Moving the second condition to `Additional information:\nA security clearance is required.` removes it from the parsed requirements entirely and also yields actionable.

**Impact:** Partial recognition is treated as complete resolution of a mandatory clause. Explicit conditions outside the small Additional Information allowlist are silently ignored. A candidate need not assert a known gap for an unverified mandatory condition to require review.

**Bounded remedy and acceptance:** Preserve unresolved qualifying conditions after recognised tools, languages or status facts; do not consider a whole clause resolved merely because one detector returned a finding. Retain explicit candidate requirements in neutral sections even when their subject is outside the current catalogue. Both clearance examples must remain verify-first until the exact condition is reviewed; an explicitly recorded clearance gap must exclude. A plain `SQL required` with valid SQL evidence should remain met. Benefits and company boilerplate should still be excluded. Clearance is a synthetic parsing test, not a proposed new automated legal judgement.

### R2-3 — P1: vendor actions and proposal content become direct candidate achievements

**Location:** `career_discovery/analysis.py:204–240`; direct-link consumption in `career_discovery/matching.py:104–114`.

**Reproduction:** Replace the fictional profile's evidence with a single CV-stated fictional paragraph, either `Managed a vendor that built dashboards and automated workflows.` or `Reviewed proposals to build dashboards and automate workflows.` Match a fixture-open job requiring `Build dashboards` and `Automate workflows`. Both paragraphs acquire `dashboard` and `automate` direct tags and yield **strong fit / actionable**.

**Impact:** The explanation attributes implementation to the candidate when the evidence describes vendor management or proposal review. The original fact is preserved verbatim, but the system's direct-capability claim is unsupported.

**Bounded remedy and acceptance:** Withhold direct implementation tags when the action is governed by another actor or proposal/plan content. Preserve any separately supported management/review capability without inventing the implementation. Neither reproduced paragraph may support those two direct links or a strong fit based on them. Positive controls such as `Built dashboards with a vendor` and `Reviewed proposals, then built dashboards and automated workflows` should retain clearly asserted personal implementation; ambiguous wording should remain unverified.

### R2-4 — P1: a closed page with a disabled application control becomes verified

**Location:** `career_discovery/sources.py:22–29,277–283` and `VisibleText`.

**Reproduction:** Create an ATS-source job at `https://job-boards.greenhouse.io/fictional/jobs/42`, with external ID `42`. Stub an exact-URL HTTP 200 response at the same time as feed membership, containing a matching `<h1>` plus `<p>Applications are closed.</p><button disabled>Apply now</button>`. `verify_job` returns **verified**. No network is needed.

**Impact:** A stale feed member and a nonfunctional retained button can create an actionable “verified” job. Matching text is currently treated as a visible application action without checking its element or enabled state, and the explicit closure phrase falls outside the narrow pattern.

**Bounded remedy and acceptance:** Explicit closure overrides positive page signals. Require an enabled, nonhidden application control or supported application-form signal; ordinary prose containing “Apply now” is insufficient. The reproduced page must be closed. A matching page with only a disabled/hidden button, or only a paragraph saying “Apply now”, must remain unverified. An enabled supported control plus current membership can verify. Keep exact URL, freshness, manual-check preservation, generic-page and existing expiry tests. Conservatively leaving unsupported ATS rendering unverified is acceptable.

### R2-5 — P2: shared tenure expansion loses bounds and trailing wording corrupts scope

**Location:** `career_discovery/eligibility.py:148–169,188–206`.

**Reproduction:** With fictional experience months `relevant=36, sql=0, python=36`, `2 years experience with SQL required` becomes an unknown requirement for the invented scope `sql required`, instead of the explicit SQL conflict. `Up to 2 years of experience with SQL or Python` returns **met**: the first alternative retains an upper-bound unknown, while the generated Python alternative becomes an invented minimum of 24 months satisfied by 36 months.

**Impact:** Equivalent wording yields inconsistent eligibility, and expansion can change an employer's upper bound into a minimum. This probe was identified by the controller and independently reproduced here.

**Bounded remedy and acceptance:** Separate scope from terminal modal wording and preserve the entire duration operator across conjunction/alternative expansion. Zero SQL months must conflict for both trailing-required and existing minimum forms; missing SQL tenure stays unknown. All “up to”, “at most”, “maximum” shared alternatives must retain conservative upper-bound review semantics, regardless of Python tenure. Ordinary shared minimum alternatives must still allow a genuinely satisfied route.

## Privacy and evidence integrity

No new confirmed privacy defect emerged in this bounded review. The inspected implementation keeps extraction local, restricts network traffic to public ATS requests, uses private file creation for profile/export artifacts, records aggregate search counts rather than raw CV text, and supports deleting the profile plus its feedback/run records. The anonymous deck tests confirm it excludes candidate evidence and method labels. This is limited source/test evidence, not a security or regulatory certification; exports and source CV deletion remain user-controlled as documented.

The public aggregate reports appropriately distinguish 24 responding application URLs from five corroborated Greenhouse pages and 19 unverified Ashby URLs, with two expired controls. R2-4 strengthens the integrity requirement; it does not prove that any of the five live pages is actually closed. I did not independently recheck live pages. Historical test counts in dated reports refer to their respective stages and should not be presented as current totals.

## Completion gates, separate from code fixes

**Immediate software gate:** Correct R2-1 through R2-5, add the bounded acceptance cases, and have the controller run the full offline suite. Invalidate affected cached analyses and any obsolete automatic availability proof when verification semantics change. Re-run aggregate frozen-corpus diagnostics at a fixed clock without converting a provisional candidate draft into a real confirmed profile. Keep zero unsupported factual claims and zero confirmed hard conflicts in actionable output as hard review criteria.

**Elapsed-time gate:** The comparable repeat employer observation remains due around 23 November, using the same source scope, candidate constraints and comparable analysis settings. Reanalysis at the original timestamp is not another observation. The first corpus's 1,181 records yielding one review-only case and zero actionable results fails the provisional ten-opening supply target; adding 117 targeted listings did not remedy that. The 26-case curated benchmark is useful for testing but is not an independent repeat supply sample.

**Consenting-human gate:** Candidate correction and confirmation, blind relevance/realism/eligibility/link judgements, a subsequent atomic explanation audit, and sessions with three to five consenting volunteers remain necessary. The owner draft's zero task review candidates and the baseline's review counts are diagnostics, not evidence of usefulness or inferiority without relevance labels. Time-to-three, observed reuse, useful new discoveries, explanation accuracy and valid-link targets remain unmeasured. The fictional 12/18 versus 5/10 results are designed-case checks with different filled-list denominators, not a validated improvement claim. Keep held-out profiles because the owner example informed parser changes.

**Decision:** Complete the bounded reliability fixes and continue the local pilot. Do not describe the product as validated, supply-ready or ready for public launch on the present evidence. The broader commercial/public-launch questions from the original brief remain future decision work rather than missing CLI features.
