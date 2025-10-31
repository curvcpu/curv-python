# <repo-root>/Makefile
UV ?= uv
VENVDIR ?= .venv
PYTEST = uv run pytest
PYTEST_OPTS = -q -n auto
PACKAGES = packages/curv packages/curvtools
REMOTE ?= origin
PKG_CURV = packages/curv
PKG_CURVTOOLS = packages/curvtools
DEPENDENT_LEVEL ?= patch

.PHONY: setup
setup:
	$(UV) sync

# local convenience: format, then run hooks (will be no-op)
.PHONY: pre-commit
pre-commit:
	$(UV) run ruff format .
	$(UV) run pre-commit run --all-files

.PHONY: venv
venv: $(VENVDIR)/bin/python
$(VENVDIR)/bin/python:
	$(UV) venv --seed

.PHONY: install-min
install-min: venv
	$(UV) pip install -e $(PKG_CURV)
	$(UV) pip install -e $(PKG_CURVTOOLS)

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
#   make publish                    # PKG=all, LEVEL=patch
#   make publish PKG=curv LEVEL=minor
#   make publish PKG=curvtools LEVEL=patch
# Notes:
#   - With hatch-vcs, version is derived from tags; we never edit pyproject.toml.

.PHONY: publish
publish: check-clean
	@set -e; \
	LEVEL=$${LEVEL:-patch}; \
	PKG=$${PKG:-all}; \
	DEPENDENT_LEVEL=$${DEPENDENT_LEVEL:-patch}; \
	case "$$PKG" in \
	  all|"") ORDER="curv curvtools" ;; \
	  curv)   ORDER="curv" ;; \
	  curvtools) ORDER="curvtools" ;; \
	  *) echo "Unknown PKG=$$PKG (expected curv|curvtools|all)"; exit 1 ;; \
	esac; \
	\
	bump() { \
	  v="$${1:-0.0.0}"; lvl="$${2:-patch}"; \
	  set -- $$(printf '%s' "$$v" | tr '.' ' '); \
	  MA=$${1:-0}; MI=$${2:-0}; PA=$${3:-0}; \
	  case "$$lvl" in \
	    major) MA=$$((MA+1)); MI=0; PA=0 ;; \
	    minor) MI=$$((MI+1)); PA=0 ;; \
	    patch|*) PA=$$((PA+1)) ;; \
	  esac; \
	  printf '%s.%s.%s\n' "$$MA" "$$MI" "$$PA"; \
	}; \
	\
	next_tag() { \
	  pfx="$$1"; lvl="$$2"; \
	  last=$$(git tag --list "$${pfx}*" | sed -E "s/^$${pfx}//" \
	    | sort -t. -k1,1n -k2,2n -k3,3n | tail -n1); \
	  [ -z "$$last" ] && last="0.0.0"; \
	  ver=$$(bump "$$last" "$$lvl"); \
	  printf '%s%s\n' "$$pfx" "$$ver"; \
	}; \
	\
	for name in $$ORDER; do \
	  if [ "$$name" = "curv" ]; then \
	    pfx="curv-v"; lvl="$$LEVEL"; \
	  else \
	    pfx="curvtools-v"; \
	    if [ "$$PKG" = "curv" ]; then lvl="$$DEPENDENT_LEVEL"; else lvl="$$LEVEL"; fi; \
	  fi; \
	  tag=$$(next_tag "$$pfx" "$$lvl"); \
	  echo "Tagging $$name → $$tag"; \
	  git tag "$$tag"; \
	done; \
	\
	git push $(REMOTE) HEAD; \
	git push $(REMOTE) --tags; \
	echo "Published PKG=$$PKG (level=$$LEVEL). When PKG=curv, curvtools auto-bumped at $$DEPENDENT_LEVEL)."
