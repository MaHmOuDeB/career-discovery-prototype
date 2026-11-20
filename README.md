# Career Discovery Prototype

A local web app and command-line tool that match job ads to the work a person has done, and compare that with a traditional title and keyword search. It is configured for an initial Germany pilot.

Status: research prototype. It runs offline on your own machine, uses fictional profiles and vacancies for its tests and demo, and has no hosted service. Results and open questions are in the [project handoff](docs/handoff/README.md).

## What the app does

The app finds jobs by the work you have done, not only by the job titles you already know. It explains every match, and it runs entirely on your own computer. There is no AI model and no account: a rule-based matcher compares the duties in each job ad with the work your CV shows. The interface is in English and German (the EN and DE buttons in the header).

The app walks you through four steps, then two pages help you keep track:

1. **Start with your CV.** Upload a Word (.docx) or PDF CV, or start without one. The app lists the work it found. You keep what is true, fix what is not quite right, remove the rest and add things in your own words. Only items you keep count.
2. **Tell us a bit more.** Your languages and levels (A1 to C2, with a guide), the cities you would work in, the countries you could work from remotely, the kinds of work you are open to, and optional answers about recent graduation and visa sponsorship. Job titles you already know feed the title-search comparison.
3. **Find jobs.** One button reads the public job boards of 12 employers. A second button also reads three more employers with operations roles in Berlin (Trading 212, bunch and Upvest) and reports how many extra listings they added. You can also load your own jobs from a CSV file, and choose whether to keep their descriptions for duty matching.
4. **Your matches.** Jobs sorted into "Looks like a good fit", "Worth a closer look" and, if you ask, "Probably not for you, and why". Each card shows:
   - why it fits: the ad's duty next to the line from your CV that backs it;
   - possible conflicts, such as a language level, place or kind of work that does not fit;
   - the language level the ad asks for next to yours;
   - pay if stated, the deadline, and how long ago the job was posted;
   - help with wording your application: which duties your CV supports, and which are not in it yet (add them only if true).

   At the top, a bar shows what you are looking for, with a Change button. You can search the matches by title, company, place or duty, in English or German: a German search such as "Dashboards erstellen" also finds an English ad that says "Build dashboards", and the card quotes the duty that matched. You can hide jobs your languages rule out, and compare the results with a plain title search. "Roles you might not have searched for" suggests job families backed by your experience.
5. **My applications.** Save a job from your matches and track its status, dates, notes and follow-ups. The page shows what is due this week and new matches since your last visit, and exports the list as CSV.
6. **Your data.** See where your data lives, download all of it as one file, delete everything, or close the app.

Before you apply, the **Recheck** button on a job from the employer boards visits the employer's page and checks the job is still open.

What the app does not do: it does not apply for you, write application text, or send anything about you anywhere. The internet is used only to read public job boards and, when you press Recheck, one employer page.

## Use the app (no terminal needed)

The app runs on your own computer and opens in your web browser. It never uploads your CV. The only internet use is when you press the button to read the public job boards, or Recheck on a job.

1. Open the project page on GitHub, click the green **Code** button, then **Download ZIP**.
2. Unzip the file (double-click it on a Mac; right-click and **Extract All** on Windows).
3. Open the unzipped folder and double-click the starter: `Start Career Discovery.command` on a Mac, `Start Career Discovery.bat` on Windows, `start.sh` on Linux.
4. If your computer warns you the first time:
   - Mac, "cannot be opened": right-click the starter, choose **Open**, then **Open** again. Or go to System Settings, Privacy & Security, and click **Open Anyway**.
   - Windows, SmartScreen: click **More info**, then **Run anyway**.
5. Wait a moment. Your browser opens with the app.

What happens the first time: if your computer has no Python 3.12 or newer, the starter explains what it will install and waits for you to press Enter. It installs the free uv tool from astral.sh, which downloads Python into your own user folder. It needs no admin rights. Later starts take a few seconds.

To stop: click the app's Close button, or close the starter window.

Where your data lives: macOS `~/Library/Application Support/Career Discovery`, Windows `%LOCALAPPDATA%\Career Discovery`, Linux `~/.local/share/career-discovery`. The app's Your data page can export or delete it.

To remove everything: delete the unzipped folder and the data folder above. If the starter installed uv, also delete the `uv` and `uvx` files in `~/.local/bin` (Windows: `%USERPROFILE%\.local\bin`) and uv's Python downloads (run `uv cache clean` first; they are in `~/.local/share/uv` on Mac and Linux, `%APPDATA%\uv` on Windows).

For Claude Code, see [CLAUDE.md](CLAUDE.md); for Codex and other agents, [AGENTS.md](AGENTS.md).

## Quick start

Use Python 3.14 on macOS, Linux or Windows. The standard library handles the matcher, storage, CSV and DOCX. A local Poppler installation with pdftotext is needed for PDF imports. The demo and offline tests require no network or credentials.

    git clone https://github.com/MaHmOuDeB/career-discovery-prototype.git
    cd career-discovery-prototype
    python3 -B -m career_discovery demo
    python3 -B -m career_discovery demo --profile technical-graduate --details
    python3 -B -m unittest discover -s tests -v

The demo runs four fictional profiles against 24 fictional vacancies. It uses the same corpus, eligibility checks, and top-five cap for both rankings. Underfilled lists are shown as such. Fixture results are a check on designed cases. Real relevance and usefulness need human ratings.

### Windows

1. Install Python 3.14 from [python.org](https://www.python.org/downloads/windows/) and use the `py` launcher instead of `python3`.
2. Clone the repository, or download the ZIP from GitHub and extract it.
3. In PowerShell, from the project folder:

       py -B -m career_discovery demo
       py -B -m career_discovery demo --profile technical-graduate --details
       py -B -m unittest discover -s tests -v

4. DOCX imports work without extra software. PDF imports need Poppler for Windows with `pdftotext.exe` on `PATH`.
5. The `scripts/*.sh` helpers need Git Bash (or WSL).

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

Feedback records the candidate’s judgement and can include a correction. Export includes the profile and saved feedback. Deletion removes the local profile, its feedback and its search logs. Originals and any exports are controlled by the user. On macOS and Linux, new files and the state directory are owner-only through file permissions. On Windows they inherit the access rules of the folder they are created in, so keep the state directory inside your own user profile folder. Put the state directory on local storage outside cloud sync. The prototype does not encrypt files itself.

## Coverage diagnostics

    python3 -B -m career_discovery --state .state/pilot coverage --at 2026-11-16T22:52:55+00:00
    python3 -B -m career_discovery --state .state/pilot coverage --titles "analyst|operations|support"
    python3 -B -m career_discovery heldout fixtures/heldout/vacancies.json
    python3 -B scripts/score-evidence.py fixtures/heldout-v3/evidence.json
    python3 -B scripts/profile-yield.py

coverage reports how many duty lines in the stored vacancies map to a catalogue task, how many listings yield no duties, and the fit, lane and review-reason counts for the fictional scenario. It prints aggregate counts only and writes nothing. heldout scores the analyser against 24 labelled fictional vacancies written independently of the matching vocabulary: duty detection, task precision and recall, qualification lines mistaken for duties, and mandatory language conflicts. There are three independent sets: `fixtures/heldout`, `fixtures/heldout-v2` and `fixtures/heldout-v3` (24 ads each; v3 also has 30 labelled CV lines, scored with `scripts/score-evidence.py`). `scripts/profile-yield.py` compares supply yield for fictional profiles on a temporary copy of the pilot pool. Use the same pool and clock when you compare two versions of the analyser. Keep the held-out file out of any tuning work, otherwise its scores stop being an independent check.

## Optional semantic comparison

A provider-independent proposal exchange works on the built-in fictional material. It prepares a bounded brief, checks exact excerpts and stable IDs, and requires human acceptance before a transfer link affects ranking. It does not call an API. See [Semantic experiment](docs/semantic.md).

## Where to make a decision

- [Pilot protocol](docs/pilot.md) covers the frozen-corpus comparison, anonymous reviewer deck, vacancy supply gate, ratings and volunteer sessions.
- [Decision log](docs/decisions.md) records reuse, implementation choices and limitations.
- career_discovery/catalog.json contains a small editable task map and directional transfer rules. Pass the --catalogue option before your command to try a separate version.

## Licence

MIT. See [LICENSE](LICENSE).
