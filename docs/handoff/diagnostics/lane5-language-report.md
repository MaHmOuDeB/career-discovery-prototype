# Lane 5 language requirements: DONE (L2 dropped by ruling)

Ruling applied: existing assertions kept; no inferred levels. Qualifier-only wording stays "unknown".

## Changes
- eligibility.py: OR lookahead gains besser/darüber (L1: "oder besser" no longer an alternative path).
  LANGUAGE_SIGNAL gains `\w+kenntnisse` (gute Deutschkenntnisse, Englischkenntnisse now yield a language finding).
  AND no longer splits after a hyphen, so "Deutsch- und Englischkenntnisse" names de and en (L4).
- analysis.py: LANGUAGE_TERM excludes Deutschland (L4). LANGUAGE_QUALIFIER gains muttersprach*; new STRONG_LANGUAGE
  (fluent/native/verhandlungssicher/fließend/muttersprach*). New plain_language_line: a non-bullet line naming a language
  with a CEFR level or strong qualifier, in an unclear section or before any heading, is mandatory unless OPTIONAL
  wording applies (L3). It also bypasses the two-word minimum. Skip and preferred sections unchanged (L3).
- L5: "Native-level German", "German (native)", "native German speaker" were already matched by `native`; tests confirm
  unknown finding and mandatory classification.
- tests/test_languages.py: 9 tests, written first (6 failed before the change).

## Notes
- "Deutsch- und Englischkenntnisse C1": C1 binds to the nearest language (en), de stays unknown (existing proximity rule).
- Bullets in unclear sections keep their old "unclear" kind. ANALYSER_VERSION not changed; controller must bump it.
- Fast checks: tests.test_languages, test_parsing, test_matching, test_vocabulary all pass (57 tests).
