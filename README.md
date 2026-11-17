# Career Discovery Prototype

A local CLI that compares a traditional title and keyword search with matching based on evidence for the work. It is configured for an initial Germany pilot.

For Claude Code, see [CLAUDE.md](CLAUDE.md) and the [project handoff](docs/handoff/README.md).

## Quick start

Use Python 3.14 on macOS or Linux. The standard library handles the matcher, storage, CSV and DOCX. A local Poppler installation with pdftotext is needed for PDF imports. The demo and offline tests require no network or credentials.

    cd "/path/to/Career Discovery Prototype"
    python3 -B -m career_discovery demo
    python3 -B -m career_discovery demo --profile technical-graduate --details
    python3 -B -m unittest discover -s tests -v

The demo runs four fictional profiles against 24 fictional vacancies. It uses the same corpus, eligibility checks, and top-five cap for both rankings. Underfilled lists are shown as such. Fixture results are a check on designed cases. Real relevance and usefulness need human ratings.

## Import and review a profile

    python3 -B -m career_discovery profile import my-profile "/path/to/test-cv.docx"
    python3 -B -m career_discovery profile show my-profile

Edit the JSON file named by the import command. Add the candidate's own languages and CEFR levels, preferred locations, remote-work countries, employment types, familiar search titles and keywords. Set optional enrolment, graduation and sponsorship answers only if the candidate wants to supply them. Use relevant experience in months keyed by scope, for example "sql" or "relevant". Leave facts unknown when unsure. For a requirement held for manual review, check the employer’s wording. If it is optional or you have established that you meet it, enter the exact displayed clause in `verified_requirements` and save the profile. For a senior role held for an early-career profile, use `Seniority and ownership: <employer vacancy URL>` after checking the actual scope with the employer.

Each imported evidence item has an original paragraph or extracted page and line. Review the exact wording and scope. A CV-stated entry is a claim from the document. A user-confirmed entry records the candidate’s judgement. Entries marked inferred or missing stay outside the match. Leave confirmed false until after review. If you edit a previously confirmed profile, set confirmed false and confirm the revised profile again.

    python3 -B -m career_discovery profile confirm my-profile
    python3 -B -m career_discovery discover --profile my-profile

For a scan or unsupported Word layout, start with profile new and add evidence manually. A repeat import of the same document under the same ID preserves profile corrections. Use profile import with --replace for a changed CV. The replacement profile needs a new review. PDF extraction covers up to twelve pages. DOCX extraction reads the main body, including ordinary table paragraphs, and may miss content in drawings, tracked revisions or other document parts.

## Add vacancies and search

**CSV.** Required columns are company, title and url. Optional columns are external_id, apply_url, description, locations, workplace, remote_regions, employment, listed_date, date_kind and deadline. Separate multiple places or regions with a pipe. Use ISO dates and a matching date_kind of posted, updated or last_published. Use full_time, part_time, internship, working_student, freelance, contract, temporary or trainee for employment. Leave unstated fields empty. Use --keep-description only with content you are permitted to keep locally.

    python3 -B -m career_discovery import-jobs "/path/to/vacancies.csv" --keep-description
    python3 -B -m career_discovery jobs
    python3 -B -m career_discovery check-job "https://employer.example/vacancies/role-id" open
    python3 -B -m career_discovery search --profile my-profile --mode both

Use check-job only after manually checking the actual application path. Imported vacancies begin unverified. For a particular job, use its full URL or the job_key returned by jobs or search --json.

**Employer feeds.** docs/boards.example.json lists boards that responded during the smoke test. Copy it to your private state, then enable only the boards you have reviewed for your local use. The tested pilot uses the separate .state/pilot state directory. Place the --state option first to work with it consistently.

    python3 -B -m career_discovery --state .state/pilot refresh .state/pilot/boards.json
    python3 -B -m career_discovery --state .state/pilot supply
    python3 -B -m career_discovery --state .state/pilot supply --history

The coverage report uses a fictional graduate by default. Its screen is a count for manual review. It does not establish relevance or availability. Capture another snapshot about a week apart and compare unique vacancies. Same-day recalculations on the same feed are a single observation.

search --verify adds up to ten bounded rechecks on supported ATS-hosted application paths. verify-job checks one stored employer-feed job. Custom careers domains and imported URLs use check-job. Matching can run offline on cached jobs. After 24 hours, earlier availability checks need renewal. Automatic verification requires recent employer-feed membership, the exact job URL, a matching job heading, and an enabled application control. JavaScript-only or ambiguous pages stay in manual review. Read the employer page before applying.

## Feedback and records

    python3 -B -m career_discovery feedback --profile my-profile --job "https://employer.example/vacancies/role-id" --relevance yes --would-consider yes --new-to-me yes
    python3 -B -m career_discovery profile export my-profile "/path/to/private-export.json"
    python3 -B -m career_discovery profile delete my-profile --yes

Feedback records the candidate’s judgement and can include a correction. Export includes the profile and saved feedback. Deletion removes the local profile, its feedback and its search logs. Originals and any exports are controlled by the user. New files are private to the local account by file permissions. Put the state directory on local storage outside cloud sync. The prototype does not encrypt files itself.

## Optional semantic comparison

A provider-independent proposal exchange works on the built-in fictional material. It prepares a bounded brief, checks exact excerpts and stable IDs, and requires human acceptance before a transfer link affects ranking. It does not call an API. See [Semantic experiment](docs/semantic.md).

## Where to make a decision

- [Pilot protocol](docs/pilot.md) covers the frozen-corpus comparison, anonymous reviewer deck, vacancy supply gate, ratings and volunteer sessions.
- [Decision log](docs/decisions.md) records reuse, implementation choices and limitations.
- career_discovery/catalog.json contains a small editable task map and directional transfer rules. Pass the --catalogue option before your command to try a separate version.
