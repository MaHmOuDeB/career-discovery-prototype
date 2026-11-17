# Vacancy benchmark and matching replay

**17 November 2026**

The prototype has a 26-case public vacancy benchmark and a separate blind review sheet. The set contains analysis and operations jobs, adjacent work under different titles, and cases for closure, geography, employment type, language or seniority. These are coverage categories. Candidate relevance ratings have yet to be collected.

Ten of eleven added public boards responded within the request limits and supplied 260 listings. One board exceeded the response size limit. The benchmark selected 24 records across the new and earlier employer snapshots. All 24 official application URLs responded and had recent employer-feed membership. A stricter check added during review corroborated five Greenhouse application pages. The 19 Ashby URLs remained unverified. Three required support for Greenhouse’s European application hostname. Two expired employer pages are negative controls. [Greenhouse European example](https://job-boards.eu.greenhouse.io/orcristtechnologies/jobs/5017454101) · [Delivery Hero data analyst control](https://careers.deliveryhero.com/job/associate-data-analyst-tech-foundations-finops-and-tech-metrics-in-berlin-germany-jid-10515) · [Delivery Hero product analyst control](https://careers.deliveryhero.com/job/associate-product-analyst-logistics-service-in-berlin-germany-jid-6069)

## Matching result before the independent reviews

The revised parser recognises actions separated from their objects by qualifiers. Regression cases cover reviewing experiments without running them, learning a tool, building learning materials, and explicit exclusions in job descriptions. Partial evidence must connect distinct responsibilities to distinct task types and stays in the review queue.

| Berlin test using the approved private draft | Title review candidates | Task review candidates | Actionable from either method |
| --- | ---: | ---: | ---: |
| Curated 26-case benchmark | 6 | 0 | 0 |
| Frozen 1,298-listing replay | 129 | 0 | 0 |

The broader task phrases initially surfaced a senior role by misreading an explicitly excluded job duty. The corrected parser removed it. Candidate relevance and any lift over title search still need human ratings. Four task types were recognised in the private CV-stated evidence, and the saved draft remained unconfirmed.

At this benchmark stage, the complete offline suite passed **53 tests**. Fictional precision counts stayed at **12/18** for task-based matching and **5/10** for the title baseline. The private replay made zero network requests and paid API spend remained zero.

## Pilot readiness

The [vacancy benchmark review sheet](<Vacancy benchmark review sheet.md>) lets a reviewer assess all 26 listings in a shuffled order without seeing the ranking method. No human ratings have been submitted. The repeat employer-board observation is due around 23 November. The first snapshot was re-analysed with the current catalogue at its original timestamp so it can be compared with the second observation.
