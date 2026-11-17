#!/bin/sh
# Offline gates. Writes a one-line-per-gate summary and a full log; prints the summary.
cd "$(dirname "$0")/.." || exit 2
out="${GATES_DIR:-.state/gates}"
mkdir -p "$out"
log="$out/gates.log"
summary="$out/summary.txt"
: > "$log"
: > "$summary"
status=0

gate() {
  name="$1"; shift
  printf '\n### %s\n' "$name" >> "$log"
  if "$@" >> "$log" 2>&1; then
    echo "PASS $name" >> "$summary"
  else
    echo "FAIL $name" >> "$summary"
    status=1
  fi
}

gate compile python3 -B -m compileall -q career_discovery tests
gate unit-tests python3 -B -X warn_default_encoding -W error::EncodingWarning -m unittest discover -s tests -q
gate demo python3 -B -m career_discovery demo
gate help python3 -B -m career_discovery --help
grep -E '^Ran [0-9]+ tests' "$log" | tail -n 1 >> "$summary"
cat "$summary"
exit $status
