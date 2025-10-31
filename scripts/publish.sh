#!/usr/bin/env bash
# Publish a package: bump version, create tag, update dependencies, push
# Usage: scripts/publish.sh <package> <level>
#   package: curvpyutils, curv, or curvtools
#   level: patch or minor (major not allowed)

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

# Map package to tag prefix
case "$PACKAGE" in
  curvpyutils) TAG_PFX="curvpyutils-v" ;;
  curv) TAG_PFX="curv-v" ;;
  curvtools) TAG_PFX="curvtools-v" ;;
  *) echo "Error: unknown package '$PACKAGE'" >&2; exit 1 ;;
esac

# Bump version function
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

# Get next tag
next_tag() {
  local pfx="$1"
  local lvl="$2"
  local last

  last=$(git tag --list "${pfx}*" | sed -E "s/^${pfx}//" \
    | sort -t. -k1,1n -k2,2n -k3,3n | tail -n1)

  if [[ -z "$last" ]]; then
    last="0.0.0"
  fi

  local ver
  ver=$(bump "$last" "$lvl")
  printf '%s%s\n' "$pfx" "$ver"
}

# Update dependency in pyproject.toml
update_dependency() {
  local pkg_file="$1"
  local dep_name="$2"
  local dep_ver="$3"

  if grep -q "\"${dep_name}>=" "$pkg_file"; then
    sed -i "s/\"${dep_name}>=[^\"]*\"/\"${dep_name}>=${dep_ver}\"/" "$pkg_file"
  else
    awk -v dep="\"${dep_name}>=${dep_ver}\"," 'BEGIN { in_deps=0 }
      /^dependencies = \[/ { in_deps=1; print; next }
      in_deps && /^\]/ { print "  " dep; in_deps=0 }
      { print }
    ' "$pkg_file" > "${pkg_file}.tmp" && mv "${pkg_file}.tmp" "$pkg_file"
  fi
}

# Calculate next tag
NEW_TAG=$(next_tag "$TAG_PFX" "$LEVEL")
NEW_VER=$(echo "$NEW_TAG" | sed -E "s/^${TAG_PFX}//")

echo "Tagging $PACKAGE → $NEW_TAG"

# Create the tag
git tag "$NEW_TAG"

# Update dependencies
if [[ "$PACKAGE" == "curvpyutils" ]]; then
  update_dependency "packages/curv/pyproject.toml" "curvpyutils" "$NEW_VER"
  update_dependency "packages/curvtools/pyproject.toml" "curvpyutils" "$NEW_VER"
elif [[ "$PACKAGE" == "curv" ]]; then
  update_dependency "packages/curvtools/pyproject.toml" "curv" "$NEW_VER"
fi

# Push HEAD and tags
git push "$REMOTE" HEAD
git push "$REMOTE" --tags

# Output the tag name (used by Makefile)
echo "$NEW_TAG"
