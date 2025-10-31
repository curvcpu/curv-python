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
#   make publish                    # PKG=all, LEVEL=patch
#   make publish PKG=curv LEVEL=minor
#   make publish PKG=curvtools LEVEL=patch
#   make publish PKG=curvpyutils LEVEL=patch
# Notes:
#   - With hatch-vcs, version is derived from tags; we never edit pyproject.toml.
#   - Before publishing any package, checks if curvpyutils has new commits and publishes it first if needed.

.PHONY: publish
publish: check-clean
	set -e; \
	LEVEL=$${LEVEL:-patch}; \
	PKG=$${PKG:-all}; \
	DEPENDENT_LEVEL=$${DEPENDENT_LEVEL:-patch}; \
	case "$$PKG" in \
	  all|"") ORDER="curv curvtools" ;; \
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
	get_last_tag_ver() { \
	  pfx="$$1"; \
	  git tag --list "$${pfx}*" | sed -E "s/^$${pfx}//" \
	    | sort -t. -k1,1n -k2,2n -k3,3n | tail -n1; \
	}; \
	\
	update_dependency() { \
	  pkg_file="$$1"; dep_name="$$2"; dep_ver="$$3"; \
	  if grep -q '"'"'$${dep_name}>='"'"' "$$pkg_file"; then \
	    sed -i "s/\"$${dep_name}>=[^\"]*\"/\"$${dep_name}>=$${dep_ver}\"/" "$$pkg_file"; \
	  else \
	    awk -v dep="\"$${dep_name}>=$${dep_ver}\"," 'BEGIN { in_deps=0 } \
	      /^dependencies = \[/ { in_deps=1; print; next } \
	      in_deps && /^\]/ { print "  " dep; in_deps=0 } \
	      { print } \
	    ' "$$pkg_file" > "$$pkg_file.tmp" && mv "$$pkg_file.tmp" "$$pkg_file"; \
	  fi; \
	}; \
	\
	# Check if curvpyutils needs to be published first \
	if [ "$$PKG" != "curvpyutils" ]; then \
	  last_ver=$$(get_last_tag_ver "curvpyutils-v"); \
	  if [ -n "$$last_ver" ]; then \
	    last_tag="curvpyutils-v$$last_ver"; \
	    tag_commit=$$(git rev-parse "$$last_tag" 2>/dev/null || echo ""); \
	    head_commit=$$(git rev-parse HEAD); \
	    if [ -n "$$tag_commit" ] && [ "$$tag_commit" != "$$head_commit" ]; then \
	      echo "curvpyutils has new commits since $$last_tag, publishing it first..."; \
	      curvpy_tag=$$(next_tag "curvpyutils-v" "$$LEVEL"); \
	      echo "Tagging curvpyutils → $$curvpy_tag"; \
	      git tag "$$curvpy_tag"; \
	      curvpy_ver=$$(echo "$$curvpy_tag" | sed -E "s/^curvpyutils-v//"); \
	      update_dependency "packages/curv/pyproject.toml" "curvpyutils" "$$curvpy_ver"; \
	      update_dependency "packages/curvtools/pyproject.toml" "curvpyutils" "$$curvpy_ver"; \
	    fi; \
	  else \
	    echo "curvpyutils has no tags, publishing it first..."; \
	    curvpy_tag=$$(next_tag "curvpyutils-v" "$$LEVEL"); \
	    echo "Tagging curvpyutils → $$curvpy_tag"; \
	    git tag "$$curvpy_tag"; \
	    curvpy_ver=$$(echo "$$curvpy_tag" | sed -E "s/^curvpyutils-v//"); \
	    update_dependency "packages/curv/pyproject.toml" "curvpyutils" "$$curvpy_ver"; \
	    update_dependency "packages/curvtools/pyproject.toml" "curvpyutils" "$$curvpy_ver"; \
	  fi; \
	fi; \
	\
	for name in $$ORDER; do \
	  if [ "$$name" = "curv" ]; then \
	    pfx="curv-v"; lvl="$$LEVEL"; \
	  elif [ "$$name" = "curvtools" ]; then \
	    pfx="curvtools-v"; \
	    if [ "$$PKG" = "curv" ]; then lvl="$$DEPENDENT_LEVEL"; else lvl="$$LEVEL"; fi; \
	  elif [ "$$name" = "curvpyutils" ]; then \
	    pfx="curvpyutils-v"; lvl="$$LEVEL"; \
	  fi; \
	  tag=$$(next_tag "$$pfx" "$$lvl"); \
	  echo "Tagging $$name → $$tag"; \
	  git tag "$$tag"; \
	done; \
	\
	git push $(REMOTE) HEAD; \
	git push $(REMOTE) --tags; \
	echo "Published PKG=$$PKG (level=$$LEVEL). When PKG=curv, curvtools auto-bumped at $$DEPENDENT_LEVEL)."
