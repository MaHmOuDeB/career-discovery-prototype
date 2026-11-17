#!/bin/sh
# Offline lint and self-test of the starters. No network, nothing installed.
cd "$(dirname "$0")/.." || exit 2
status=0
bad() { echo "FAIL $1"; status=1; }

for f in start.sh "Start Career Discovery.command" scripts/starter-check.sh; do
  [ -f "$f" ] || { bad "missing $f"; continue; }
  sh -n "$f" || bad "sh -n $f"
  if command -v bash >/dev/null 2>&1; then bash -n "$f" || bad "bash -n $f"; fi
  [ -x "$f" ] || bad "not executable: $f"
  if grep -q "$(printf '\r')" "$f"; then bad "CR in $f"; fi
done

bat="Start Career Discovery.bat"
[ -f "$bat" ] || bad "missing $bat"
if [ -f "$bat" ]; then
  [ "$(grep -c "$(printf '\r')\$" "$bat")" -eq "$(wc -l < "$bat")" ] || bad "$bat is not all CRLF"
  for needle in "-m career_discovery app" "--no-project --python 3.12" "install.ps1"; do
    grep -q -e "$needle" "$bat" || bad "$bat lacks: $needle"
  done
fi

out=$(CD_DRY_RUN=1 CD_TEST_NO_PYTHON=1 CD_TEST_UV=/fake/uv sh start.sh) || bad "dry run uv path"
case "$out" in *"/fake/uv run --no-project --python 3.12 -- python -B -m career_discovery app"*) ;; *) bad "uv command not printed";; esac

[ "$status" -eq 0 ] && echo "PASS starter-check"
exit "$status"
