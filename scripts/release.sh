#!/usr/bin/env bash
# The whole catalogue update in one command. Run it yourself, on the computer
# that holds the publisher key:
#
#   scripts/release.sh            bring every app to its newest release
#   scripts/release.sh --check    only say what is out of date; change nothing
#
# What it does, in order:
#   1. looks up each app's newest release and updates packages.txt
#   2. for a version the catalogue already has, fetches the signed package
#      back from the catalogue (it is not signed again)
#   3. for a new version, downloads the three per-platform packages, merges
#      them and signs the result with the publisher key (the only step that
#      uses the secret key)
#   4. checks every package is signed by the key logos-repo.json trusts,
#      uploads new packages, rebuilds and uploads the listing
#   5. for lines marked "attach", puts the signed package on the app's own
#      release as <package>.lgx and makes that release the app's latest
#   6. commits and pushes packages.txt
set -euo pipefail
cd "$(dirname "$0")/.."
REPO="${REPO:-roxanneen/basecamp-apps}"
KEY="${KEY:-thehat}"
SIGNER_NAME="${SIGNER_NAME:-thehat}"
SIGNER_URL="${SIGNER_URL:-https://github.com/${REPO}}"
CHECK_ONLY=0; [ "${1:-}" = "--check" ] && CHECK_ONLY=1

say() { printf '%s\n' "$*"; }
die() { printf 'error: %s\n' "$*" >&2; exit 1; }

# ---- tools (fetched once into tools/, which git ignores) --------------------
mkdir -p tools staging
if [ -z "${LGX:-}" ]; then
  [ -x tools/lgx-tool/bin/lgx ] || nix build github:logos-co/logos-package#lgx -o tools/lgx-tool
  LGX="$PWD/tools/lgx-tool/bin/lgx"
fi
if [ -z "${INDEX_PY:-}" ]; then
  [ -f tools/logos-modules-release-tool/index.py ] || \
    git clone -q --depth 1 https://github.com/logos-co/logos-modules-release-tool tools/logos-modules-release-tool
  INDEX_PY="$PWD/tools/logos-modules-release-tool/index.py"
fi
export PATH="$(dirname "$LGX"):$PATH"
command -v gh >/dev/null || die "the GitHub CLI (gh) is needed"

DID="$(python3 -c 'import json; print(json.load(open("logos-repo.json"))["trustedSigners"][0]["did"])')"
case "$DID" in did:jwk:*) ;; *) die "logos-repo.json has no publisher key";; esac

# ---- 1. newest release of each app ------------------------------------------
tmp="$(mktemp)"; behind=0
while IFS= read -r line <&3; do
  case "$line" in ''|'#'*) printf '%s\n' "$line" >> "$tmp"; continue;; esac
  read -r repo tag name attach <<< "$line"
  # Newest published release, pre-releases included: an app may publish a
  # version as a pre-release first and let step 5 make it the latest once the
  # signed package is attached.
  latest="$(gh api "repos/${repo}/releases?per_page=20" --jq '[.[] | select(.draft | not)][0].tag_name // empty')"
  [ -n "$latest" ] || die "cannot read the newest release of ${repo}"
  if [ "$latest" != "$tag" ]; then
    say "${name}: ${tag} -> ${latest}"; behind=1; tag="$latest"
  fi
  printf '%s\n' "${repo} ${tag} ${name}${attach:+ ${attach}}" >> "$tmp"
done 3< packages.txt
if [ "$CHECK_ONLY" = 1 ]; then
  rm -f "$tmp"
  [ "$behind" = 0 ] && say "the catalogue is up to date" || say "the catalogue is behind; run scripts/release.sh"
  exit "$behind"
fi
mv "$tmp" packages.txt

# ---- 2 and 3. one signed package per app in staging/ ------------------------
rm -f staging/*.lgx staging/urls.txt
signed_new=0
while read -r repo tag name attach <&3; do
  version="${tag#v}"; out="staging/${name}-${version}.lgx"; cat_tag="${name}-v${version}"
  if gh release view "$cat_tag" --repo "$REPO" >/dev/null 2>&1 && \
     gh release download "$cat_tag" --repo "$REPO" --pattern "${name}-${version}.lgx" --dir staging --clobber 2>/dev/null; then
    say "${name} ${version}: already in the catalogue"
  else
    work="staging/.in-${name}-${version}"; rm -rf "$work"; mkdir -p "$work"
    for p in darwin-arm64 linux-x86_64 linux-aarch64; do
      curl -fsSL -o "$work/${name}-${p}.lgx" "https://github.com/${repo}/releases/download/${tag}/${name}-${p}.lgx" \
        || die "${repo} ${tag} has no ${name}-${p}.lgx yet (is its release build still running?)"
    done
    "$LGX" merge "$work"/*.lgx -o "$out" -y >/dev/null
    rm -rf "$work"
    got="$(tar -xOf "$out" manifest.json | python3 -c 'import json,sys; m=json.load(sys.stdin); print(m["name"], m["version"])')"
    [ "$got" = "$name $version" ] || die "${out}: manifest says '${got}', expected '${name} ${version}'"
    "$LGX" sign "$out" --key "$KEY" --name "$SIGNER_NAME" --url "$SIGNER_URL" >/dev/null
    say "${name} ${version}: merged and signed"; signed_new=1
  fi
done 3< <(grep -vE '^\s*(#|$)' packages.txt)

# ---- 4. verify, upload, rebuild the listing ---------------------------------
ring="$(mktemp -d)"; trap 'rm -rf "$ring"' EXIT
"$LGX" keyring add publisher "$DID" --dir "$ring" >/dev/null
while read -r repo tag name attach <&3; do
  version="${tag#v}"; f="staging/${name}-${version}.lgx"; cat_tag="${name}-v${version}"
  signer="$("$LGX" signature "$f" | python3 -c 'import json,sys; d=sys.stdin.read(); print(json.loads(d)["did"] if d.strip() else "")')"
  [ "$signer" = "$DID" ] || die "${f} is not signed by the catalogue's publisher key"
  "$LGX" verify "$f" --keyring-dir "$ring" | grep -q "Signer is trusted" || die "${f} failed verification"
  if ! gh release view "$cat_tag" --repo "$REPO" >/dev/null 2>&1; then
    gh release create "$cat_tag" --repo "$REPO" --title "${name} ${version}" --latest=false \
      --notes "Signed multi-platform package for the catalogue (macOS Apple chip, Linux x86_64, Linux ARM64). Install it through the catalogue; see the README." >/dev/null
    gh release upload "$cat_tag" "$f" --repo "$REPO" >/dev/null
    say "${name} ${version}: uploaded to the catalogue"
  fi
  echo "https://github.com/${REPO}/releases/download/${cat_tag}/${name}-${version}.lgx $PWD/$f" >> staging/urls.txt
done 3< <(grep -vE '^\s*(#|$)' packages.txt)

rm -rf staging/index && mkdir -p staging/index
python3 "$INDEX_PY" build staging/urls.txt -o staging/index/index.json --icons-dir "" --fetch none >/dev/null
python3 "$INDEX_PY" validate staging/index/index.json --full --pairs-file staging/urls.txt --fetch none
python3 "$INDEX_PY" validate-repo logos-repo.json
gh release view index --repo "$REPO" >/dev/null 2>&1 || \
  gh release create index --repo "$REPO" --title "Catalogue index" --latest=false \
    --notes "The catalogue's package listing and icons. Basecamp reads these; there is nothing here to download by hand." >/dev/null
gh release upload index staging/index/* --repo "$REPO" --clobber >/dev/null
say "listing published"

# ---- 5. signed copy on the app's own release --------------------------------
while read -r repo tag name attach <&3; do
  [ "${attach:-}" = "attach" ] || continue
  version="${tag#v}"; f="staging/${name}-${version}.lgx"
  cp "$f" "staging/${name}.lgx"
  ( cd staging && shasum -a 256 "${name}.lgx" > "${name}.lgx.sha256" )
  gh release upload "$tag" "staging/${name}.lgx" "staging/${name}.lgx.sha256" --repo "$repo" --clobber >/dev/null
  rm -f "staging/${name}.lgx" "staging/${name}.lgx.sha256"
  gh release edit "$tag" --repo "$repo" --prerelease=false --latest >/dev/null
  say "${name} ${version}: signed package attached to ${repo} ${tag}, now its latest release"
done 3< <(grep -vE '^\s*(#|$)' packages.txt)

# ---- 6. record what the catalogue now holds ---------------------------------
if ! git diff --quiet -- packages.txt; then
  git add packages.txt
  git commit -q -m "Catalogue: $(grep -vE '^\s*(#|$)' packages.txt | awk '{printf "%s%s %s", (NR>1?", ":""), $3, $2}')"
  git push -q
  say "packages.txt committed and pushed"
fi
say "done. Catalogue address: https://raw.githubusercontent.com/${REPO}/main/logos-repo.json"
