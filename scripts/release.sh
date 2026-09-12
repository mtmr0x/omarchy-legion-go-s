#!/bin/bash
# Tag a version and push it. Run through `make release`.
#
# Shows the latest version on GitHub, asks for the new one, then asks for the
# release notes, which become the annotated tag message. Pushing the tag triggers
# .github/workflows/release.yml, which publishes the GitHub release from that
# message. Only git is needed locally.
set -euo pipefail

cd "$(dirname "${BASH_SOURCE[0]}")/.."

info() { printf '\033[1;34m::\033[0m %s\n' "$*"; }
warn() { printf '\033[1;33m!!\033[0m %s\n' "$*"; }
ok()   { printf '\033[1;32m ok\033[0m %s\n' "$*"; }
die()  { printf '\033[1;31m!!\033[0m %s\n' "$*" >&2; exit 1; }

BRANCH=main

# --------------------------------------------------------------- preflight

for tool in git gum; do
  command -v "$tool" >/dev/null || die "$tool is not installed"
done

[[ -z "$(git status --porcelain)" ]] || die "working tree has uncommitted changes, commit or stash them first"

current="$(git branch --show-current)"
[[ "$current" == "$BRANCH" ]] || die "releases are cut from $BRANCH, you are on ${current:-a detached HEAD}"

[[ -e .github/workflows/release.yml ]] || die ".github/workflows/release.yml is missing, GitHub would not publish the release"

info "Checking GitHub"
git fetch origin "$BRANCH" --tags --quiet

behind="$(git rev-list --count "HEAD..origin/$BRANCH")"
ahead="$(git rev-list --count "origin/$BRANCH..HEAD")"
(( behind == 0 )) || die "$BRANCH is $behind commit(s) behind origin, pull first"
if (( ahead > 0 )); then
  warn "$BRANCH has $ahead commit(s) that are not on GitHub yet"
  gum confirm "Push $BRANCH before releasing?" || die "aborted, the release has to point at a pushed commit"
  git push origin "$BRANCH"
fi

# --------------------------------------------------------------- version

latest="$(git ls-remote --tags --refs origin 'v*' \
  | sed 's#.*refs/tags/##' \
  | grep -E '^v[0-9]+\.[0-9]+\.[0-9]+$' \
  | sort -V | tail -n 1 || true)"

if [[ -n "$latest" ]]; then
  IFS=. read -r major minor patch <<<"${latest#v}"
  suggested="v$major.$minor.$((patch + 1))"
  ok "latest version on GitHub: $latest"
else
  suggested="v0.1.0"
  ok "no version on GitHub yet"
fi

while true; do
  version="$(gum input \
    --header "New version (latest on GitHub: ${latest:-none})" \
    --placeholder "$suggested" \
    --value "$suggested")"
  [[ -n "$version" ]] || die "aborted, no version given"
  [[ "$version" == v* ]] || version="v$version"

  if ! [[ "$version" =~ ^v[0-9]+\.[0-9]+\.[0-9]+$ ]]; then
    warn "$version is not in the form v1.2.3"
  elif git rev-parse -q --verify "refs/tags/$version" >/dev/null; then
    warn "$version already exists"
  elif [[ -n "$latest" && "$(printf '%s\n' "$latest" "$version" | sort -V | tail -n 1)" != "$version" ]]; then
    warn "$version is not newer than $latest"
  else
    break
  fi
done

# --------------------------------------------------------------- notes

# Pre-fill with the commits since the last release, as a starting point.
if [[ -n "$latest" ]] && git rev-parse -q --verify "refs/tags/$latest" >/dev/null; then
  changes="$(git log --pretty='- %s' "$latest..HEAD")"
else
  changes="$(git log --pretty='- %s')"
fi

notes="$(gum write \
  --header "Release notes for $version (markdown, ctrl+d to finish, esc to cancel)" \
  --width 80 --height 15 \
  --value "$changes")"
[[ -n "${notes//[[:space:]]/}" ]] || die "aborted, the release notes are empty"

notes_file="$(mktemp)"
trap 'rm -f "$notes_file"' EXIT
printf '%s\n' "$notes" >"$notes_file"

# --------------------------------------------------------------- confirm

commit="$(git rev-parse --short HEAD)"
echo
info "$version at $commit ($(git log -1 --pretty=%s))"
echo
sed 's/^/   /' "$notes_file"
echo
gum confirm "Create tag $version and push it?" || die "aborted, nothing was created"

# --------------------------------------------------------------- publish

# verbatim keeps markdown headings, which would otherwise be stripped as comments.
git tag --annotate "$version" --file "$notes_file" --cleanup=verbatim
ok "tag $version created"

if ! git push origin "refs/tags/$version"; then
  git tag --delete "$version" >/dev/null
  die "could not push the tag, removed it locally so you can try again"
fi
ok "tag $version pushed"

url="$(git remote get-url origin)"
repo="${url#git@github.com:}"
repo="${repo#https://github.com/}"
repo="${repo%.git}"
echo
info "GitHub Actions is publishing the release, usually within a minute:"
echo "   progress  https://github.com/$repo/actions"
echo "   release   https://github.com/$repo/releases/tag/$version"
