# Web UI report (interface lane, 17 Nov 2026)

## Files (all under career_discovery/web/ unless noted)
- index.html (replaces placeholder; token meta, inline SVG sprite, header, step bar, language switch), app.css (one :root block, dark mode).
- js/util.js (i18n, DOM helper without innerHTML for data, API client with X-CD-Token, blob download), js/main.js (hash router, step bar),
  js/views-profile.js (CV, Details, Find jobs), js/views-work.js (Matches, My applications, Your data).
- i18n/en.json, i18n/de.json (265 keys each, identical sets and placeholders).
- tests/test_web_ui.py (5 tests: key sets equal, every data-i18n and t('key') exists in both files and no dynamic keys,
  no http(s) URL / inline script / style attribute / on* handler / .style / eval, referenced assets and JS imports exist, token meta present).

## Results
- RED first: tests failed with missing catalogues and no referenced assets. GREEN: `python3 -B -m unittest tests.test_web_ui -q` Ran 5, OK.
- `app --smoke --port 0 --state <temp>` prints OK. `node --check` on all JS files: no syntax errors.

## API gaps and guesses
1. Card `availability` values are not listed. UI treats values starting open/available/active/live/verified plus a `checked_at` as "Confirmed open"; otherwise shows the raw value as "Checked <date>: <value>".
2. No flag says whether Recheck is supported; the button always shows and a 422 message appears inline. Suggest `can_recheck` on the card.
3. `findings` and `evidence_links` shapes are undocumented. "Why it fits" uses `wording.supported` only; findings are shown via message/text/summary/reason/label and sorted into Conflicts when kind/type/severity contains "conflict".
4. `results.title` structure is shown as `{...}`; UI accepts an array or an object of arrays, and may not match.
5. `application` on a card: handled as a status string or an object with `status`.
6. `workplace` values assumed remote/hybrid/onsite; others are not shown. `locations` assumed strings (or objects with city/name/label).
7. Fit label comes from the lane (actionable, verify first, excluded), not from `fit`, whose values are not documented.
8. Language names in the details form are a fixed list of 14 codes; unknown codes already in the profile are kept.
9. Delete confirmation must be the English word DELETE in both languages (the API requires it); the German text says so.

## Not verified without a browser
Everything visual and interactive: layout at 320 px and 200% text, dark-mode contrast, keyboard order and focus ring, drag and drop,
file picker, progress polling, blob download filenames, the native confirm() dialogs, language switch persistence, and all live API
responses against real cards. Only static checks and the smoke start were run.
