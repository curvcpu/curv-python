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
publish: check-clean
	set -e; \
	LEVEL=$${LEVEL:-patch}; \
	PKG=$${PKG:-all}; \
	case "$$PKG" in \
	  all|"") ORDER="curv curvpyutils curvtools" ;; \
	  curv)   ORDER="curv" ;; \
	  curvpyutils) ORDER="curvpyutils" ;; \
	  curvtools) ORDER="curvtools" ;; \
	  *) echo "Unknown PKG=$$PKG (expected curv|curvpyutils|curvtools|all)"; exit 1 ;; \
	esac; \
	for name in $$ORDER; do \
		if [ "$$name" = "curv" ]; then \
			dir="$(PKG_CURV)"; prefix="curv-v"; this_level="$$LEVEL"; \
		elif [ "$$name" = "curvpyutils" ]; then \
			dir="$(PKG_CURVPYUTILS)"; prefix="curvpyutils-v"; this_level="$$LEVEL"; \
		elif [ "$$name" = "curvtools" ]; then \
			dir="$(PKG_CURVTOOLS)"; prefix="curvtools-v"; this_level="$$LEVEL"; \
		else \
			echo "Unknown package: $$name"; exit 1; \
		fi; \
		cd $$dir; \
		$(UV) run hatch version $$this_level >/dev/null; \
		V=$$(uv run hatch version); \
		cd ../..; \
		git add $$dir/pyproject.toml; \
		git commit -m "$$name: bump version to $$V"; \
		git tag $$prefix$$V; \
	done; \
	git push $(REMOTE) HEAD; \
	git push $(REMOTE) --tags; \
	echo "Published PKG=$$PKG (level=$$LEVEL). When PKG=curv, curvtools auto-bumped at $(DEPENDENT_LEVEL)."


.PHONY: show-pypi-versions
show-pypi-versions:
	@for p in curv curvpyutils curvtools; do \
		echo "$$p:"; \
		scripts/chk-pypi-latest-ver.py -L "$$p"; \
		echo ""; \
	done