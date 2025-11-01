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
#   make publish-curvpyutils LEVEL=patch
#   make publish-curv LEVEL=minor
#   make publish-curvtools LEVEL=patch
# Notes:
#   - With hatch-vcs, version is derived from tags; we never edit pyproject.toml.
#   - Dependencies: curv depends on curvpyutils, curvtools depends on both.
#   - LEVEL must be 'patch' or 'minor' (major not allowed).

LEVEL ?= patch

# Publish stamp for curvpyutils
build/.publish.curvpyutils.stamp:
	@mkdir -p build
	@set -e; \
	LEVEL="$${LEVEL:-patch}"; \
	get_last_tag_ver() { \
	  pfx="$$1"; \
	  git tag --list "$${pfx}*" | sed -E "s/^$${pfx}//" \
	    | sort -t. -k1,1n -k2,2n -k3,3n | tail -n1; \
	}; \
	get_last_tag_commit() { \
	  pfx="$$1"; \
	  ver=$$(get_last_tag_ver "$$pfx"); \
	  if [ -n "$$ver" ]; then \
	    git rev-parse "$${pfx}$$ver" 2>/dev/null || echo ""; \
	  else \
	    echo ""; \
	  fi; \
	}; \
	cleanup_tag() { \
	  git tag -d "$$1" 2>/dev/null || true; \
	  git push --delete $(REMOTE) "$$1" 2>/dev/null || true; \
	  git push $(REMOTE) 2>/dev/null || true; \
	}; \
	last_tag_commit=$$(get_last_tag_commit "curvpyutils-v"); \
	head_commit=$$(git rev-parse HEAD); \
	if [ -n "$$last_tag_commit" ] && [ "$$last_tag_commit" = "$$head_commit" ]; then \
	  echo "curvpyutils already published at HEAD (no new commits)"; \
	  touch "$@"; \
	else \
	  echo "Publishing curvpyutils..."; \
	  new_tag=$$(scripts/publish.sh curvpyutils "$$LEVEL"); \
	  echo "Waiting for GitHub publish result..."; \
	  if ! scripts/wait-github-publish-result.py "$$new_tag"; then \
	    echo "Error: GitHub publish failed for $$new_tag"; \
	    cleanup_tag "$$new_tag"; \
	    exit 1; \
	  fi; \
	  echo "Verifying PyPI publication..."; \
	  pypi_ver=$$(scripts/chk-pypi-latest-ver.py -L curvpyutils); \
	  expected_ver=$$(echo "$$new_tag" | sed -E "s/^curvpyutils-v//"); \
	  if [ "$$pypi_ver" != "$$expected_ver" ]; then \
	    echo "Error: PyPI version mismatch. Expected $$expected_ver, got $$pypi_ver"; \
	    cleanup_tag "$$new_tag"; \
	    exit 1; \
	  fi; \
	  echo "curvpyutils published successfully as $$new_tag ($$expected_ver)"; \
	  touch "$@"; \
	fi

# Publish stamp for curv (depends on curvpyutils)
build/.publish.curv.stamp: build/.publish.curvpyutils.stamp
	@mkdir -p build
	@set -e; \
	LEVEL="$${LEVEL:-patch}"; \
	get_last_tag_ver() { \
	  pfx="$$1"; \
	  git tag --list "$${pfx}*" | sed -E "s/^$${pfx}//" \
	    | sort -t. -k1,1n -k2,2n -k3,3n | tail -n1; \
	}; \
	get_last_tag_commit() { \
	  pfx="$$1"; \
	  ver=$$(get_last_tag_ver "$$pfx"); \
	  if [ -n "$$ver" ]; then \
	    git rev-parse "$${pfx}$$ver" 2>/dev/null || echo ""; \
	  else \
	    echo ""; \
	  fi; \
	}; \
	cleanup_tag() { \
	  git tag -d "$$1" 2>/dev/null || true; \
	  git push --delete $(REMOTE) "$$1" 2>/dev/null || true; \
	  git push $(REMOTE) 2>/dev/null || true; \
	}; \
	last_tag_commit=$$(get_last_tag_commit "curv-v"); \
	head_commit=$$(git rev-parse HEAD); \
	if [ -n "$$last_tag_commit" ] && [ "$$last_tag_commit" = "$$head_commit" ]; then \
	  echo "curv already published at HEAD (no new commits)"; \
	  touch "$@"; \
	else \
	  echo "Publishing curv..."; \
	  new_tag=$$(scripts/publish.sh curv "$$LEVEL"); \
	  echo "Waiting for GitHub publish result..."; \
	  if ! scripts/wait-github-publish-result.py "$$new_tag"; then \
	    echo "Error: GitHub publish failed for $$new_tag"; \
	    cleanup_tag "$$new_tag"; \
	    exit 1; \
	  fi; \
	  echo "Verifying PyPI publication..."; \
	  pypi_ver=$$(scripts/chk-pypi-latest-ver.py -L curv); \
	  expected_ver=$$(echo "$$new_tag" | sed -E "s/^curv-v//"); \
	  if [ "$$pypi_ver" != "$$expected_ver" ]; then \
	    echo "Error: PyPI version mismatch. Expected $$expected_ver, got $$pypi_ver"; \
	    cleanup_tag "$$new_tag"; \
	    exit 1; \
	  fi; \
	  echo "curv published successfully as $$new_tag ($$expected_ver)"; \
	  touch "$@"; \
	fi

# Publish stamp for curvtools (depends on curvpyutils and curv)
build/.publish.curvtools.stamp: build/.publish.curvpyutils.stamp build/.publish.curv.stamp
	@mkdir -p build
	@set -e; \
	LEVEL="$${LEVEL:-patch}"; \
	get_last_tag_ver() { \
	  pfx="$$1"; \
	  git tag --list "$${pfx}*" | sed -E "s/^$${pfx}//" \
	    | sort -t. -k1,1n -k2,2n -k3,3n | tail -n1; \
	}; \
	get_last_tag_commit() { \
	  pfx="$$1"; \
	  ver=$$(get_last_tag_ver "$$pfx"); \
	  if [ -n "$$ver" ]; then \
	    git rev-parse "$${pfx}$$ver" 2>/dev/null || echo ""; \
	  else \
	    echo ""; \
	  fi; \
	}; \
	cleanup_tag() { \
	  git tag -d "$$1" 2>/dev/null || true; \
	  git push --delete $(REMOTE) "$$1" 2>/dev/null || true; \
	  git push $(REMOTE) 2>/dev/null || true; \
	}; \
	last_tag_commit=$$(get_last_tag_commit "curvtools-v"); \
	head_commit=$$(git rev-parse HEAD); \
	if [ -n "$$last_tag_commit" ] && [ "$$last_tag_commit" = "$$head_commit" ]; then \
	  echo "curvtools already published at HEAD (no new commits)"; \
	  touch "$@"; \
	else \
	  echo "Publishing curvtools..."; \
	  new_tag=$$(scripts/publish.sh curvtools "$$LEVEL"); \
	  echo "Waiting for GitHub publish result..."; \
	  if ! scripts/wait-github-publish-result.py "$$new_tag"; then \
	    echo "Error: GitHub publish failed for $$new_tag"; \
	    cleanup_tag "$$new_tag"; \
	    exit 1; \
	  fi; \
	  echo "Verifying PyPI publication..."; \
	  pypi_ver=$$(scripts/chk-pypi-latest-ver.py -L curvtools); \
	  expected_ver=$$(echo "$$new_tag" | sed -E "s/^curvtools-v//"); \
	  if [ "$$pypi_ver" != "$$expected_ver" ]; then \
	    echo "Error: PyPI version mismatch. Expected $$expected_ver, got $$pypi_ver"; \
	    cleanup_tag "$$new_tag"; \
	    exit 1; \
	  fi; \
	  echo "curvtools published successfully as $$new_tag ($$expected_ver)"; \
	  touch "$@"; \
	fi

# Phony targets that users invoke
.PHONY: publish-curvpyutils publish-curv publish-curvtools
publish-curvpyutils: check-clean build/.publish.curvpyutils.stamp
	@echo "curvpyutils publish complete"

# When publishing curv, also publish curvtools (since curvtools depends on curv)
publish-curv: check-clean build/.publish.curv.stamp build/.publish.curvtools.stamp
	@echo "curv publish complete"

publish-curvtools: check-clean build/.publish.curvtools.stamp
	@echo "curvtools publish complete"
