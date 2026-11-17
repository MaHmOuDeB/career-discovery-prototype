> Historical report. See the current handoff for the latest test count and status.

# Follow-up validation

The prototype now explains why listings fall outside the graduate supply screen and prepares a blind reviewer deck with a separate scoring key. The expanded source check and the remaining real-user steps are recorded below.

## What the added sources changed

| Corpus | Listings assessed | Reached review under the supply screen | Actionable |
| --- | ---: | ---: | ---: |
| Original 12 employer boards | 1,181 | 1 | 0 |
| Eight additional targeted employer boards | 117 | 0 | 0 |
| Same eight boards, adding internships and temporary roles to the fictional profile | 117 | 0 | 0 |

The additional Ashby boards belonged to AMBOSS, Bettermile, LIQID, Ostrom, bunch, Upvest, finmid and Hawk. They were stored separately from the original corpus. Among the 117 listings, 54 triggered an insufficient responsibility-coverage alert and 27 had an explicit location conflict. Flags can overlap. The alert exposes an important measurement limit. A small count can reflect unsuitable vacancies, incomplete extraction, or both.

## Live cases and fixes

- Ostrom’s growth associate application path responded, and the job description specifies C2 German. The corrected matcher records the language conflict for the fictional profile. [Employer listing](https://jobs.ashbyhq.com/Ostrom/c2073b43-69b3-41d2-b914-d8fbf17dc8eb)
- finmid’s operations internship was present on the feed and its apply path responded. The profile variant that allows internships reaches verification, with insufficient task evidence and an unquantified English requirement. It is useful as a review case. [Employer listing](https://jobs.ashbyhq.com/finmid.com/a00eb04e-b3f5-45e4-8792-b75901ac969c)
- LIQID’s internship was listed as full-time in source metadata. The importer now preserves internship as the position type, including for already cached vacancies. The parser separately identifies the stated B2 German minimum and C1 preference. [Employer listing](https://jobs.ashbyhq.com/liqid-lig/41c3002a-a122-46e9-b4d3-e5ec812fbe2a)
- Four apparently relevant results from Delivery Hero led to employer pages that explicitly marked the jobs expired. A current search result and a responding employer page can coexist with a closed application. The verifier now recognises this explicit expiry wording. [Associate Data Analyst](https://careers.deliveryhero.com/job/associate-data-analyst-tech-foundations-finops-and-tech-metrics-in-berlin-germany-jid-10515) · [Associate, Data Science](https://careers.deliveryhero.com/job/associate-data-science-in-berlin-germany-jid-6155) · [Associate Product Analyst, Logistics](https://careers.deliveryhero.com/job/associate-product-analyst-logistics-service-in-berlin-germany-jid-6069) · [Associate Product Analyst](https://careers.deliveryhero.com/job/associate-product-analyst-all-genders-in-berlin-germany-jid-1851)

## Verification

**45 automated tests passed.** The fictional benchmark remained at 12 relevant task-based recommendations out of 18 and 5 out of 10 for title and keyword search. The reviewer deck was generated through the CLI using fictional evidence. Its public vacancy links appear without candidate CV text or method labels. The scoring key stays separate. Paid API spend was **$0**.

## Open validation steps

- Repeat the original board observation approximately a week after 16 November 2026. Run with the same profile and source scope. The comparison explicitly checks elapsed time and comparability.
- A private owner test requires the owner’s permission to use a specific CV and sufficient profile review. The human pilot requires consent and ratings from real participants. No real CV or volunteer data was used.
- The current board mix has fallen short of the vacancy gate. A curated pool from current employer indexes or permitted user imports would also help separate ranking quality from supply quality in the owner test.

From the project directory, the repeat observation runs with:

    python3 -B -m career_discovery --state .state/pilot refresh .state/pilot/boards.json
    python3 -B -m career_discovery --state .state/pilot supply

The decision log and pilot protocol are in the project’s docs directory.
