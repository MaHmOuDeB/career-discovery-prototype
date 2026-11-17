#!/bin/sh
# Repeat the fictional supply observation with the frozen baseline method (git tag baseline-2026-11-17).
# Network: bounded public GETs to the 12 reviewed employer boards only. Run on or after 2026-11-23 (Europe/Berlin).
# Usage: scripts/repeat-supply.sh [--force]
set -eu
root="$(cd "$(dirname "$0")/.." && pwd)"
tree="$root/.state/baseline-worktree"
state="$root/.state/fictional-supply-repeat"
out="$root/.state/repeat-supply"
earliest="2026-11-22T23:00:00Z"   # six days after the first observation, as capture_supply requires

if [ "${1:-}" != "--force" ] && [ "$(date -u +%Y-%m-%dT%H:%M:%SZ)" \< "$earliest" ]; then
  echo "Too early: the comparison needs six days after 2026-11-16 22:52 UTC. Run on or after 2026-11-23." >&2
  exit 2
fi

if [ ! -d "$tree" ]; then
  git -C "$root" worktree add --detach "$tree" baseline-2026-11-17
fi
mkdir -p "$out"
cd "$tree"

python3 -B - "$state" <<'PY'
import sys
from pathlib import Path
from career_discovery.storage import Storage, read_json

baseline = read_json(Path("docs/handoff/first-supply-observation.json"))
assert baseline["scenario"] == "technical-graduate"
store = Storage(sys.argv[1])
try:
    if not any(item.get("observed_at") == baseline["observed_at"] and item["settings"] == baseline["settings"]
               for item in store.supply_history()):
        store.record_supply(baseline)
finally:
    store.close()
PY

stamp="$(date -u +%Y%m%dT%H%M%SZ)"
python3 -B -m career_discovery --state "$state" refresh docs/handoff/supply-boards.json > "$out/refresh-$stamp.json"
python3 -B -m career_discovery --state "$state" supply > "$out/supply-baseline-method-$stamp.json"

# Diagnostic only: the current method on the same refreshed state. Read-only; it records no snapshot.
cd "$root"
if python3 -B -m career_discovery --help | grep -q coverage; then
  python3 -B -m career_discovery --state "$state" coverage > "$out/coverage-current-method-$stamp.json"
fi

python3 -B - "$out/supply-baseline-method-$stamp.json" <<'PY'
import json, sys
d = json.load(open(sys.argv[1]))
keys = ("corpus_jobs", "plausible", "actionable_count", "gate_met_this_snapshot", "comparison_ready",
        "new_since_previous", "repeat_since_previous", "both_snapshots_meet_gate")
print(json.dumps({k: d.get(k) for k in keys}, indent=1))
PY
echo "Full outputs: $out"
