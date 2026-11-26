#!/usr/bin/env bash
# Step 1 of 3. Downloads each app's per-platform packages from its own release
# and merges them into one multi-platform package in staging/. Signs nothing.
set -euo pipefail
cd "$(dirname "$0")/.."
LGX="${LGX:-lgx}"
mkdir -p staging
grep -vE '^\s*(#|$)' packages.txt | while read -r repo tag name; do
  version="${tag#v}"
  out="staging/${name}-${version}.lgx"
  work="staging/.in-${name}-${version}"
  rm -rf "$work" "$out"; mkdir -p "$work"
  for p in darwin-arm64 linux-x86_64 linux-aarch64; do
    curl -fsSL -o "$work/${name}-${p}.lgx" "https://github.com/${repo}/releases/download/${tag}/${name}-${p}.lgx"
  done
  "$LGX" merge "$work"/*.lgx -o "$out" -y >/dev/null
  "$LGX" verify "$out" >/dev/null
  got="$(tar -xOf "$out" manifest.json | python3 -c 'import json,sys; m=json.load(sys.stdin); print(m["name"], m["version"])')"
  [ "$got" = "$name $version" ] || { echo "manifest says '$got', expected '$name $version'" >&2; exit 1; }
  rm -rf "$work"
  echo "prepared $out"
done
