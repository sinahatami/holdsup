#!/usr/bin/env bash
# Pre-commit guard: .env.example must never hold real secrets. Prints no values.
set -euo pipefail
f="${1:-.env.example}"
[ -f "$f" ] || exit 0
if grep -Eq '^[A-Z0-9_]*(API_KEY|TOKEN|SECRET|PASSWORD)=.+' "$f"; then
  echo "error: $f has a filled-in key/token/secret. Keep values empty there; put them in .env." >&2
  exit 1
fi
if grep -E '^DATABASE_URL=' "$f" | grep -Evq '@(localhost|127\.0\.0\.1|host)[:/]'; then
  echo "error: $f has a non-local DATABASE_URL. Use a localhost placeholder; real URLs go in .env." >&2
  exit 1
fi
