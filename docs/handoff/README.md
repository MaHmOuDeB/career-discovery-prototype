# Claude Code handoff

17 November 2026 · Europe/Berlin

## Paste into Claude Code

> Read CLAUDE.md and docs/handoff/README.md. Reproduce the current baseline with the offline tests and demo. Continue the local Germany pilot. Start by reproducing one specific gap that could explain the low discovery yield, using fictional profiles and permitted public vacancy material. Make a small improvement if the evidence supports it, add a regression case, and report the before and after results. Preserve the first supply observation and keep the owner’s CV and private state outside the session.

## Where the project stands

The owner approved the isolated CLI after the Phase 0 assessment. The implementation and two independent reviews are complete. The current code supports local PDF/DOCX intake and candidate review, evidence-linked discovery, title and keyword comparison, CSV and bounded public Greenhouse and Ashby ingestion, vacancy checks, feedback, export and deletion. A fictional-only semantic experiment exchanges reviewed proposals offline. The pilot is still collecting evidence for supply and usefulness.

| Check | Reviewed baseline |
| --- | --- |
| Offline suite | 63 passing tests at tag `baseline-2026-11-17`; 200 after the coverage-gap, catalogue, web-app and Codex B1 lanes (see below) |
| Fictional comparison | 96 profile–vacancy pairs. Task ranking found 12 relevant jobs in 18 filled actionable slots. Title ranking found 5 in 10. Treat these as designed checks with different denominators. |
| Frozen public challenge set | 26 cases. Five of 24 application paths corroborated at the time of the final check. Nineteen stayed unverified. Two expired controls stayed closed. |
| Private replay using provisional Berlin settings | Zero actionable in either mode on both samples. Task review first returned 0 in both. Title review first returned 6 among 26 cases and 129 among 1,298 listings. |
| First fictional supply observation | 12 boards and 1,181 listings yielded one plausible review case and zero actionable. The target was at least ten plausible openings across three employers and two role families in each observation. |
| Paid usage | $0 in paid API spend |

## Read as needed

| File | Purpose |
| --- | --- |
| [Project brief](project-brief.md) | Historical product requirements, Phase 0 questions and implementation constraints. The owner subsequently approved this isolated CLI. |
| [Decision log](../decisions.md) and [pilot protocol](../pilot.md) | Approved scope, trade-offs, review workflow and evaluation thresholds. |
| [Review 1](reviews/round-one.md), [first fixes](reviews/round-one-remediation.md), [review 2](reviews/round-two.md) | Seven first-round findings and five second-round findings with repros. Historical line numbers refer to the code at each review. [Combined code changes](reviews/review-changes.patch) records the source and test delta across both rounds. |
| [Final review and results](validation/Independent%20review%20and%20validation.md) | Resolution of both rounds and the final offline and public-vacancy results. |
| [Implementation report](validation/Implementation%20report.md), [follow-up validation](validation/Follow-up%20validation.md) and [benchmark report](validation/Benchmark%20validation.md) | Dated implementation and validation history. |
| [Blind vacancy review sheet](validation/Vacancy%20benchmark%20review%20sheet.md) and [blank ratings](validation/Vacancy%20benchmark%20ratings.json) | The 26 frozen, anonymous public vacancy IDs. Record ratings independently before using a private method key. |
| [First supply observation](first-supply-observation.json) and [reviewed public board list](supply-boards.json) | Carry the fictional supply starting point into the repeat comparison. |

## Open work

- **Engineering.** Done on 17 November 2026: the low-yield cause was reproduced and the parsing, vocabulary and language fixes were evaluated on a held-out fictional set. See [the diagnosis](diagnostics/2026-11-17-coverage-gap.md) and [the progress log](progress.md). Catalogue version 4 then added three tasks (`ANALYSER_VERSION` 15). Yield is still below the gate. Richer fictional profiles (`scripts/profile-yield.py`) showed profile evidence is not the main limit; location supply, out-of-profile titles, duty recognition on analyst, operations and support titles and the strict plausible rule are. `ANALYSER_VERSION` is 16. Next: a vocabulary lane for those titles with fresh held-out labels. The owner kept the plausible rules strict (see `docs/decisions.md`).
- **Repeat supply around 23 November 2026.** Use the same 12 public boards, fictional graduate constraints, catalogue and observation policy. Record successful scope, reasons for rejection, employer and role-family coverage, and link status. Keep any exploratory source or matching changes in a separate comparison. Run `scripts/repeat-supply.sh` on or after 23 November: it uses a worktree of the frozen baseline tag, then runs the current method as a separate read-only `coverage` diagnostic.
- **Human pilot.** The owner reviews and confirms the profile. Complete the 26 blind relevance and realism judgements, then audit explanation claims against the reviewed evidence. Run paired sessions with three to five consenting volunteers. Measure useful adjacent discoveries, time to find three viable jobs, link validity, explanation accuracy and observed reuse. Follow the consent and deletion workflow in the pilot protocol.

## Repeat the fictional supply observation

On the original machine, `.state/pilot` holds the fictional supply history and the originally enabled board list. The archive contains only selected public and aggregate records. To carry the first observation into a fresh checkout, seed it once in a new state directory from the project root.

```sh
python3 -B - <<'PY'
from pathlib import Path
from career_discovery.storage import Storage, read_json

baseline = read_json(Path("docs/handoff/first-supply-observation.json"))
assert baseline["scenario"] == "technical-graduate"
store = Storage(".state/fictional-supply-repeat")
try:
    if not any(item.get("observed_at") == baseline["observed_at"]
               and item["settings"] == baseline["settings"]
               for item in store.supply_history()):
        store.record_supply(baseline)
finally:
    store.close()
PY
```

Around the observation date, run the existing CLI against the reviewed board list.

```sh
python3 -B -m career_discovery --state .state/fictional-supply-repeat refresh docs/handoff/supply-boards.json
python3 -B -m career_discovery --state .state/fictional-supply-repeat supply
```

Check `comparison_ready` and the board scope. Same-day runs count as one observation. A changed source scope or method belongs in a separate diagnostic run unless the historical corpus can be reanalysed under the comparable settings.
