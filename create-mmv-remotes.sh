#!/usr/bin/env bash
set -euo pipefail

# Create GitHub repos for all mmv-* directories in current folder.
# Usage:
#   ./create-mmv-remotes.sh            # private repos (default)
#   ./create-mmv-remotes.sh --public   # public repos
#   ./create-mmv-remotes.sh --private  # explicit private

VISIBILITY="private"
if [[ "${1:-}" == "--public" ]]; then
  VISIBILITY="public"
elif [[ "${1:-}" == "--private" || -z "${1:-}" ]]; then
  VISIBILITY="private"
else
  echo "Unknown option: ${1:-}"
  echo "Usage: $0 [--private|--public]"
  exit 1
fi

command -v gh >/dev/null 2>&1 || { echo "gh CLI is required."; exit 1; }

if ! gh auth status >/dev/null 2>&1; then
  echo "Not logged in to GitHub CLI."
  echo "Run: gh auth login -h github.com -p https -w"
  exit 1
fi

OWNER="$(gh api user -q .login)"
echo "Creating repos under owner: ${OWNER}"
echo "Visibility: ${VISIBILITY}"
echo

for d in mmv-*; do
  [[ -d "$d" ]] || continue
  repo="${OWNER}/${d}"

  if gh repo view "${repo}" >/dev/null 2>&1; then
    echo "exists: ${repo}"
    continue
  fi

  if [[ "${VISIBILITY}" == "public" ]]; then
    gh repo create "${repo}" --public
  else
    gh repo create "${repo}" --private
  fi
  echo "created: ${repo}"
done

echo
echo "Done."
