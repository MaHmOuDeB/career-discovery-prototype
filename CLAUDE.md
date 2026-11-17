# Career Discovery Prototype

This is a local Python CLI for the Germany pilot. It compares title and keyword search with vacancy matching based on evidence of the work a candidate has done. Start with [the handoff](docs/handoff/README.md) for the current state, original requirements, two review rounds and next steps. [README.md](README.md) documents the CLI. For work in progress, read [the progress log](docs/handoff/progress.md) and follow [the agent rules](docs/agent-rules.md). [AGENTS.md](AGENTS.md) gives Codex and other agents the same entry point.

## Baseline

Run from the project root with Python 3.14.

```sh
python3 -B -m unittest discover -s tests -q
python3 -B -m career_discovery demo
python3 -B -m career_discovery --help
```

The reviewed baseline (git tag `baseline-2026-11-17`) passed 63 offline tests; the current code passes 193. Run `scripts/gates.sh` for all offline gates. The demo exercises four fictional profiles against 24 fictional vacancies. PDF import uses a local Poppler installation for `pdftotext`. The demo and core CLI use the standard library.

## Code map

| Work | Entry points |
| --- | --- |
| CLI, profiles, evidence | `career_discovery/__main__.py`, `models.py`, `documents.py`, `word_xml.py` |
| Task parsing, eligibility, ranking | `career_discovery/analysis.py`, `eligibility.py`, `matching.py`, `catalog.json` |
| Public feeds and availability | `career_discovery/sources.py`, `network.py`, `sourcing.py`, `storage.py` |
| Blind review and metrics | `career_discovery/pilot.py`, `evaluation.py`, `docs/pilot.md` |

## Working rules

- Work in this isolated project. Treat the older personal Claude Code workflow, CVs, trackers, credentials and candidate state as outside this handoff.
- Use fictional profiles and temporary state for engineering checks. The owner's CV approval covered the previous private local test. Treat `.state/owner-pilot`, candidate-level exports and the private scoring key as out of scope for this session.
- Keep hard conflicts, unknowns and preferences distinct. Only reviewed CV-stated or user-confirmed evidence can support a personal claim. Weak task coverage stays in review. Use an exact vacancy URL and current, corroborated employer evidence for automatic verification.
- Keep defaults offline and paid API spend at zero. Preserve the bounds and source policies on public employer requests. Publication, deployment, paid services and volunteer outreach require separate owner authorization.
- Use the same frozen vacancy pool and clock when comparing ranks. Preserve the dated supply baseline. Changes to parsing require a new `ANALYSER_VERSION`. A changed matcher or supply policy needs a comparability check before interpreting repeat observations.

## Current status

Both independent review rounds and their fixes are complete. On 17 November 2026 the low-yield cause was reproduced and fixed in the analyser (`ANALYSER_VERSION` 14), then catalogue version 4 added `process_improvement`, `quality_compliance` and `customer_communication` (`ANALYSER_VERSION` 15). See [the diagnosis](docs/handoff/diagnostics/2026-11-17-coverage-gap.md). Mapped duties rose from 4.6% to 18.4%, but plausible listings stay at 2: the fictional profile's evidence now limits yield, so the next step needs an owner decision on richer fictional or consented profiles. A local web app (`python -m career_discovery app`, double-click starters, spec in `docs/web-app/`) wraps the same matcher for non-technical users. The repeat supply observation runs from the frozen baseline tag with `scripts/repeat-supply.sh` on or after 23 November. Keep `fixtures/heldout/` and `fixtures/heldout-v2/` out of tuning work.
