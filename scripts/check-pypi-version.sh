#!/usr/bin/env bash
PKG=curv
VER=0.1.6
curl -fsSL "https://pypi.org/pypi/$PKG/json" \
  | jq -e --arg v "$VER" '.releases[$v] and (.releases[$v] | length > 0)' \
  >/dev/null && echo "PyPI has $PKG==$VER" || echo "Not on PyPI yet"
