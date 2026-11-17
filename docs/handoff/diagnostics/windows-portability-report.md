# Windows portability report

Full suite with `-X warn_default_encoding -W error::EncodingWarning`: 125 tests OK on macOS. Nothing was run on Windows.

## Changed
- `documents.py`: `pdf_segments` no longer uses `preexec_fn`/`resource`. It writes the PDF to a temp file, runs `pdftotext <file> -` with stdout piped, reads at most `MAX_TEXT + 1` bytes and kills the process if the cap is exceeded or a 12 s timer fires. Page cap (12) unchanged. The temp file is deleted in `finally`. Messages kept: cap or non-zero exit gives "within the limits"; timeout or OS error gives "did not complete".
- `storage.py` `write_private_json`: `os.replace` ran while the temp file was still open, which fails on Windows. The file is now closed before the replace; the temp file is removed on any failure.
- `__main__.py`: stdout/stderr are switched to UTF-8 when run as a script (Windows pipes default to cp1252).
- `demo.py`: three `read_text` calls now pass `encoding="utf-8"`.
- Tests: `encoding="utf-8"` on every text write/open and subprocess decode (test_cli, test_diagnostics, test_sourcing). CSV fixture written with `newline=""`.
- New tests: PDF cap exceeded, cap exactly met, timeout, normal output, extractor failure and missing Poppler (all mocked, no Poppler needed); `write_private_json` replace and no leftover temp file; POSIX permission test for state files.
- `.github/workflows/tests.yml`: ubuntu/macos/windows, Python 3.14, no `PYTHONUTF8`, no secrets.
- `README.md`: "### Windows" subsection and corrected privacy sentence.

## POSIX assumptions found
- `st_mode == 0o600` in test_cli flow: now guarded by `os.name != "nt"` in the flow; separate `skipIf(os.name == "nt")` test covers file, directory and sqlite modes. POSIX assertions unchanged.
- `resource.setrlimit` (fixed), open temp file replaced (fixed), cp1252 pipes (fixed).
- Not a problem: `/usr/bin/python3` fallback is gated on `sys.platform == "darwin"`; tests already use `sys.executable`; no symlink or "/" path-string tests found; sqlite is closed before temp dirs are removed. `argparse prog="python3 -m ..."` is cosmetic.

## Not verifiable without Windows
- `mkdir(mode=0o700)` and `os.open(..., 0o600)` are accepted but ignored; real privacy there depends on folder ACLs.
- Killing `pdftotext.exe` through `Popen.kill`, and a real Poppler run on Windows.
- Subprocess CLI tests under cp1252 defaults with the new UTF-8 reconfigure.
- CI will show whether the `unittest discover` import of `test_documents` from `test_cli` (path-based) behaves the same.
