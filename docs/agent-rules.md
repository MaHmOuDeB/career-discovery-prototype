# Rules for agents working on this project

Read CLAUDE.md first. These rules add to it.

- Folder: the project root. Branch: the one checked out. Do not create branches, commit, push or tag. The controller commits.
- Python 3.14, standard library only. No network calls, no paid APIs, no new dependencies.
- Never read or write `.state/owner-pilot`, candidate exports, private scoring keys or anything outside this project.
  `.state/pilot` (fictional scenario over public vacancies) may be read locally for diagnostics. Never copy vacancy
  descriptions out of it into tracked files, tests or reports. Aggregate counts and your own paraphrased examples are fine.
- Tests first: write or extend a test, see it fail, then change the code. Never weaken or delete an existing assertion
  unless your brief says so; if an old test conflicts with a fix, stop and report it.
- Run only fast checks: `python3 -B -m unittest tests.<module> -q` for modules you touched. Do not run the full suite or
  the demo repeatedly, and never sleep, poll or wait. The controller runs `scripts/gates.sh`.
- Parsing or catalogue changes: the controller sets `ANALYSER_VERSION` and the catalogue `version`; do not change them
  unless your brief says so.
- Keep the code style: small functions, compiled regexes at module level, no comments that narrate the change.
- Final message: at most 5 lines (status DONE/BLOCKED, files changed, one line of test results, concerns).
  Details go to the report file named in your brief, at most 40 lines.
