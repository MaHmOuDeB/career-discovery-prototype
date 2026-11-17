# Lane 1 parsing report

Status: DONE. ANALYSER_VERSION, catalog.json, matching.py, __main__.py untouched (controller bumps the version).

## Changes
- `analysis.py`: `heading_kind` now tests both sides of " — ", " – ", " - " (prefix first, then suffix) (F3).
- `analysis.py` SECTIONS: new core, unclear and skip labels exactly as briefed (F2). Apostrophes normalise to a space,
  so "you ll" / "what you ll get" are the stored keys. Sentences without a colon do not become headings.
- `analysis.py`: `qualification_shaped` plus `QUALIFICATION_SHAPE` (experience/years/proficiency/knowledge/degree/
  background/familiarity and German equivalents after optional lead words, or a language with CEFR level or qualifier
  and no leading role verb). Inside a core section such a line is classified with the "unclear" rules: mandatory if
  MANDATORY wording or REQUIRED_QUALIFICATION (incl. a CEFR level), preferred if OPTIONAL, else unclear (F4).
- `eligibility.py`: a core requirement containing a CEFR level also gets `language_findings` (F4 defence in depth).
- `analysis.py` MANDATORY: added hard requirement(s), a must / is a must, essential, Pflicht, Voraussetzung (F5).
- New `tests/test_parsing.py` (9 tests, fictional text; failed first with 41 failures).

## Results
- `python3 -B -m unittest tests.test_parsing tests.test_matching -q`: 42 tests OK, no existing assertion edited.
- Listings with zero core duties in `.state/pilot`: 333 -> 253 of 1,181.
- Required case: "German proficiency at C2 - this is a hard requirement" yields ("language (de)", "conflict")
  for the B1 German demo profile under no heading, an unrecognised heading and a dash heading.

## Concerns
- "essential" and "Pflicht" in MANDATORY match anywhere, so a core duty such as "ensure essential reports are
  delivered" becomes a mandatory requirement. Precision of that word is unchecked on the corpus.
- Because a CEFR level in a qualification-shaped core line counts as REQUIRED_QUALIFICATION, "Fluent in German (C2)"
  becomes mandatory, not unclear, as the unclear-section rules dictate.
- Only the two touched test modules were run; the full suite and gates are the controller's.
