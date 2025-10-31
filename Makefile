# <repo-root>/Makefile
UV ?= uv
VENVDIR ?= .venv
PYTEST = uv run pytest
PYTEST_OPTS = -q -n auto
PACKAGES = packages/curv packages/curvtools
REMOTE ?= origin
PKG_CURV = packages/curv
PKG_curvtools = packages/curvtools
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
	$(UV) pip install -e $(PKG_curvtools)

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
		$(UV) run -C $$p -m build --sdist --wheel ; \
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

# Version bump + tag + push; hatch-vcs reads tags on build/publish
.PHONY: publish
publish: check-clean
	@set -e; \
	LEVEL=$${LEVEL:-patch}; \
	PKG=$${PKG:-all}; \
	case "$$PKG" in \
	  all|"") ORDER="curv curvtools" ;; \
	  curv)   ORDER="curv" ;; \
	  curvtools) ORDER="curvtools" ;; \
	  *) echo "Unknown PKG=$$PKG (expected curv|curvtools|all)"; exit 1 ;; \
	esac; \
	for name in $$ORDER; do \
		if [ "$$name" = "curv" ]; then \
			dir="$(PKG_CURV)"; prefix="curv-v"; this_level="$$LEVEL"; \
		else \
			dir="$(PKG_curvtools)"; prefix="curvtools-v"; \
			if [ "$$PKG" = "curv" ]; then this_level="$(DEPENDENT_LEVEL)"; else this_level="$$LEVEL"; fi; \
		fi; \
		$(UV) run -C $$dir hatch version $$this_level >/dev/null; \
		V=$$(uv run -C $$dir hatch version); \
		git add $$dir/pyproject.toml; \
		git commit -m "$$name: bump version to $$V"; \
		git tag $$prefix$$V; \
	done; \
	git push $(REMOTE) HEAD; \
	git push $(REMOTE) --tags; \
	echo "Published PKG=$$PKG (level=$$LEVEL). When PKG=curv, curvtools auto-bumped at $(DEPENDENT_LEVEL)."
