# <repo-root>/Makefile
UV ?= uv
VENVDIR ?= .venv
PYTEST = uv run pytest
PYTEST_OPTS = -q -n auto
PACKAGES = packages/curv packages/curvtools packages/curvpyutils
REMOTE ?= origin
PKG_CURV = packages/curv
PKG_CURVTOOLS = packages/curvtools
DEPENDENT_LEVEL ?= patch

.PHONY: setup
setup:
	$(UV) sync

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

#
# make publish [PKG=curv|curvpyutils|curvtools|all] [LEVEL=patch|minor|major]
# example: make publish PKG=curvpyutils LEVEL=minor
# - defaults: PKG=all, LEVEL=patch
#
.PHONY: publish
publish: check-clean build test
	@set -e; \
	LEVEL=$${LEVEL:-patch}; \
	PKG=$${PKG:-all}; \
	DEPENDENT_LEVEL=$${DEPENDENT_LEVEL:-patch}; \
	case "$$PKG" in \
	  all|"") ORDER="curv curvtools curvpyutils" ;; \
	  curv)   ORDER="curv" ;; \
	  curvtools) ORDER="curvtools" ;; \
	  curvpyutils) ORDER="curvpyutils" ;; \
	  *) echo "Unknown PKG=$$PKG (expected curv|curvtools|curvpyutils|all)"; exit 1 ;; \
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
	    pfx="curv-v"; \
	  elif [ "$$name" = "curvtools" ]; then \
	    pfx="curvtools-v"; \
	  elif [ "$$name" = "curvpyutils" ]; then \
	    pfx="curvpyutils-v"; \
	  fi; \
	  if [ "$$PKG" = "curv" ] && [ "$$name" != "curv" ]; then \
	    lvl="$$DEPENDENT_LEVEL"; \
	  else \
	    lvl="$$LEVEL"; \
	  fi; \
	  tag=$$(next_tag "$$pfx" "$$lvl"); \
	  echo "Tagging $$name → $$tag"; \
	  git tag "$$tag"; \
	done; \
	\
	git push $(REMOTE) HEAD; \
	git push $(REMOTE) --tags; \
	echo "Published PKG=$$PKG (level=$$LEVEL). When PKG=curv, curvtools auto-bumped at $$DEPENDENT_LEVEL)."

#
# make untag PKG=curvtools [VER=0.0.6]
# Delete tags for PKG that are newer than VER.
# If VER not specified, use latest published version from PyPI.
# VER must not be older than the latest published version.
# PKG is required.
#
.PHONY: untag
untag: check-clean
	@set -e; \
	PKG=$${PKG:-}; \
	if [ -z "$$PKG" ]; then \
		echo "Error: PKG= must be specified (curv|curvtools|curvpyutils)"; \
		exit 1; \
	fi; \
	# Always get the latest published version for safety \
	echo "Getting latest published version for $$PKG..."; \
	PUBLISHED=$$(scripts/chk-pypi-latest-ver.py -L "$$PKG"); \
	echo "Latest published: $$PUBLISHED"; \
	\
	VER=$${VER:-}; \
	if [ -z "$$VER" ]; then \
		LATEST="$$PUBLISHED"; \
		echo "Using published version as baseline: $$LATEST"; \
	else \
		# Validate that VER is not older than published version \
		if [ "$$(printf '%s\n%s' "$$PUBLISHED" "$$VER" | sort -V | head -n1)" = "$$VER" ] && [ "$$VER" != "$$PUBLISHED" ]; then \
			echo "Error: Cannot delete tags older than or equal to published version $$PUBLISHED"; \
			echo "Specified VER=$$VER is older than published version"; \
			exit 1; \
		fi; \
		LATEST="$$VER"; \
		echo "Using specified version: $$LATEST"; \
	fi; \
	\
	# Get package prefix (curv-v, curvtools-v, or curvpyutils-v) \
	case "$$PKG" in \
	  curv) PREFIX="curv-v" ;; \
	  curvtools) PREFIX="curvtools-v" ;; \
	  curvpyutils) PREFIX="curvpyutils-v" ;; \
	  *) echo "Error: Unknown PKG=$$PKG"; exit 1 ;; \
	esac; \
	\
	# Find all tags for this package that are newer than LATEST \
	TAGS_TO_DELETE=$$(git tag --list "$${PREFIX}*" | while read tag; do \
		tag_ver=$$(echo "$$tag" | sed "s/$${PREFIX}//"); \
		if [ "$$(printf '%s\n%s' "$$LATEST" "$$tag_ver" | sort -V | tail -n1)" = "$$tag_ver" ] && [ "$$tag_ver" != "$$LATEST" ]; then \
			echo "$$tag"; \
		fi; \
	done); \
	\
	if [ -z "$$TAGS_TO_DELETE" ]; then \
		echo "No tags found for $$PKG newer than $$LATEST"; \
		exit 0; \
	fi; \
	\
	echo "Tags to delete: $$TAGS_TO_DELETE"; \
	echo "Deleting local tags..."; \
	git tag -d $$TAGS_TO_DELETE; \
	echo "Deleting remote tags..."; \
	if git push --delete $(REMOTE) $$TAGS_TO_DELETE 2>/dev/null; then \
		echo "Successfully deleted remote tags"; \
	else \
		echo "Warning: Some remote tags may not exist or deletion failed"; \
	fi; \
	echo "Successfully deleted tags newer than $$LATEST for $$PKG"

.PHONY: show-pypi-versions
show-pypi-versions:
	@for p in curv curvtools curvpyutils; do \
		echo "$$p:"; \
		scripts/chk-pypi-latest-ver.py -L "$$p"; \
		echo ""; \
	done