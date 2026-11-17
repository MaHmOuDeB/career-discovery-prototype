> Historical report. See the current handoff for the latest test count and status.

# Career Discovery Prototype — implementation report

**16 November 2026**

The local MVP is implemented in the project root. Its README describes profile import and review, vacancy sourcing, matching, feedback and privacy controls. The project also contains a decision log and an anonymous pilot protocol.

## Try it

```sh
python3 -B -m career_discovery demo --profile technical-graduate --details
python3 -B -m unittest discover -s tests -v
```

The demo is offline and uses fictional people and vacancies. The same command without the profile option compares all four fictional profiles.

## Milestones

| Milestone | Verified result | Remaining |
|---|---|---|
| Offline comparison | Four fictional profiles, 24 fictional jobs and 96 candidate–job pairs. The task matcher returned 12 of 18 fixture-labelled relevant recommendations. Title and keyword search returned 5 of 10. Each method had a cap of five per profile and could leave slots empty. | Human relevance ratings on a shared real corpus. |
| Vacancy sourcing | 12 public Greenhouse and Ashby boards responded, with 1,181 listed records before candidate screening. Both formats parsed. One sampled ATS-hosted apply path from each provider corroborated the live verifier. | The first supply screen fell below the ten-vacancy threshold. One listing reached review for the fictional Berlin graduate. Inspecting it showed prior knowledge-systems and stakeholder enablement experience beyond the evidence in the fictional profile. A Germany-wide location variant returned the same listing. Repeat supply observation remains due about a week after the first. |
| Local CV-to-shortlist workflow | Imported generated PDF and DOCX files with evidence locators. Confirmed profiles, compared rankings, checked the CSV flow, saved feedback, exported it and tested deletion. The synthetic semantic exchange accepted a reviewed transfer, with the same shortlist precision in this example. | Real-document variety, including complex layouts, needs testing with consent. Scans use manual entry. |
| Small user pilot | Added an anonymous evaluation schema and scoring CLI. Verified it with fictional ratings. | Owner and volunteer sessions, human explanation audits, real time savings, reuse, and the 19-of-20 link target remain unmeasured. |

## Verification and decisions

- **40 automated tests passed.** The suite requires no network. It covers document handling, profile review, requirement boundaries, title traps, evidence, deduplication, source failures, availability and privacy controls.
- **Paid API spend was $0.** The public sourcing tests used bounded unauthenticated reads. Original Claude Code assets, trackers and CVs were preserved. No real CV or volunteer data was processed.
- The first live pass overcounted opportunity because common employer headings were missed. The parser was corrected and the supply measurement re-run. Ranked results retain a review category for unresolved conditions.
- DOCX uses the installed macOS Python parser as a fallback on this machine after a Homebrew XML-library incompatibility surfaced. The project leaves system settings intact.
- The live count applies to the selected employers and the fictional profile. The experiment can be repeated with a more targeted permitted corpus. The semantic exchange stays on fictional data, with human review before changes affect ranking.

[Greenhouse Job Board API](https://docs.greenhouse.io/job-board) · [Ashby Job Postings API](https://developers.ashbyhq.com/docs/public-job-posting-api)
