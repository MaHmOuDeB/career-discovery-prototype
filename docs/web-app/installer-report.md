# Installer lane report (17 Nov 2026)

Pick: "Download ZIP, double-click starter; installs Python via uv if missing."

## Files
- `start.sh` (Linux) and `Start Career Discovery.command` (macOS): same POSIX script, LF, executable bit set in the git index.
- `Start Career Discovery.bat` (Windows): CRLF, uses `py -3` then `python`, then uv.
- `scripts/starter-check.sh`: offline lint and self-test (sh -n, bash -n, line endings, markers, dry run).
- `.gitattributes`: bat CRLF, command and sh LF.
- README: new section "Use the app (no terminal needed)" after the Status line; Windows CLI subsection kept.
- `tests/test_starters.py`: 10 tests.

## Behaviour
Python 3.12+ check by running it; else uv (PATH, then `~/.local/bin/uv` or `%USERPROFILE%\.local\bin\uv.exe`) with
`uv run --no-project --python 3.12 -- python -B -m career_discovery app`; else two-sentence explanation, Enter prompt,
official uv installer, then the uv run. Errors keep the window open with a plain message and exit 1.
Choices beyond the brief: the installer runs with `UV_NO_MODIFY_PATH=1` so no shell profile or PATH is touched (the
starter finds uv by path); on macOS `/usr/bin/python3` is skipped when the Xcode tools are absent (avoids the install popup).
Test hooks: `CD_DRY_RUN=1` prints the chosen command and exits 0; `CD_TEST_NO_PYTHON`, `CD_TEST_NO_UV`, `CD_TEST_UV=<path>`.

## Results
- RED: `python3 -B -m unittest tests.test_starters -q` failed (7 failures, 3 errors) before the files existed.
- GREEN: same command, 10 tests OK (python3 3.14.7 on macOS). Dry run verified for Python, uv and install branches, and a folder with spaces.
- Not run: full suite, gates. Nothing committed; no network step executed.

## Not verified
- A real Windows run of the .bat (only reviewed by reading; the test checks CRLF and markers, not execution).
- macOS Gatekeeper and Windows SmartScreen first-open prompts; README wording is from spec, not observed.
- The real uv install and first-run download; the app start within 60 s without Python.
- ZIP downloads drop the executable bit on some unzip tools; the README says to double-click, and macOS Archive Utility keeps it. If not, `chmod +x` is needed.
