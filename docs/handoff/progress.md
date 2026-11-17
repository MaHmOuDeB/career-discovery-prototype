# Progress log

Newest entry first. Each entry: date, what is done, what is open, the exact next step.

## 2026-11-17 — catalogue lane complete (owner chose "add catalogue tasks")

Done
- Catalogue version 4: `process_improvement`, `quality_compliance`, `customer_communication`, five transfers,
  `stakeholders` reworded (`docs/task-definitions.md`). `ANALYSER_VERSION` 15. Report: `diagnostics/lane6-catalogue-report.md`.
- Second held-out set `fixtures/heldout-v2/` (24 ads, 157 duties), scored once on v14 before tuning.
- Language fixes found on v2: "native or C2" / "B2 or C1" stay one path, "jeweils/each at least B2" shares the level,
  markdown-bold headings are headings, bulleted CEFR language lines before any heading are mandatory.
- Per-task vetoes for look-alikes (code review, contract renewals, data quality, title-case benefit subheadings).
- Results in the diagnosis ("Results after the catalogue lane"): mapped duties 12.4% → 18.4%, v2 precision/recall
  0.931/0.129 → 0.938/0.215, v2 language conflicts 17 of 17. v1 precision on its own tasks unchanged at 0.897.
- 117 offline tests pass; demo output identical to the baseline.

Finding: plausible stays at 2. 168 of 176 listings without a hard conflict lack task evidence for the fictional
profile; the catalogue no longer limits yield. No listing became newly plausible, so no plausibility review was needed.

Open
1. Repeat supply observation on or after 23 November 2026: `scripts/repeat-supply.sh`. Record its summary here.
2. Owner decision: evaluate with richer fictional or consented profiles (the only remaining lever on yield).
3. Human pilot steps in the handoff need the owner and volunteers.

Next step: item 1 on or after 23 November; item 2 waits for the owner.

## 2026-11-17 — coverage-gap lane complete

Done (commits on the checked-out branch, after tag `baseline-2026-11-17`)
- Cause of the low yield reproduced and fixed in the analyser; `ANALYSER_VERSION` 14, catalogue unchanged at 3.
  Numbers, method and limits: [diagnostics/2026-11-17-coverage-gap.md](diagnostics/2026-11-17-coverage-gap.md).
  Per-lane agent reports sit next to it (`lane1` parsing, `lane3` diagnostics, `lane4` vocabulary, `lane5` languages,
  `lane-review` independent review).
- New: `coverage` and `heldout` CLI commands, `fixtures/heldout/` (24 independent labelled fictional ads),
  `scripts/gates.sh`, `scripts/repeat-supply.sh`, `AGENTS.md`, `docs/agent-rules.md`, `docs/task-definitions.md`.
- 110 offline tests pass; the demo output is identical to the baseline.

Independent review: 8 reproduced findings in `diagnostics/lane-review.md`, all fixed with tests (`ANALYSER_VERSION` 14).

Open
1. Repeat supply observation on or after 23 November 2026: run `scripts/repeat-supply.sh` (bounded public GETs to
   the 12 reviewed boards). It refuses to run earlier. Record its printed summary here and in the handoff.
2. Owner decision on yield (see "Why yield is still low" in the diagnosis): add catalogue tasks for unmapped duty
   themes such as process improvement and customer communication, or evaluate with richer fictional or consented
   profiles. Either change needs a catalogue version bump and a fresh held-out set or blind precision review.
3. Human pilot steps in the handoff are unchanged and need the owner and volunteers.

Rules that keep later results comparable
- Never tune on `fixtures/heldout/`. If it is used for development, write a new held-out set before claiming results.
- Compare analyser versions on the same frozen pool and clock: `coverage --at 2026-11-16T22:52:55+00:00` on
  `.state/pilot`, against a worktree of the baseline tag.

Next step: item 1 on or after 23 November; item 2 waits for the owner.
