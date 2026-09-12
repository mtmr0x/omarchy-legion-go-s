#!/bin/bash
# Create an annotated version tag locally. Run through `make release`.
#
# Lists the last 10 versions, asks for the new one, then asks for the message,
# which is stored in the tag so it can be pasted into the GitHub release. Nothing
# is pushed: push the tag and publish the release yourself.
set -euo pipefail

cd "$(dirname "${BASH_SOURCE[0]}")/.."

info() { printf '\033[1;34m::\033[0m %s\n' "$*"; }
warn() { printf '\033[1;33m!!\033[0m %s\n' "$*"; }
ok()   { printf '\033[1;32m ok\033[0m %s\n' "$*"; }
die()  { printf '\033[1;31m!!\033[0m %s\n' "$*" >&2; exit 1; }

SEMVER='^v[0-9]+\.[0-9]+\.[0-9]+$'

for tool in git gum; do
  command -v "$tool" >/dev/null || die "$tool is not installed"
done

if [[ -n "$(git status --porcelain)" ]]; then
  warn "you have uncommitted changes, they will not be part of the tag"
fi

# --------------------------------------------------------------- versions

# Read-only look at GitHub, so versions tagged elsewhere show up too. Works
# offline, just without them.
remote_tags="$(git ls-remote --tags --refs origin 'v*' 2>/dev/null | sed 's#.*refs/tags/##' || true)"
local_tags="$(git tag --list 'v*')"

recent="$(printf '%s\n%s\n' "$remote_tags" "$local_tags" | grep -E "$SEMVER" | sort -V -u | tail -n 10 || true)"
latest="$(tail -n 1 <<<"$recent")"

echo
if [[ -n "$recent" ]]; then
  info "Last versions (newest last)"
  while read -r tag; do
    if grep -qxF "$tag" <<<"$remote_tags"; then
      echo "   $tag"
    else
      echo "   $tag   (local only, not pushed)"
    fi
  done <<<"$recent"
  IFS=. read -r major minor patch <<<"${latest#v}"
  suggested="v$major.$minor.$((patch + 1))"
else
  info "No versions yet"
  suggested="v0.1.0"
fi
echo

while true; do
  version="$(gum input \
    --header "New version (latest: ${latest:-none})" \
    --placeholder "$suggested" \
    --value="$suggested")"
  [[ -n "$version" ]] || die "aborted, no version given"
  [[ "$version" == v* ]] || version="v$version"

  if ! [[ "$version" =~ $SEMVER ]]; then
    warn "$version is not in the form v1.2.3"
  elif git rev-parse -q --verify "refs/tags/$version" >/dev/null || grep -qxF "$version" <<<"$remote_tags"; then
    warn "$version already exists"
  elif [[ -n "$latest" && "$(printf '%s\n' "$latest" "$version" | sort -V | tail -n 1)" != "$version" ]]; then
    warn "$version is not newer than $latest"
  else
    break
  fi
done

# --------------------------------------------------------------- message

# Pre-fill with the commits since the last version, as a starting point.
if [[ -n "$latest" ]] && git rev-parse -q --verify "refs/tags/$latest" >/dev/null; then
  changes="$(git log --pretty='- %s' "$latest..HEAD")"
else
  changes="$(git log --pretty='- %s')"
fi

message="$(gum write \
  --header "Message for $version (enter to finish, ctrl+j new line, ctrl+e editor, esc cancel)" \
  --width 80 --height 15 \
  --value="$changes")"
[[ -n "${message//[[:space:]]/}" ]] || die "aborted, the message is empty"

message_file="$(mktemp)"
trap 'rm -f "$message_file"' EXIT
printf '%s\n' "$message" >"$message_file"

# --------------------------------------------------------------- tag

echo
info "$version at $(git rev-parse --short HEAD) ($(git log -1 --pretty=%s))"
echo
sed 's/^/   /' "$message_file"
echo
gum confirm "Create tag $version?" || die "aborted, nothing was created"

# verbatim keeps markdown headings, which would otherwise be stripped as comments.
git tag --annotate "$version" --file "$message_file" --cleanup=verbatim
ok "tag $version created locally"

echo
echo "   push it       git push origin $version"
echo "   copy message  git tag --list --format='%(contents)' $version | wl-copy"
