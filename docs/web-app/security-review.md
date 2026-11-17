# Security and privacy review: local web app (HEAD 2733f13)

Scope: `webapp.py`, `webapi.py`, `tracker.py`, `storage.py`, `documents.py`, tests; `sources.py`/`network.py` skimmed.
Findings were checked against an in-process server on port 0 with a temp state dir. No network.

## Findings

1. **HIGH: anyone who can reach the port can get the launch token without authenticating.**
   Evidence: `webapp.py:257-271` serves `index.html` with the token filled in to any request whose Host is
   `127.0.0.1:<port>`, and a missing Origin is accepted (`:193-195`). Reproduction: `http.client` GET `/` with no headers
   returned 200 with the token, and `GET /api/export` with that token then returned 200. Loopback TCP does not separate
   users, so any other account on a shared machine can read the CV evidence, profile, applications and feedback, and call
   `POST /api/data/delete` or `/api/shutdown`. Browser threats are handled; the "other local users" threat is not.
   Minimal fix: pass a one-time launch secret in the URL that `webbrowser.open` opens, for example
   `/?launch=<secret>`. The server swaps it once for an `HttpOnly; SameSite=Strict; Path=/` cookie, redirects to `/`, and
   then requires that cookie before it serves the token page or any API call. Test that a bare `GET /` has no token.

2. **MEDIUM: the CSV formula guard can be bypassed when German-locale Excel opens the file.**
   Evidence: `tracker.py:69-80` neutralises only the first character of a cell, and `csv.writer` quotes only fields that
   contain `,`, `"` or a newline. Excel set to a `;` list separator (the default in de-DE, which is the target market)
   splits `Acme;=HYPERLINK("http://x")` into a second cell that starts with `=`. `company` and `title` come from employer
   boards or imported CSVs (third-party text). Impact: a hostile listing title can plant a link or formula in the sheet.
   Minimal fix: also neutralise formula starts after a separator, for example
   `re.sub(r"(^|[;,\t\r\n])(\s*[=+\-@])", r"\1'\2", text)`. Alternatively, write the export with `;` as the delimiter and
   `QUOTE_ALL`. Add a test with `Acme;=1+1`.

3. **LOW: connections have no socket timeout, so a local process can tie up threads indefinitely.**
   Evidence: `Handler` sets no `timeout`, and `ThreadingHTTPServer` starts one thread per connection without a cap. A client
   can open many connections and never finish the request line, or send a valid token and a `Content-Length` it never fills
   (`webapp.py:245`). A browser page cannot, as Origin is checked first. Impact: local denial of service only.
   Fix: `Handler.timeout = 30`; optionally cap connections with a semaphore.

4. **LOW: a killed PDF import can leave a copy of the CV outside the data folder.**
   Evidence: `documents.py:135` writes it to the system temp dir; if the process is killed during `pdftotext`, the 0600
   copy stays in `$TMPDIR`, outside delete-all. Fix: `mkstemp(dir=root/"cv-cache")`, which delete-all's `rmtree` covers.

5. **LOW: delete-all is narrower than "your data".**
   Evidence: `webapi.py:443-450` and `storage.py:368-373` keep the `job` rows. Those rows include jobs the user imported from
   their own CSV (`source='csv'`, which can contain descriptions they pasted), and those jobs reveal the user's search. The
   `supply` and `board_run` tables stay, and a concurrent recheck (no `self.lock`) can add a `run` row after the delete.
   Fix: also delete `source='csv'` jobs; take `self.lock` in `recheck`; say in the dialog that board listings stay.

6. **LOW: the data folder is made private only when the app creates it.**
   Evidence: `webapi.py:55-58` runs `chmod 0700` only when the folder is new. An existing folder, or a `--state DIR` the user
   chooses, keeps its mode (for example 0755 under `~/.local/share`). Files and subfolders are still 0600/0700, so other
   users can see file names but cannot read the contents. Windows relies on the inherited `%LOCALAPPDATA%` ACL, which is
   fine for the default folder and unprotected for a custom `--state` folder.
   Fix: on POSIX, `chmod 0700` the root whenever the user owns it; document that `--state` folders must be private.

## Checked and fine
- Token: `secrets.token_urlsafe(32)` per launch, compared with `compare_digest`. The token page is sent with `no-store` and
  `Referrer-Policy: no-referrer`. `log_message` is silenced and the printed URL has no token. A 401 closes the connection.
- Host/Origin: the Host check needs an exact host and port and ignores case. `[::1]`, a missing Host and a `null` Origin
  are rejected (403). An OPTIONS preflight from another site gets a 403 and no CORS headers, so a CSRF request cannot carry
  `X-CD-Token`. Framing is blocked (`X-Frame-Options: DENY`, `frame-ancestors 'none'`) and the CSP is `default-src 'self'`.
- No GET endpoint changes state, and every `/api/` route, including HEAD/405 and shutdown, checks the token first.
- Static serving: `..`, `%2e%2e`, `%5c`/backslash, NUL, dot-files and symlinks that leave `web/` (checked with `resolve()`
  and `is_relative_to`) all return 404. Upload filenames are used only for their suffix and display name, never as a path.
- Body limits: 10 MB, `Transfer-Encoding` refused, and only JSON or multipart accepted (415 otherwise). DOCX reads are
  capped at 2 MB per XML member, whatever the declared size (zip-bomb safe), and DOCTYPE/ENTITY is refused. `pdftotext`
  has a 12 s limit, 12 pages and 512 KB of output.
- Errors: unexpected errors return fixed sentences; the traceback goes only to the local terminal. ValueError text passes
  through `safe_text`.
- SQLite: each request and the refresh thread open their own connection, with `BEGIN IMMEDIATE`, a 15 s timeout and
  `secure_delete=ON`. Refresh state is guarded by `refresh_lock`.
- Network: requests are made only after `POST /api/jobs/refresh` or `POST /api/matches/recheck`. Requests are limited to
  allowlisted ATS hosts, redirects are checked, and budgets apply (45 for a refresh, 8 for a recheck). Recheck refuses
  `source='csv'` jobs, so an imported URL cannot cause a request (no SSRF). Nothing is fetched when the app starts.
- Export: JSON contains only the profile, CV info, feedback, applications and the last visit, with no token. CV cache files
  are 0600 in a 0700 folder.

## Fixes
1. HIGH token: `/?launch=<one-time secret>` sets the `cd_session` cookie (HttpOnly, SameSite=Strict) and redirects; `GET /` and `/api/` need the cookie (constant-time); a bare `GET /` returns a static page without the token. Tests: `test_page_without_the_session_cookie_has_no_token`, `test_launch_secret_sets_the_cookie_once`, `test_api_needs_the_session_cookie_even_with_the_token`. Fresh link needs a restart.
2. MEDIUM CSV: formula starts are neutralised after `; , tab` and newlines too. Test: `test_csv_neutralises_formulas_after_separators`.
3. LOW timeout: `Handler.timeout = 30`, a timed-out request just closes. Tests: `test_idle_connections_are_dropped`, `test_default_timeout_is_set`.
4. LOW PDF temp: copy named `cd-*.pdf`, removed in `finally` (already true on exceptions), stale copies over 1 h removed at start. Tests: `test_temp_copy_is_removed_when_the_process_raises`, `test_pdf_copy_uses_the_cd_prefix`, `test_stale_named_temp_copies_are_cleaned_up`.
5. LOW delete-all: also deletes `source='csv'` jobs; board jobs stay (api.md updated). Test: `test_delete_all_also_removes_csv_imported_jobs_but_keeps_board_jobs`. The recheck/lock race is not changed.
6. LOW permissions: an existing data folder owned by the user is set to 0700 at start on POSIX. Test: `test_existing_data_folder_is_made_owner_only_on_posix`.
