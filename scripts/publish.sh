#!/usr/bin/env bash
# Step 3 of 3. Checks every staged package is signed by the DID that
# logos-repo.json trusts, uploads each as a release asset, rebuilds index.json
# and uploads it. Uses no secret key.
set -euo pipefail
cd "$(dirname "$0")/.."
LGX="${LGX:-lgx}"
INDEX_PY="${INDEX_PY:?set INDEX_PY to logos-modules-release-tool/index.py}"
REPO="${REPO:-roxanneen/basecamp-apps}"
DID="$(python3 -c 'import json; print(json.load(open("logos-repo.json"))["trustedSigners"][0]["did"])')"
case "$DID" in did:jwk:*) ;; *) echo "logos-repo.json has no publisher DID yet" >&2; exit 1;; esac

ring="$(mktemp -d)"; trap 'rm -rf "$ring"' EXIT
"$LGX" keyring add publisher "$DID" --dir "$ring" >/dev/null

shopt -s nullglob
: > staging/urls.txt
for f in staging/*.lgx; do
  base="$(basename "$f" .lgx)"; name="${base%-*}"; version="${base##*-}"
  signer="$("$LGX" signature "$f" | python3 -c 'import json,sys; d=sys.stdin.read(); print(json.loads(d)["did"] if d.strip() else "")')"
  [ "$signer" = "$DID" ] || { echo "$f is not signed by the catalogue's publisher key" >&2; exit 1; }
  "$LGX" verify "$f" --keyring-dir "$ring" | grep -q "Signer is trusted" || { echo "$f failed verification" >&2; exit 1; }
  tag="${name}-v${version}"
  gh release view "$tag" --repo "$REPO" >/dev/null 2>&1 || \
    gh release create "$tag" --repo "$REPO" --title "${name} ${version}" --latest=false \
      --notes "Signed multi-platform package for the catalogue (macOS Apple chip, Linux x86_64, Linux ARM64). Install it through the catalogue; see the README."
  gh release upload "$tag" "$f" --repo "$REPO" --clobber
  echo "https://github.com/${REPO}/releases/download/${tag}/${base}.lgx $f" >> staging/urls.txt
done

# Icons go beside the index, which is what release assets require.
rm -rf staging/index && mkdir -p staging/index
PATH="$(dirname "$(command -v "$LGX")"):$PATH" python3 "$INDEX_PY" build staging/urls.txt -o staging/index/index.json --icons-dir "" --fetch none
PATH="$(dirname "$(command -v "$LGX")"):$PATH" python3 "$INDEX_PY" validate staging/index/index.json
PATH="$(dirname "$(command -v "$LGX")"):$PATH" python3 "$INDEX_PY" validate-repo logos-repo.json

gh release view index --repo "$REPO" >/dev/null 2>&1 || \
  gh release create index --repo "$REPO" --title "Catalogue index" --latest=false \
    --notes "The catalogue's package listing and icons. Basecamp reads these; there is nothing here to download by hand."
gh release upload index staging/index/* --repo "$REPO" --clobber
echo "published. Catalogue address:"
echo "https://raw.githubusercontent.com/${REPO}/main/logos-repo.json"
