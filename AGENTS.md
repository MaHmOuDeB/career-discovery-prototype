# Agent instructions (Codex, Claude Code and other coding agents)

This file is the entry point for any coding agent. Claude Code reads CLAUDE.md, which says the same things.

0. Codex: the current task list and briefs are in [docs/handoff/codex-handover.md](docs/handoff/codex-handover.md).
1. Read [CLAUDE.md](CLAUDE.md) for the project, baseline commands, code map and working rules. They apply in full.
2. Read [docs/handoff/progress.md](docs/handoff/progress.md) next. It records the current lane, what is done, what is
   in progress and the exact next step. Resume from there; do not restart finished work.
3. Follow [docs/agent-rules.md](docs/agent-rules.md) when you change code: tests first, standard library only, no
   network by default, no private state.
4. Run `scripts/gates.sh` before you call a step done. It prints one line per gate; the full log is in
   `.state/gates/gates.log`.
5. After each finished step, update `docs/handoff/progress.md` (one short entry) and commit on the checked-out branch
   with a message that says what changed and why. Do not push, publish or contact anyone.

Key references: [coverage gap diagnosis](docs/handoff/diagnostics/2026-11-17-coverage-gap.md),
[task definitions](docs/task-definitions.md), [handoff](docs/handoff/README.md), [decisions](docs/decisions.md).

The supply baseline is frozen at git tag `baseline-2026-11-17`. The repeat supply observation around
23 November 2026 runs from a worktree of that tag (see progress.md), never from changed matcher code.
