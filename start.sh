#!/bin/sh
# Career Discovery starter for macOS and Linux. Needs no admin rights.
# CD_DRY_RUN=1 prints the command that would run and exits.

dry="${CD_DRY_RUN:-}"

pause_close() {
  if [ -z "$dry" ] && [ -t 0 ]; then
    printf 'Press Enter to close this window. '
    read -r _unused
  fi
}

fail() {
  printf '\nSomething went wrong: %s\n' "$1"
  printf 'Next step: %s\n' "$2"
  pause_close
  exit 1
}

cd "$(dirname "$0")" || fail "The starter could not open its own folder." "Unzip the download again and double-click the starter inside the unzipped folder."

is_python_ok() {
  "$1" -c 'import sys; sys.exit(0 if sys.version_info >= (3, 12) else 1)' >/dev/null 2>&1
}

find_python() {
  [ -n "${CD_TEST_NO_PYTHON:-}" ] && return 1
  for name in python3 python; do
    found=$(command -v "$name" 2>/dev/null) || continue
    if [ "$found" = /usr/bin/python3 ] && [ "$(uname)" = Darwin ] && ! xcode-select -p >/dev/null 2>&1; then
      continue
    fi
    if is_python_ok "$found"; then
      PY="$found"
      return 0
    fi
  done
  return 1
}

find_uv() {
  [ -n "${CD_TEST_NO_UV:-}" ] && return 1
  if [ -n "${CD_TEST_UV:-}" ]; then
    UV="$CD_TEST_UV"
    return 0
  fi
  for candidate in "$(command -v uv 2>/dev/null)" "$HOME/.local/bin/uv"; do
    if [ -n "$candidate" ] && [ -x "$candidate" ]; then
      UV="$candidate"
      return 0
    fi
  done
  return 1
}

install_uv() {
  echo "Career Discovery needs Python, and it is not installed on this computer."
  echo "This starter can install the free uv tool from astral.sh, which then downloads Python into your own folder. No admin rights are needed."
  if [ -n "$dry" ]; then
    echo "DRY RUN: would ask, then run: curl -LsSf https://astral.sh/uv/install.sh | sh"
    echo "Press Enter to continue or close this window to cancel"
    exit 0
  fi
  printf 'Press Enter to continue or close this window to cancel. '
  read -r _unused
  command -v curl >/dev/null 2>&1 || fail "The download tool curl is missing." "Install Python 3.12 or newer from python.org, then double-click this starter again."
  UV_NO_MODIFY_PATH=1 curl -LsSf https://astral.sh/uv/install.sh | UV_NO_MODIFY_PATH=1 sh || fail "The uv installer did not finish." "Check your internet connection and try again, or install Python 3.12 or newer from python.org."
  find_uv || fail "uv was installed but could not be found." "Close this window and double-click the starter again."
}

run_app() {
  if [ -n "$dry" ]; then
    echo "DRY RUN in $(pwd): $*"
    exit 0
  fi
  "$@"
  code=$?
  if [ "$code" -ne 0 ]; then
    fail "The app stopped with an error (code $code)." "Read the message above. If the port or a file is in use, close other copies of the app and try again."
  fi
  exit 0
}

if find_python; then
  run_app "$PY" -B -m career_discovery app
fi
find_uv || install_uv
run_app "$UV" run --no-project --python 3.12 -- python -B -m career_discovery app
