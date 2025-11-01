# <repo-root>/Makefile
UV ?= uv
VENVDIR ?= .venv
PYTEST = uv run pytest
PYTEST_OPTS = -q -n auto
PACKAGES = packages/curv packages/curvtools packages/curvpyutils
REMOTE ?= origin
PKG_CURV = packages/curv
PKG_CURVTOOLS = packages/curvtools
PKG_CURVPYUTILS = packages/curvpyutils
DEPENDENT_LEVEL ?= patch

.PHONY: setup
setup:
	$(UV) sync

.PHONY: pre-commit
pre-commit:
	$(UV) run pre-commit run --all-files

.PHONY: venv
venv: $(VENVDIR)/bin/python
$(VENVDIR)/bin/python:
	$(UV) venv --seed

.PHONY: install-min
install-min: venv
	$(UV) pip install -e $(PKG_CURV)
	$(UV) pip install -e $(PKG_CURVTOOLS)
	$(UV) pip install -e $(PKG_CURVPYUTILS)

.PHONY: install-dev
install-dev: install-min

.PHONY: fmt
fmt:
	$(UV) run ruff format .

.PHONY: lint
lint:
	$(UV) run ruff check .

.PHONY: test
test: install-min test-unit test-e2e

.PHONY: test-unit
test-unit:
	$(PYTEST) $(PYTEST_OPTS) -m "unit"

.PHONY: test-e2e
test-e2e:
	$(PYTEST) $(PYTEST_OPTS) -m "e2e"

.PHONY: build
build:
	for p in $(PACKAGES); do \
		( cd $$p && $(UV) run -m build --sdist --wheel ) \
	done

.PHONY: clean
clean:
	find . -type d -name __pycache__ -prune -exec rm -rf {} +
	rm -rf build dist .pytest_cache .ruff_cache $(VENVDIR)
	for p in $(PACKAGES); do \
		rm -rf $$p/dist $$p/build $$p/*.egg-info $$p/src/*.egg-info ; \
	done

.PHONY: check-clean
check-clean:
	@test -z "$$(git status --porcelain)" || (echo "Error: git working tree is not clean. Commit/stash first."; exit 1)

# -------- Version bump + publish (via tags only) --------
# Usage:
#   make publish PKG=curvpyutils LEVEL=patch
#   make publish PKG=curv LEVEL=minor
#   make publish PKG=curvtools LEVEL=patch
# Notes:
#   - With hatch-vcs, version is derived from tags; we never edit pyproject.toml.
#   - Dependencies: curv depends on curvpyutils, curvtools depends on both.
#   - LEVEL must be 'patch' or 'minor' (major not allowed).
#   - All dependency logic is handled by scripts/publish.sh

LEVEL ?= patch
PKG ?=

.PHONY: publish
publish: check-clean
	@if [ -z "$(PKG)" ]; then \
	  echo "Error: PKG must be set (curvpyutils, curv, or curvtools)" >&2; \
	  exit 1; \
	fi
	@scripts/publish.sh "$(PKG)" "$(LEVEL)"
