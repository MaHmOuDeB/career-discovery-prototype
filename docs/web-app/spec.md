# Career Discovery local web app: spec v1 (17 November 2026)

Status: feature set and look chosen by the owner on 17 November 2026 (quotes below). The owner delegated the
choice of further helpful features: "Add all the mentioned features above as well as other features you believe
would be helpful for jobhunters."

## Intent
Who uses it: job seekers in Germany, often international graduates, on their own Windows or Mac laptop. No terminal skills assumed.
Job it does for them: from their CV, find current jobs whose work matches what they have done, explain why, flag
hard conflicts (language, location, seniority) early, and keep their applications organised.
How the owner will know it worked: a volunteer can go from download to a first list of matches without help, and
pilot feedback says the matches and reasons are useful.

## Type and platforms
Local web app: a Python standard-library server on 127.0.0.1, opened in the user's default browser.
Platforms: Windows 10/11, macOS 13+, Linux. Browsers: current Chrome, Edge, Safari, Firefox.
Languages: English and German interface (switch in the header; the default follows the browser language).

## Owner's picks (17 November 2026)
| Decision | Choice | Quote |
| --- | --- | --- |
| Look | B, friendly guide: step bar, larger text, plain-language reasons, teal accent | "B Friendly guide (Recommended)" |
| Install | Download ZIP, double-click starter; installs Python via uv if missing | "Double-click starter (Recommended)" |
| Interface languages | English and German | "English and German (Recommended)" |
| Core features | CV upload and review, fetch jobs from the 12 boards, matches with reasons and feedback, export and delete | (all four selected) |
| Extras | Application tracker, still-open check, language reality filter, application wording helper, plus more | (all four selected, plus delegation above) |

## Scope (v1)
Guided steps (step bar): 1 Your CV, 2 Your details, 3 Find jobs, 4 Your matches. Separate pages: My applications, Your data.
1. CV: upload DOCX or PDF (drag and drop or file picker) or start without a CV. Each extracted item is shown with its
   source line; the user keeps, edits or removes it. Only kept items count as evidence.
2. Details: languages with CEFR levels (with a plain-language level guide), preferred cities, remote countries,
   employment types, familiar job titles, optional sponsorship and graduation answers. Confirm button.
3. Find jobs: one button reads the 12 reviewed employer boards (progress shown), optional CSV upload. Shows how many
   jobs are stored and when they were last fetched.
4. Matches: ranked cards in the evidence-based order, with a title-search comparison view. Each card shows:
   fit label in plain words; why it fits (ad duty next to the CV line); what to check first; hard conflicts.
   Feedback: "Useful", "Not for me" (with optional reason), "New to me".
Extras on matches
- Still-open check: posting age, last confirmed open, source is the employer's own board; one-click recheck for
  supported boards (the existing bounded `verify_job`).
- Language reality: the German and English level the ad asks, next to the user's; filter "Hide jobs my languages rule out".
- Pay: the salary or range when the ad states one, otherwise "Pay not stated".
- Deadline when the ad gives one.
- Wording helper: ad duties the CV supports (ad wording plus the CV line) and ad duties the CV does not show yet,
  labelled "Add to your application only if true". No generated text.
- Roles you might not have searched: role families backed by the user's evidence (`discover_families`).
My applications (tracker): statuses Saved, Applied, Interview, Offer, Rejected, Withdrawn; applied date; notes;
follow-up date defaulting to 7 working days after applying; CSV export. Weekly overview at the top: applied this week,
follow-ups due, interviews coming up, new matches since the last visit.
Your data: where the data lives on disk, download everything (JSON), delete everything (typed confirmation), close the app.

Cut list (not in v1; the owner would not miss them at a pilot): accounts, cloud sync, more boards or LinkedIn,
e-mail reminders, AI-written cover letters, auto-apply, mobile layout beyond reflow, multiple profiles per install.
Non-goals: no AI or paid API, no data leaves the machine except the user-started job-board reads, no tracking or analytics.

## Acceptance criteria
| Feature | Criterion | Check |
| --- | --- | --- |
| Start | Double-click starter opens the app in the browser within 60 s on a machine with Python 3.12+; without Python, uv installs it first | CI runs the app module start and a smoke request on 3 OSes; manual run on macOS |
| CV | A DOCX upload lists evidence items with source lines; removing an item excludes it from matching | unit + API tests |
| Details | Invalid CEFR level or empty language list shows an inline message; nothing saved until valid | API test |
| Find jobs | Refresh reads only the boards in the shipped reviewed list, honours the existing bounds, reports progress and per-board errors | API test with a fake client |
| Matches | Records equal `run_match` output for the same state and clock, plus the extra fields | API test |
| Tracker | Status change persists across restarts; follow-up defaults to 7 working days; CSV export opens in a spreadsheet | storage + API tests |
| Data | Export contains profile, feedback, applications; delete removes them and the uploaded CV cache | API test |
| i18n | Every visible string comes from `en.json`/`de.json`; a test fails on a missing key | unit test |

## Quality floor
- Accessibility: WCAG 2.2 AA contrast, full keyboard use, visible focus, labels on every input, 44 px targets,
  `prefers-reduced-motion`, reflow at 320 px and 200% text without horizontal scroll.
- Performance: first screen under 1 s locally; no external requests from the page (no CDN, fonts or icons from the web).
- Security (local server): bind 127.0.0.1 only; per-launch random token required on every API call; reject a Host
  other than 127.0.0.1/localhost on the bound port (DNS rebinding); reject cross-origin Origin; JSON or multipart only;
  upload limit 10 MB; CSP `default-src 'self'`; `X-Frame-Options: DENY`; `Cache-Control: no-store` on API responses;
  never echo raw exceptions. Files in the user data folder; owner-only permissions on macOS and Linux.
- Truth: wording and fit labels come from the matcher; the UI never claims more than the record says.

## Data contracts
- Data folder: macOS `~/Library/Application Support/Career Discovery`, Windows `%LOCALAPPDATA%\Career Discovery`,
  Linux `$XDG_DATA_HOME/career-discovery` (default `~/.local/share/career-discovery`). Override with `--state`.
- One profile per install, id `me`. Times are UTC ISO 8601 in storage; the UI shows Berlin dates.
- API: JSON over HTTP on `127.0.0.1:<port>`, header `X-CD-Token`. Endpoints are listed in `api.md` (written by the
  backend lane, from this spec).

## Human-only steps
| Step | Who | Code runs without it? |
| --- | --- | --- |
| First open of the downloaded starter past the Mac Gatekeeper or Windows SmartScreen prompt | each user | no; README shows the clicks |
| Try the app with a real CV and give feedback | owner, volunteers | yes |

## Risks and open questions (each with a default)
1. Downloaded starters are unsigned. Default: README shows the one-time "Open anyway" steps with screenshots later.
2. Salary wording varies. Default: show only amounts with a currency next to a pay word; otherwise "Pay not stated".
3. Board reads can fail. Default: per-board error in plain words; matching still runs on cached jobs.
