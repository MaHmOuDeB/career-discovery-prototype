# Lane review: baseline-2026-11-17..HEAD (analysis, eligibility, diagnostics, CLI)

All outputs are actual runs on fictional text (demo technical-graduate profile, de B1). `T(s, ev)` = `task_tags(s, load_catalogue(), evidence=ev)`; `E(desc)` = analyse_description + eligibility, language findings only (scratch script, not in the repo). "New" = baseline returned nothing or something different.

1. HIGH, evidence overclaims (new). The new task patterns credit the candidate with tasks the text does not show.
   `T('Colleagues resolve tickets while I observe', True)` -> ('troubleshoot',); same for 'Managers handle escalations; I watched', 'Applied for a role handling tickets', 'Enrolled in a course on handling tickets', 'Wrote about incident post-mortems', 'Studied how to fix bugs in a lecture'.
   `T('Provided with training sessions', True)` -> ('teach',) (received); 'Seminar on running training sessions' -> teach; 'Wanted to run training sessions' -> teach (INTENT_ONLY has "want to", not "wanted to"); 'Hold a course certificate' -> teach. Baseline () for all.
   Fix: for evidence=True block plural/role subjects before the verb, add wanted/applied/enrolled/studied/seminar/"on|about" guards, and drop bare "hold" and "course(s)" from teach.

2. HIGH, false hard language conflicts from core duties (new: core lines with a CEFR token now go through language_findings, no negation or audience check).
   `E('Responsibilities\n- Teach German to C1 learners in small groups')` -> ['conflict'] (baseline []). `E('Responsibilities\n- Review contracts, no German C2 needed')` -> ['conflict']. `E('Responsibilities\n- Document defects found in the Level C1 firmware in German')` -> ['conflict'].
   Fix: for core lines emit a language finding only when the line states a candidate requirement and has no NEGATION/NO_LANGUAGE; otherwise unknown.

3. HIGH, missed language conflict on short lines under the new duty headings. plain_language_line only fires for section "" or "unclear", but "Your role", "You will", "Deine Rolle" now open a core section and lines under 3 words are dropped.
   `E('Your Role\nGerman: C2')` -> [] ; `E('Your Role\nGerman C1')` -> [] ; `E('You will\nGerman: C1')` -> [] (add "required" and it gives ['conflict']). Baseline also [] for "Your Role" (not a heading then), but the new headings make this path common.
   Fix: allow section "core" in plain_language_line and in the short-line exemption.

4. MEDIUM, job-side look-alikes: benefits and other actors now yield tasks (new, evidence=False). `T('We provide training sessions and workshops for you')`, `T('Wir bieten dir Schulungen und Trainings an')`, `T('Wir halten regelmäßig Seminare ab')`, `T('Our managers hold training sessions for new hires')` -> teach; `T('Our support team resolves tickets and you escalate edge cases')`, `T('Engineers fix bugs while you document requirements')` -> troubleshoot. End to end: `analyse_description('Your Role\n- Wir bieten dir Schulungen und Trainings an')` -> [('core', ('teach',))].
   Fix: extend OTHER_ACTOR with wir/we/our/team/manager/engineers subjects and "für dich|for you|dir" recipients.

5. MEDIUM, qualifications filed as core duties in German duty sections (new SECTION_DUTY: `du \w+st`, `\w+ung`). After "Deine Aufgaben": 'Du kennst dich mit SQL aus' -> ('core', ('sql',)); 'Du beherrschst Excel und Python' -> core spreadsheets; 'Berufserfahrung in der Analyse von Daten' -> core data_analysis; 'Ausbildung oder Studium in der Wirtschaft' -> core. Baseline all []. Inflates duty coverage and task credit.
   Fix: exclude kennen/beherrschen/denken and Erfahrung/Ausbildung/Studium/Berufserfahrung/Kenntnisse from SECTION_DUTY.

6. MEDIUM, real duties demoted to "unclear" by qualification_shaped (new; `match` from line start). Under "Responsibilities": '- Background checks on new vendors', '- Knowledge transfer sessions for new hires', '- Experience reports are compiled for customers', '- Erfahrungsberichte erstellen und Dokumentation pflegen' (carries document_process) all -> unclear (baseline core).
   Fix: require the shape word to be followed by with/in/of/mit/im or end of line.

7. LOW, pre-existing, still a missed conflict: `E('Requirements\n- German and English C1')` -> English only, German silently dropped; same for 'Deutsch und Englisch auf C1-Niveau'. SHARED_LEVEL covers only the hyphen form.

8. LOW, `python3 -B -m career_discovery coverage --titles '('` -> uncaught re.PatternError traceback (not in main's except tuple). Fix: compile inside try and raise ValueError.

Checked, no finding: coverage/heldout never write (sha1 of vacancies.sqlite and directory listing unchanged; a missing state dir is not created). coverage prints counts only; heldout prints text only from the supplied fictional file. Performance: 800-char adversarial lines (repeated verbs, long `\w*daten\w*` chains, hyphen runs, SECTION_DUTY, QUALIFICATION_SHAPE) took under 10 ms in task_tags and analyse_description, no cliff. Qualifier-only wording still infers no level. Location, employment, enrolment and deadline code paths are unchanged by the diff.

## Fixes

All eight findings fixed tests first (tests/test_vocabulary, test_languages, test_parsing, test_diagnostics). `ANALYSER_VERSION`, catalog.json and matching.py untouched.

1. analysis.py `task_is_asserted`: evidence blocks plural/role subjects (not after with/alongside/and/to/for/by) and extra intent guards; hold/held dropped from RUN_VERBS. "Delivered training sessions to staff", "Resolved escalated tickets", "Worked with engineers to fix bugs" stay positive.
2. eligibility.py: core-line language findings are downgraded conflict -> unknown, skipped on NEGATION/NO_LANGUAGE. Changed existing test `test_core_requirement_with_explicit_level_gets_language_findings`: it asserted "conflict" for a direct core Requirement, which ruling 2 forbids; it now asserts unknown and no conflict. The F4 test (hard requirement under odd headings) still gives conflict.
3. `plain_language_line` accepts section "core" (not when the line has a ROLE_VERB), so "Your Role\nGerman: C2" is mandatory.
4. Job side: we/wir/our/unser*/engineers/managers/colleagues/the team prefix blocks unless you/your/someone/candidate/du/dein* is present; "for you/für dich/für Sie/dir" right after the hit blocks.
5. SECTION_DUTY excludes du kennst/beherrschst/denkst/weißt and Erfahrung/Berufserfahrung/Ausbildung/Studium/Kenntnis* openers.
6. QUALIFICATION_SHAPE needs a following with/in/of/on/using/across/mit/im/in der/als/oder/der/von/an, comma, colon, "(of) experience" or line end; Berufserfahrung added.
7. eligibility.py `and_split` keeps two bare language terms together; German gets unknown in "German and English C1".
8. coverage_report raises ValueError on a bad --titles regex; CLI exits 2 with "Error:" and no traceback.
Open: "Teach German to C1 learners" is still classified mandatory (qualification path, "teach" is not in ROLE_VERB). It is a qualification-parse gap, not covered by the rulings.
