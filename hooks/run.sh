#!/usr/bin/env bash
# Launch an APM hook: `run.sh pretooluse` or `run.sh session_start`, with the event on stdin.
# If python is missing or fails (any exit but 0 or 2) inside an initialized APM project,
# a PreToolUse call is blocked (exit 2) instead of let through. SessionStart never blocks.
name="$1"
here="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
python "$here/../scripts/hook_$name.py"
code=$?
if [ "$code" -eq 0 ] || [ "$name" = "session_start" ]; then
  exit 0
fi
if [ "$code" -eq 2 ]; then
  exit 2
fi
top="$(git rev-parse --show-toplevel 2>/dev/null)"
common="$(git rev-parse --path-format=absolute --git-common-dir 2>/dev/null)"
main="${common%/*}"
for profile in "${top:+$top/.apm/profile.json}" "${common:+$main/.apm/profile.json}" \
  "${common:+$main/.apm/state/profile.json}"; do
  if [ -n "$profile" ] && [ -f "$profile" ]; then
    echo "APM guard: the hook could not run (python exited $code), so this call is blocked." \
      "Make python available on the hook's PATH." >&2
    exit 2
  fi
done
exit 0
