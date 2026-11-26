#!/usr/bin/env bash
# Step 2 of 3. Signs every package in staging/ with the publisher key.
# Run this yourself: it is the only step that uses the secret key, which
# stays in ~/.config/logos/keys/ and is never printed or copied.
set -euo pipefail
cd "$(dirname "$0")/.."
LGX="${LGX:-lgx}"
KEY="${KEY:-thehat}"
NAME="${SIGNER_NAME:-thehat}"
URL="${SIGNER_URL:-https://github.com/roxanneen/basecamp-apps}"
shopt -s nullglob
files=(staging/*.lgx)
[ ${#files[@]} -gt 0 ] || { echo "nothing in staging/; run scripts/prepare.sh first" >&2; exit 1; }
for f in "${files[@]}"; do
  "$LGX" sign "$f" --key "$KEY" --name "$NAME" --url "$URL" >/dev/null
  echo "signed $f"
done
echo "done: ${#files[@]} package(s) signed as \"$NAME\""
