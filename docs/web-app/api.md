# Local web app API (v1)

Server: `python -m career_discovery app [--port N] [--no-browser] [--state DIR] [--smoke]`. It binds 127.0.0.1 only
(port 8765 or the next free one). On start the terminal prints, and the app opens, `http://127.0.0.1:<port>/?launch=<secret>`.
That link works once: the server answers with `Set-Cookie: cd_session=<session secret>; HttpOnly; SameSite=Strict; Path=/` and
`303` to `/`. Lost or used link: stop and start the app again. `GET /` serves `career_discovery/web/index.html` with
`<meta name="cd-token" content="...">` filled in per launch, only when the cookie is present; without it `GET /` returns a small
static page (English and German) that says to open the app from its starter window and contains no token. Static assets stay public.
Read the token once; send it on every `/api/` call. Connections time out after 30 seconds.

## Rules for every call
- The `cd_session` cookie and header `X-CD-Token: <token>` on every `/api/` request (401 `unauthorized` without either). Fetch downloads with this header
  and save the blob; a plain link cannot send it.
- Host must be `127.0.0.1:<port>` or `localhost:<port>`; a foreign `Origin` is refused (403).
- Bodies: `application/json` (object) or `multipart/form-data`, at most 10 MB (413 `too_large`, 415 `unsupported_type`).
- Success: HTTP 200 and a JSON object. Failure: `{"error": {"code": "...", "message": "<plain sentence>", "fields": {"name": "message"}}}`
  (`fields` only on 422). Show `message` to the user; branch on `code`. Codes: `unauthorized` 401, `bad_host` `bad_origin` 403,
  `not_found` `no_profile` 404, `method_not_allowed` 405, `profile_exists` `profile_not_ready` `refresh_running` `changed` 409,
  `invalid` 422, `bad_json` `bad_request` `bad_upload` 400, `too_large` 413, `unsupported_type` 415, `storage_error` `internal_error` 500.
- All API responses carry `Cache-Control: no-store`. Profile id is always `me`. Dates are `YYYY-MM-DD`; timestamps UTC ISO 8601.

## State
`GET /api/state` returns `{app_version, analyser_version, data_dir, step, cv, applications,
profile: {exists, confirmed, evidence_total, evidence_usable, has_languages},
jobs: {stored, open, last_fetched}, refresh: <see Jobs>}`. `step` is `cv | details | jobs | matches` (the step bar position).
`cv` is `{name, uploaded_at}` or null.

## Profile
Every profile response is `{profile: {id, confirmed, evidence: [{id, text, locator, state, context, scope}], languages,
locations, remote_regions, employment, search_titles, keywords, interests, known_gaps, verified_requirements, stage, enrolled,
recent_graduate, needs_sponsorship, experience_months, evidence_usable, ...}, cv}`.
- `POST /api/profile/cv` multipart, field `file` (.docx or .pdf). Extracts draft evidence (`locator` is the source line),
  sets `confirmed=false`, keeps manually added items. The same file again returns the stored profile unchanged.
- `POST /api/profile/new` `{"replace": false}`: empty profile. 409 `profile_exists` unless `replace` is true.
- `GET /api/profile`: 404 `no_profile` if none.
- `PUT /api/profile`: any of `languages` (`{"de": "B1"}`, CEFR A1 to C2, not empty), `locations`, `remote_regions`
  (country codes such as `DE`), `employment` (`full_time part_time internship working_student freelance contract temporary trainee`),
  `search_titles`, `keywords`, `interests`, `known_gaps`, `verified_requirements`, `stage`, `enrolled`, `recent_graduate`,
  `needs_sponsorship` (true/false/null), `experience_months`. Nothing is saved unless every field is valid; 422 returns
  `fields` such as `{"languages": "Use lowercase language codes and CEFR levels, for example de and B1."}`.
- `POST /api/profile/evidence` `{"action": "keep"|"edit"|"remove"|"add", "id": "cv-001", "text": "..."}`. `keep` turns an
  `inferred` item into `user_confirmed`; `edit` changes `text` and marks it `user_confirmed`; `remove` excludes it;
  `add` creates `me-001` with locator "Added by you". Only `cv_stated` and `user_confirmed` items count, and only once confirmed.
- `POST /api/profile/confirm` `{}`: 422 unless at least one usable item exists.
- `GET /api/families` (confirmed profile): `{families: [{id, label, direct, transferable, aliases, open_tasks}]}`.

## Jobs
- `POST /api/jobs/refresh` `{}`: starts a background read of the shipped reviewed boards (`career_discovery/boards.json`, 12 boards,
  the existing request bounds). Returns 200 with the status below; 409 `refresh_running` if already running.
- `GET /api/jobs/refresh`: `{status: idle|running|done|error, total, done, boards: [{ats, board, company, status:
  refreshed|cached|unavailable|budget|superseded, count?, reason?}], started_at, finished_at, public_gets, error}`.
  Poll about every second while `running`; `unavailable` rows carry a plain `reason`. Matching works on cached jobs.
- `POST /api/jobs/import` multipart `file` (CSV) or JSON `{"csv": "company,title,url\n...", "keep_description": false}`:
  `{imported, kept_description_fields}`. Columns as in README (`company,title,url` required).

## Matches
`GET /api/matches?mode=task|title|both&limit=50&excluded=0&hide_language_conflicts=0&q=` (profile must be confirmed, else 409).
`q` (at most 100 characters) keeps jobs whose title, company or places contain every word, ignoring case; it is applied
before `limit`, so it searches every stored job.
`task` is the evidence-based ranking, `title` the title and keyword comparison. `limit` 1 to 200 applies per lane.
`excluded=1` includes the `excluded` lane (hard conflicts). Response:
`{mode, corpus_vacancies, generated_at, query, counts: {task: {actionable, "verify first", excluded}}, shown: {task: {lane: n}},
results: {task: {actionable: [card], "verify first": [card]}, title: {...}}}`. `counts` ignores the filters; `shown`
counts each returned lane after `q` and the language filter, before `limit`.
Each card is the `as_record` output (job_key, company, title, url, apply_url, locations, workplace, employment, date, availability,
checked_at, verification_reason, lane, fit, families, findings, requirements, evidence_links with the CV line, growth) plus:
- `salary`: text such as `"€55,000 - €65,000 per year"`, or null (show "Pay not stated"). Only amounts next to a pay word.
- `age_days`: days since the listing date (Berlin), or null. `deadline`: `YYYY-MM-DD` or null.
- `language_summary`: `{languages: {"de": {asked: "B2"|null, yours: "B1"|null, state: met|unknown|conflict}}, conflict: bool}`.
- `wording`: `{supported: [{ad, cv, task, kind}], missing: [{ad, task, kind}]}`; `kind` is direct/transferable (supported) or
  partial/unverified/known_gap (missing). Label `missing` "Add to your application only if true". No text is generated.
- `application`: tracker status of this job or null.
`POST /api/matches/recheck` `{"job_key": "..."}`: the one place that visits the employer page (at most 8 requests). Returns
`{job_key, availability, checked_at, reason, public_gets, paid_api_spend}`. 422 for jobs not from a supported employer board.
`POST /api/feedback` `{job_key, verdict: "useful"|"not_for_me"|"new_to_me", reason?}` (or explicit `relevance`, `would_consider`,
`new_to_me` = yes|no|uncertain). `GET /api/feedback`: `{items: [...]}`.

## Applications
Row: `{job_key, company, title, url, status, applied_on, follow_up_on, notes, updated_at, follow_up_due}`.
Statuses: `saved applied interview offer rejected withdrawn`.
- `GET /api/applications`: `{items: [row]}`, newest first.
- `POST /api/applications` `{job_key, status, applied_on?, follow_up_on?, notes?}`: create or update; returns `{application: row}`.
  Applying without `applied_on` uses today (Berlin). `follow_up_on` defaults to 7 working days (Mon to Fri, no holidays) after
  `applied_on` and follows it if you change the date. 422 with `fields` for a bad status or date.
- `DELETE /api/applications?job_key=<url-encoded key>`: `{deleted: true}`.
- `GET /api/applications/export.csv`: UTF-8 with BOM, opens in Excel; cells that start with, or contain after `; , tab` or a newline, one of `= + - @` (and cells starting with tab or CR) get a `'` prefix.
- `GET /api/summary`: `{today, week_start, applied_this_week, follow_ups_due: [row], interviews: [row], new_matches,
  last_visit, first_visit, counts}`. `new_matches` counts task matches not seen at the last `POST /api/summary/seen` `{}`
  (call it after the user has looked at their matches).

## Your data
- `GET /api/export`: download JSON `{exported_at, profile, cv, feedback, applications, last_visit}` (attachment).
- `POST /api/data/delete` `{"confirm": "DELETE"}`: removes profile, feedback, applications, uploaded CV cache, search logs, visit
  markers and jobs imported from CSV. Jobs fetched from boards stay (public listings). Any other `confirm` is 422.
- `POST /api/shutdown` `{}`: replies `{stopping: true}` then stops the server.
