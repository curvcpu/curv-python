#!/usr/bin/env bash
# Publish a package with dependencies: bump version, create tag, push, verify
# Usage: scripts/publish.sh <package> <level>
#   package: curvpyutils, curv, or curvtools
#   level: patch or minor (major not allowed)
#
# Dependencies:
#   - curv depends on curvpyutils
#   - curvtools depends on curvpyutils and curv

set -euo pipefail

PACKAGE="${1:-}"
LEVEL="${2:-patch}"

if [[ -z "$PACKAGE" ]]; then
  echo "Error: package name required" >&2
  exit 1
fi

if [[ "$LEVEL" != "patch" && "$LEVEL" != "minor" ]]; then
  echo "Error: level must be 'patch' or 'minor' (major not allowed)" >&2
  exit 1
fi

REMOTE="${REMOTE:-origin}"

# Helper: get last tag version for a package
get_last_tag_ver() {
  local pfx="$1"
  git tag --list "${pfx}*" | sed -E "s/^${pfx}//" \
    | sort -t. -k1,1n -k2,2n -k3,3n | tail -n1
}

# Helper: get commit hash of last tag for a package
get_last_tag_commit() {
  local pfx="$1"
  local ver
  ver=$(get_last_tag_ver "$pfx")
  if [[ -n "$ver" ]]; then
    git rev-parse "${pfx}${ver}" 2>/dev/null || echo ""
  else
    echo ""
  fi
}

# Helper: check if package needs publishing
needs_publish() {
  local pkg="$1"
  local pfx
  case "$pkg" in
    curvpyutils) pfx="curvpyutils-v" ;;
    curv) pfx="curv-v" ;;
    curvtools) pfx="curvtools-v" ;;
    *) return 1 ;;
  esac

  local last_tag_commit
  last_tag_commit=$(get_last_tag_commit "$pfx")
  local head_commit
  head_commit=$(git rev-parse HEAD)

  # Need to publish if no tag exists or tag commit != HEAD
  [[ -z "$last_tag_commit" ]] || [[ "$last_tag_commit" != "$head_commit" ]]
}

# Helper: cleanup tag (delete local and remote)
cleanup_tag() {
  local tag="$1"
  echo "Cleaning up failed tag: $tag" >&2
  git tag -d "$tag" 2>/dev/null || true
  git push --delete "$REMOTE" "$tag" 2>/dev/null || true
  git push "$REMOTE" 2>/dev/null || true
}

# Helper: bump version
bump() {
  local v="${1:-0.0.0}"
  local lvl="${2:-patch}"
  local MA MI PA

  IFS='.' read -r MA MI PA <<< "$v"
  MA="${MA:-0}"
  MI="${MI:-0}"
  PA="${PA:-0}"

  case "$lvl" in
    minor) MI=$((MI + 1)); PA=0 ;;
    patch|*) PA=$((PA + 1)) ;;
  esac

  printf '%s.%s.%s\n' "$MA" "$MI" "$PA"
}

# Helper: get next tag
next_tag() {
  local pfx="$1"
  local lvl="$2"
  local last

  last=$(get_last_tag_ver "$pfx")
  if [[ -z "$last" ]]; then
    last="0.0.0"
  fi

  local ver
  ver=$(bump "$last" "$lvl")
  printf '%s%s\n' "$pfx" "$ver"
}

# Helper: publish a single package
publish_one() {
  local pkg="$1"
  local lvl="$2"
  local pfx

  case "$pkg" in
    curvpyutils) pfx="curvpyutils-v" ;;
    curv) pfx="curv-v" ;;
    curvtools) pfx="curvtools-v" ;;
    *) echo "Error: unknown package '$pkg'" >&2; return 1 ;;
  esac

  # Check if already published
  if ! needs_publish "$pkg"; then
    echo "$pkg already published at HEAD (no new commits)" >&2
    return 0
  fi

  echo "Publishing $pkg..." >&2

  # Calculate and create tag
  local new_tag
  new_tag=$(next_tag "$pfx" "$lvl")
  echo "Tagging $pkg → $new_tag" >&2
  git tag "$new_tag"

  # Push HEAD and tags
  git push "$REMOTE" HEAD
  git push "$REMOTE" --tags

  # Wait for GitHub publish result
  echo "Waiting for GitHub publish result..." >&2
  if ! scripts/wait-github-publish-result.py "$new_tag"; then
    echo "Error: GitHub publish failed for $new_tag" >&2
    cleanup_tag "$new_tag"
    return 1
  fi

  # Verify PyPI publication
  echo "Verifying PyPI publication..." >&2
  local pypi_ver
  pypi_ver=$(scripts/chk-pypi-latest-ver.py -L "$pkg")
  local expected_ver
  expected_ver=$(echo "$new_tag" | sed -E "s/^${pfx}//")

  if [[ "$pypi_ver" != "$expected_ver" ]]; then
    echo "Error: PyPI version mismatch. Expected $expected_ver, got $pypi_ver" >&2
    cleanup_tag "$new_tag"
    return 1
  fi

  echo "$pkg published successfully as $new_tag ($expected_ver)" >&2
  return 0
}

# Main publish logic with dependencies
case "$PACKAGE" in
  curvpyutils)
    publish_one "curvpyutils" "$LEVEL" || exit 1
    ;;
  curv)
    # First publish curvpyutils if needed
    if needs_publish "curvpyutils"; then
      publish_one "curvpyutils" "$LEVEL" || exit 1
    fi
    # Then publish curv
    publish_one "curv" "$LEVEL" || exit 1
    ;;
  curvtools)
    # First publish curvpyutils if needed
    if needs_publish "curvpyutils"; then
      publish_one "curvpyutils" "$LEVEL" || exit 1
    fi
    # Then publish curv if needed
    if needs_publish "curv"; then
      publish_one "curv" "$LEVEL" || exit 1
    fi
    # Finally publish curvtools
    publish_one "curvtools" "$LEVEL" || exit 1
    ;;
  *)
    echo "Error: unknown package '$PACKAGE'" >&2
    exit 1
    ;;
esac

echo "Publish complete for $PACKAGE" >&2
