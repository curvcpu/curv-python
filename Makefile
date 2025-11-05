# <repo-root>/Makefile
UV ?= uv
VENVDIR ?= .venv
PYTEST = uv run pytest
PYTEST_OPTS = -q -n auto
PACKAGES = packages/curv packages/curvtools packages/curvpyutils
REMOTE ?= origin
PKG_CURV = packages/curv
PKG_CURVTOOLS = packages/curvtools

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
	echo "Fetching latest tags from remote '$(REMOTE)'..."; \
	git fetch $(REMOTE) --tags; \
	LEVEL=$${LEVEL:-patch}; \
	PKG=$${PKG:-all}; \
	case "$$PKG" in \
	  all|"") ORDER="curvpyutils curv curvtools" ;; \
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
	  lvl="$$LEVEL"; \
	  tag=$$(next_tag "$$pfx" "$$lvl"); \
	  echo "Tagging $$name → $$tag"; \
	  git tag -a "$$tag" -m "Release $$name ($$tag)"; \
	  git push $(REMOTE) HEAD; \
	  git push $(REMOTE) --tags; \
	  echo "📣 Published PKG=$$name (level=$$LEVEL)."; \
	done; 

#
# make untag PKG=curvtools [VER=0.0.6]
# Delete tags for PKG that are newer than VER.
# If VER not specified, use latest published version from PyPI.
# VER must not be older than the latest published version on PyPI; otherwise we die with error.
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

#
# make show
# Show all PyPI published versions and local tags for each package which may or may not have succeeded in publishing
#
.PHONY: show
show:
	@set -e; \
	echo "Fetching all remote tags to make sure we're up to date..."; \
	git fetch origin --tags; \
	echo "Showing all versions for each package..."; \
	echo ""; \
	for p in curv curvtools curvpyutils; do \
		scripts/chk-pypi-latest-ver.py "$$p"; \
		echo ""; \
	done; \

#
# make show-publish-status
# Show the CI status of the latest tag for each package
#
.PHONY: show-publish-status
show-publish-status:
	@echo "Checking publish status for latest tags..."; \
	for pkg in curv curvtools curvpyutils; do \
		latest_tag=$$(git tag --list "$${pkg}-v*" | sort -V | tail -n1); \
		if [ -n "$$latest_tag" ]; then \
			status=$$(curl -fsSL "https://api.github.com/repos/curvcpu/curv-python/commits/$${latest_tag}/status" 2>/dev/null | jq -r '.state' 2>/dev/null || echo "unknown"); \
			echo "  👉 $${latest_tag}: $${status}"; \
		else \
			echo "  ❌ $${pkg}: no tags found"; \
		fi; \
	done; \


#
# make help to remind what the targets are
#
.PHONY: help
help:
	@echo "Run these once before you get started:"
	@echo "  make setup               - Setup the project"
	@echo "  make install-dev         - Install the development packages"
	@echo ""
	@echo "Building and running tests:"
	@echo "  make build               - Build the packages"
	@echo "  make test                - Run the tests"
	@echo "  make test-unit           - Run the unit tests"
	@echo "  make test-e2e            - Run the CLI e2e tests"
	@echo "  make clean               - Clean the project"
	@echo ""
	@echo "Publishing to PyPI:"
	@echo "  make publish             - Publish the packages"
	@echo "  make untag               - Undo a tag"
	@echo "  make show                - Show the PyPI published versions and local tags"
	@echo "  make show-publish-status - Show the CI status of the latest tag for each package"
	@echo ""
	@echo "Informational commands:"
	@echo "  make show                - Show the PyPI published versions and local tags"
	@echo "  make show-publish-status - Show the CI status of the latest tag for each package"
	@echo "  make help                - Show this help message"
	@echo ""
	@echo "For more details, see the contributing guide:"
	@echo "  https://github.com/curvcpu/curv-python/blob/main/.github/CONTRIBUTING.md"
