# Web app backend report (17 November 2026)

Status: DONE. Contract for the UI lane: `docs/web-app/api.md` (87 lines).

## Files
- New: `career_discovery/webapp.py` (server, security, static, `app` runner, `--smoke`), `webapi.py` (service logic, no HTTP),
  `salary.py`, `tracker.py`, `web/index.html` (placeholder with the token meta tag), `boards.json` (copy of `docs/handoff/supply-boards.json`).
- New tests: `tests/test_webapp.py` (26), `tests/test_salary.py` (2 tests; 15 positive and 17 negative examples), `tests/test_tracker.py` (5).
- Edited: `storage.py` (tables `application` and `meta` via `CREATE TABLE IF NOT EXISTS`, plus tracker, meta, feedback and delete methods),
  `sourcing.py` (`refresh_boards(..., progress=None)`, optional callback, default behaviour unchanged), `__main__.py` (`app` subcommand),
  `.github/workflows/tests.yml` (step "Web app smoke": `app --smoke --port 0`, prints OK and exits).
- Not touched: analysis, eligibility, matching, catalog.json, fixtures, ANALYSER_VERSION, existing assertions. No helper added to matching.py.

## Tests (RED first, then GREEN)
- RED: `python3 -B -m unittest discover -s tests -p "<module>.py" -q` for test_salary, test_tracker, test_webapp: all three failed
  with ModuleNotFoundError (`career_discovery.salary`, `.tracker`, `.webapi`).
- GREEN, Python 3.14.7: test_salary 2 OK, test_tracker 5 OK, test_webapp 26 OK (2.4 s), test_sourcing 18 OK, test_cli 4 OK.
- GREEN, Python 3.12 (Homebrew): test_salary, test_tracker, test_webapp OK. test_webapp also passes with `-X warn_default_encoding -W error::EncodingWarning`.
- Manual: `app --smoke --port 0` prints OK; `app --no-browser --state X` then SIGINT exits 0 with "Stopped." and a 0700 folder.

## Not run
- Full suite, demo, `scripts/gates.sh` (controller). Python 3.13. Windows and Linux (code avoids POSIX-only calls; `chmod` guarded by `os.name`).
- No real network, no real browser (`webbrowser.open` untested). PDF upload not exercised (needs Poppler); DOCX path is.

## Decisions where the spec was silent
- `--state` on `app` is its own option (`app_state`), separate from the global `--state`; the app default is the per-user folder.
- Evidence: `keep` makes an `inferred` item `user_confirmed`; `edit` marks the item `user_confirmed`; `add` creates `me-NNN`.
- Refresh progress needs a per-board callback, hence the small `progress` parameter in `sourcing.py`.
- Follow-up = 7 Mon-Fri days, no public holidays. Follow-ups due: status applied or interview with `follow_up_on <= today` (Berlin).
- "New matches" = task matches in actionable plus verify-first lanes not in the set stored by `POST /api/summary/seen`.
- Uploaded CV is cached in `cv-cache/` (needed so delete-all has something real to remove and the UI can show the file name).
- Delete-all also clears all `run` rows and visit markers. Supply history (fictional scenarios only) is untouched.
- Hosts accepted: `127.0.0.1:<port>` and `localhost:<port>`. Each request is HTTP/1.0 (no keep-alive); a new SQLite connection per request.
- CSV import accepts multipart or JSON `{"csv": ...}`; the spec allows only JSON or multipart, so raw `text/csv` is refused.

## Concerns
- Packaging: no setup file exists, so `boards.json` and `web/` are package data only by location. The ZIP starter must include them.
- `language_summary.asked` is derived by re-running the existing `language_findings` with a probe profile (no matcher edit); it follows any later change there.
- `ValueError` text from existing parsers is shown to the user as the error message; it is plain but could name a temp file path in rare cases.
- First `GET /api/summary` runs the matcher (about 0.1 s for 24 jobs); with thousands of cached jobs the state and summary calls may need caching.
