# <repo-root>/Makefile
SHELL := /usr/bin/env bash
.SHELLFLAGS := -euo pipefail -c

UV ?= uv
VENVDIR ?= .venv
PYTEST := uv run pytest
PYTEST_OPTS := -q --numprocesses auto
PACKAGES := packages/curv packages/curvtools packages/curvpyutils
PKG_CURV := packages/curv
PKG_CURVTOOLS := packages/curvtools
PKG_CURVPYUTILS := packages/curvpyutils
SCRIPT_WAIT_CI := scripts/wait_ci.py
SCRIPT_SUBST := curv-subst
SCRIPT_SUBST_OPTS := -f -1 -m
SCRIPT_CHK_LATEST_VER := scripts/chk-latest-version.py
SCRIPT_GET_CANONICAL_REMOTE := scripts/publish-tools/src/canonical_remote.py  # uses `git remote -v` to find user's local name for the github.com/curvcpu/curv-python repo
SCRIPT_GET_PUBLISH_DEPS := scripts/publish-tools/src/get-publish-deps.py
REMOTE ?= origin

PUBLISH_HOSTNAME  := github.com
PUBLISH_ORG       := curvcpu
PUBLISH_REPO      := curv-python
PUBLISH_BRANCH    := main
PUBLISH_REMOTE    := $(shell $(SCRIPT_GET_CANONICAL_REMOTE) $(PUBLISH_HOSTNAME) $(PUBLISH_ORG) $(PUBLISH_REPO))

.PHONY: setup-sync
setup-sync:
	@echo "🔄 Syncing root dev deps (pytest, ruff, etc.)..."
	@$(UV) sync

.PHONY: venv
venv: $(VENVDIR)/bin/python
$(VENVDIR)/bin/python:
	$(UV) venv --seed

.PHONY: install-min
install-min: venv
	@echo "🔄 Installing editable installs of workspace packages..."
	@if $(UV) pip show -q $(notdir $(PKG_CURVPYUTILS)) >/dev/null 2>&1; then \
		echo "✓ $(notdir $(PKG_CURVPYUTILS)) already installed"; \
	else \
		SETUPTOOLS_SCM_PRETEND_VERSION=$$($(SCRIPT_CHK_LATEST_VER) curvpyutils -Gb) $(UV) pip install -e $(PKG_CURVPYUTILS); \
		echo "✓ Installed $(notdir $(PKG_CURVPYUTILS))..."; \
	fi;
	@if $(UV) pip show -q $(notdir $(PKG_CURV)) >/dev/null 2>&1; then \
		echo "✓ $(notdir $(PKG_CURV)) already installed"; \
	else \
		SETUPTOOLS_SCM_PRETEND_VERSION=$$($(SCRIPT_CHK_LATEST_VER) curv -Gb) $(UV) pip install -e $(PKG_CURV); \
		echo "✓ Installed $(notdir $(PKG_CURV))..."; \
	fi;
	@if $(UV) pip show -q $(notdir $(PKG_CURVTOOLS)) >/dev/null 2>&1; then \
		echo "✓ $(notdir $(PKG_CURVTOOLS)) already installed"; \
	else \
		SETUPTOOLS_SCM_PRETEND_VERSION=$$($(SCRIPT_CHK_LATEST_VER) curvtools -Gb) $(UV) pip install -e $(PKG_CURVTOOLS); \
		echo "✓ Installed $(notdir $(PKG_CURVTOOLS))..."; \
	fi;

.PHONY: fetch-latest-tags
fetch-latest-tags:
	@[ -n "$(PUBLISH_REMOTE)" ] && { \
		echo "Fetching latest tags from remote '$(PUBLISH_REMOTE)'..." && \
		git fetch "$(PUBLISH_REMOTE)" --tags --quiet; \
		echo "✓ Fetched latest tags from remote '$(PUBLISH_REMOTE)'"; \
	} || { \
		echo "❌ Failed to fetch latest tags from publish remote '$(PUBLISH_REMOTE)'"; \
		exit 1; \
	};

.PHONY: setup
setup: install-min fetch-latest-tags
	@SETUPTOOLS_SCM_PRETEND_VERSION=$$($(SCRIPT_CHK_LATEST_VER) curvtools -Gb) $(UV) tool install --editable $(PKG_CURVTOOLS)
	@#$(UV) tool install --editable $(PKG_CURVTOOLS)
	@echo "✓ All CLI tools (editable) available on PATH"
	@# Edit shell's rc file to keep the PATH update persistent
	@$(UV) tool update-shell -q || true
	@$(UV) run curvtools instructions
	@eval "$$($(UV) run curvtools shellenv)"

.PHONY: test
test: 
	$(PYTEST) $(PYTEST_OPTS)

.PHONY: unsetup-editable-installs
unsetup-editable-installs:
	@# Only uninstall if installed; stay quiet otherwise
	@if $(UV) pip show -q $(notdir $(PKG_CURVPYUTILS)) >/dev/null 2>&1; then \
		$(UV) pip uninstall -q $(notdir $(PKG_CURVPYUTILS)) >/dev/null; \
		echo "✅ Removed $(notdir $(PKG_CURVPYUTILS))"; \
	fi
	@if $(UV) pip show -q $(notdir $(PKG_CURV)) >/dev/null 2>&1; then \
		$(UV) pip uninstall -q $(notdir $(PKG_CURV)) >/dev/null; \
		echo "✅ Removed $(notdir $(PKG_CURV))"; \
	fi
	@if $(UV) pip show -q $(notdir $(PKG_CURVTOOLS)) >/dev/null 2>&1; then \
		$(UV) pip uninstall -q $(notdir $(PKG_CURVTOOLS)) >/dev/null; \
		echo "✅ Removed $(notdir $(PKG_CURVTOOLS))"; \
	fi

.PHONY: unsetup
unsetup: unsetup-editable-installs clean
	@$(UV) tool uninstall --all -q
	@echo "✓ Removed CLI tools from uv tool environment"


.PHONY: build
build:
	for p in $(PACKAGES); do \
		$(UV) run -m build --sdist --wheel $$p; \
	done

.PHONY: clean
clean:
	@find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
	@find . -type d -name .pytest_cache -exec rm -rf {} + 2>/dev/null || true
	@find . -type d -name .mypy_cache -exec rm -rf {} + 2>/dev/null || true
	@find . -type d -name .ruff_cache -exec rm -rf {} + 2>/dev/null || true
	@rm -rf build dist $(VENVDIR)
	@for p in $(PACKAGES); do \
		rm -rf $$p/dist $$p/build $$p/*.egg-info $$p/src/*.egg-info ; \
	done;
	@[ -d "$(VENVDIR)" ] && { \
		$(RM) -rf $(VENVDIR)/bin/python ; \
		echo "✓ Removed $(VENVDIR)/bin/python"; \
	} || { \
		echo "✓ Skipping venv cleanup since $(VENVDIR) does not exist"; \
	}

.PHONY: check-git-clean
check-git-clean:
	@test -z "$$(git status --porcelain)" || { \
		echo "❌ [$(@)] error: git working tree is not clean. Commit/stash first."; \
		exit 1; \
	} || { \
		echo "✓ [$(@)] git working tree is clean"; \
	};

.PHONY: must-be-on-main
must-be-on-main:
	@current=$$(git branch --show-current); \
	if [ "$$current" != $(PUBLISH_BRANCH) ]; then \
		echo "❌ [$(@)] error: must be on $(PUBLISH_BRANCH) branch (currently $$current)"; \
		exit 1; \
	else \
		echo "✓ [$(@)] currently on correct branch ($(PUBLISH_BRANCH) == $$current)"; \
	fi;

.PHONY: must-have-publish-remote-set-correctly
must-have-publish-remote-set-correctly:
	@[ -n "$(PUBLISH_REMOTE)" ] && { \
		echo "✓ [$(@)] publish remote set correctly: $(PUBLISH_REMOTE)"; \
	} || { \
		echo "❌ [$(@)] error: must have publish remote set correctly"; \
		exit 1; \
	};

.PHONY: ensure-main-in-sync
ensure-main-in-sync:
	@remote="$(PUBLISH_REMOTE)"; \
	if [ -z "$$remote" ]; then \
		echo "❌ [$(@)] error: PUBLISH_REMOTE is not set" >&2; \
		exit 1; \
	fi; \
	local_head=$$(git rev-parse HEAD); \
	remote_head=$$(git rev-parse "$$remote/main"); \
	base=$$(git merge-base HEAD "$$remote/main"); \
	if [ "$$local_head" = "$$remote_head" ]; then \
		echo "✓ [$(@)] main is in sync with $$remote/main"; \
	elif [ "$$base" = "$$local_head" ]; then \
		echo "❌ [$(@)] error: local main is behind $$remote/main." >&2; \
		echo "Hint: run:" >&2; \
		echo "  git pull --ff-only $$remote main" >&2; \
		exit 1; \
	elif [ "$$base" = "$$remote_head" ]; then \
		echo "❌ [$(@)] error: local main has commits not yet pushed to $$remote/main." >&2; \
		echo "Hint: run:" >&2; \
		echo "  git push $$remote main" >&2; \
		exit 1; \
	else \
		echo "❌ [$(@)] error: local main and $$remote/main have diverged." >&2; \
		echo "Resolve the divergence (rebase/merge/reset) before publishing." >&2; \
		exit 1; \
	fi

.PHONY: ensure-main-exact
ensure-main-exact:
	@remote="$(PUBLISH_REMOTE)"; \
	if [ -z "$$remote" ]; then \
		echo "❌ [$(@)] error: PUBLISH_REMOTE is not set" >&2; \
		exit 1; \
	fi; \
	local_head=$$(git rev-parse HEAD); \
	remote_head=$$(git rev-parse "$$remote/main"); \
	if [ "$$local_head" != "$$remote_head" ]; then \
		echo "❌ [$(@)] error: local main ($$local_head) is not $$remote/main ($$remote_head)" >&2; \
		exit 1; \
	fi; \
	echo "✓ [$(@)] local main is exactly in sync with $$remote/main";

.PHONY: forbid-extra-local-commits
forbid-extra-local-commits:
	@remote="$(PUBLISH_REMOTE)"; \
	if [ -z "$$remote" ]; then \
		echo "❌ [$(@)] error: PUBLISH_REMOTE is not set" >&2; \
		exit 1; \
	fi; \
	if git log "$$remote/main"..HEAD --oneline | grep -q .; then \
		echo "❌ [$(@)] error: you have local commits not on $$remote/main" >&2; \
		exit 1; \
	fi; \
	echo "✓ [$(@)] no extra local commits on $$remote/main";

.PHONY: prepublish-checks
prepublish-checks: must-be-on-main must-have-publish-remote-set-correctly ensure-main-exact ensure-main-in-sync forbid-extra-local-commits check-git-clean

#
# make publish-advice [PKG=curv|curvpyutils|curvtools]
# example: make publish-advice PKG=curvtools
#
# Just runs a script telling you which dependent packages are out of date
# given that you want to publish the given package (e.g., curvtools in the
# example above).
#
.PHONY: publish-advice
publish-advice:
	@set -euo pipefail; \
	PKG=$${PKG:-}; \
	if [ -z "$$PKG" ]; then \
		echo "❌ [$(@)] error: PKG= must be specified (curv|curvtools|curvpyutils)"; \
		exit 1; \
	fi;
	@$(SCRIPT_GET_PUBLISH_DEPS) $(PKG) -v

#
# make publish [PKG=curv|curvpyutils|curvtools|all] [LEVEL=patch|minor|major]
# example: make publish PKG=curvpyutils LEVEL=minor
# - defaults: PKG=all, LEVEL=patch
#
.PHONY: publish
publish: prepublish-checks fetch-latest-tags build test
	@set -euo pipefail; \
	LEVEL=$${LEVEL:-patch}; \
	: "$${PKG:?Set PKG to one of: curvpyutils|curv|curvtools|all}"; \
	CURV_VER_MAJMINPTCH=$${CURV_VER_MAJMINPTCH:-$$($(SCRIPT_CHK_LATEST_VER) curv -L)}; \
	CURVTOOLS_VER_MAJMINPTCH=$${CURVTOOLS_VER_MAJMINPTCH:-$$($(SCRIPT_CHK_LATEST_VER) curvtools -L)}; \
	CURVPYUTILS_VER_MAJMINPTCH=$${CURVPYUTILS_VER_MAJMINPTCH:-$$($(SCRIPT_CHK_LATEST_VER) curvpyutils -L)}; \
	echo "🔄 Checking readme.md for out-of-date version numbers..."; \
	echo "  👉 Initial value of CURV_VER_MAJMINPTCH: $$CURV_VER_MAJMINPTCH"; \
	echo "  👉 Initial value of CURVTOOLS_VER_MAJMINPTCH: $$CURVTOOLS_VER_MAJMINPTCH"; \
	echo "  👉 Initial value of CURVPYUTILS_VER_MAJMINPTCH: $$CURVPYUTILS_VER_MAJMINPTCH"; \
	case "$$PKG" in \
	  all) ORDER="curvpyutils curv curvtools" ;; \
	  curv|curvtools|curvpyutils) ORDER="$$($(SCRIPT_GET_PUBLISH_DEPS) $(PKG))" ;; \
	  *) echo "Unknown PKG='$$PKG'"; exit 1 ;; \
	esac; \
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
	  # Extract version from tag and export to environment \
	  ver=$$(printf '%s' "$$tag" | sed -E "s/^$${pfx}//"); \
	  case "$$pfx" in \
	    curv-v) CURV_VER_MAJMINPTCH=$$ver ;; \
	    curvtools-v) CURVTOOLS_VER_MAJMINPTCH=$$ver ;; \
	    curvpyutils-v) CURVPYUTILS_VER_MAJMINPTCH=$$ver ;; \
	    *) echo "Unknown package prefix: $$pfx"; exit 1 ;; \
	  esac; \
	  \
	  echo "🔄 Checking readme.md for out-of-date version numbers..."; \
	  echo "  👉 CURV_VER_MAJMINPTCH: $$CURV_VER_MAJMINPTCH" 1>&2; \
	  echo "  👉 CURVTOOLS_VER_MAJMINPTCH: $$CURVTOOLS_VER_MAJMINPTCH" 1>&2; \
	  echo "  👉 CURVPYUTILS_VER_MAJMINPTCH: $$CURVPYUTILS_VER_MAJMINPTCH" 1>&2; \
	  CURV_VER_MAJMINPTCH=$$CURV_VER_MAJMINPTCH CURVTOOLS_VER_MAJMINPTCH=$$CURVTOOLS_VER_MAJMINPTCH CURVPYUTILS_VER_MAJMINPTCH=$$CURVPYUTILS_VER_MAJMINPTCH $(SCRIPT_SUBST) $(SCRIPT_SUBST_OPTS) readme.md \
			&& { echo "✔️ No change needed to readme.md for $$tag release"; \
				 echo "🔄 Committing and pushing empty commit to trigger CI for $$tag release..."; \
				 commit_msg="chore(release): prepare $$name for $$tag release"; \
				 git commit --allow-empty -m "$$commit_msg" && git push $(REMOTE) HEAD; \
				 echo "🔄 Waiting for CI to pass on '$$commit_msg'..."; \
				 $(SCRIPT_WAIT_CI) || { echo "Error: CI failed on '$$commit_msg'"; exit 1; }; \
			   } \
			|| { echo "✓ Updated readme.md with new version numbers for $$tag release"; \
				readme_commit_msg="chore(release): update readme.md to next version numbers before publishing $$tag release"; \
				git add readme.md; \
				git commit -m "$$readme_commit_msg" || { echo "❌ Failed to commit changes"; exit 1; }; \
				echo "🔄 Committing and pushing empty commit to trigger CI for $$tag release..."; \
				commit_msg="chore(release): prepare $$name for $$tag release"; \
				git commit --allow-empty -m "$$commit_msg" && git push $(REMOTE) HEAD; \
				git push $(REMOTE) HEAD || { echo "❌ Failed to push commit; please do it manually"; exit 1; }; \
				echo "🔄 Waiting for CI to pass on '$$commit_msg'..."; \
				$(SCRIPT_WAIT_CI) || { echo "Error: CI failed on '$$commit_msg'"; exit 1; }; \
				}; \
	  \
	  echo "🔥 Tagging $$name → $$tag"; \
	  git tag -a "$$tag" -m "Release ($$name): $$tag"; \
	  echo "📣 Tagged PKG=$$name (level=$$LEVEL, tag=$$tag)."; \
	done; \
	\
	echo "🔄 Tagged all packages and pushing to remote with CI waiting for success..."; \
	git push $(REMOTE) --tags || { echo "Error: Failed to push tags"; exit 1; }; \
	sleep 5; \
	$(SCRIPT_WAIT_CI) || { echo "Error: CI failed on push of tags"; exit 1; }; \
	\
	echo "🔄 Waiting for PyPI to update showing latest versions..."; \
	wait_for_pypi_update() { \
		local pkg_name="$$1"; \
		local expected_ver="$$2"; \
		local script_cmd="$(SCRIPT_CHK_LATEST_VER) $$pkg_name -L"; \
		echo "⏳ Waiting for PyPI $$pkg_name to show version $$expected_ver"; \
		while true; do \
			local current_ver=$$($$script_cmd 2>/dev/null || echo "error"); \
			if [ "$$current_ver" = "$$expected_ver" ]; then \
				echo "✓ PyPI $$pkg_name is now at expected version $$expected_ver"; \
				break; \
			else \
				echo "✗ PyPI $$pkg_name currently shows: $$current_ver (expecting: $$expected_ver)"; \
				sleep 5; \
			fi; \
		done; \
	}; \
	wait_for_pypi_update curvpyutils "$$CURVPYUTILS_VER_MAJMINPTCH"; \
	wait_for_pypi_update curv "$$CURV_VER_MAJMINPTCH"; \
	wait_for_pypi_update curvtools "$$CURVTOOLS_VER_MAJMINPTCH"; \
	echo "✅ All PyPI packages are now at the expected versions";

#
# make untag PKG=curvtools [VER=0.0.6]
# Delete tags for PKG that are newer than VER.
# If VER not specified, use latest published version from PyPI.
# VER must not be older than the latest published version on PyPI; otherwise we die with error.
# PKG is required.
#
.PHONY: untag
untag: check-git-clean
	@set -e; \
	PKG=$${PKG:-}; \
	if [ -z "$$PKG" ]; then \
		echo "❌ [$(@)] error: PKG= must be specified (curv|curvtools|curvpyutils)"; \
		exit 1; \
	fi; \
	# Always get the latest published version for safety \
	echo "Getting latest published version for $$PKG..."; \
	PUBLISHED=$$($(SCRIPT_CHK_LATEST_VER) -L "$$PKG"); \
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
show: fetch-latest-tags
	@set -e; \
	echo "Showing all versions for each package..."; \
	echo ""; \
	for p in curv curvtools curvpyutils; do \
		$(SCRIPT_CHK_LATEST_VER) "$$p" -pb; \
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
	@echo "  make setup                     - Setup dev env, install packages (editable), and"
	@echo "                                   install CLI tools into your shell via uv"
	@echo ""
	@echo "Building and running tests:"
	@echo "  make build                     - Build the packages"
	@echo "  make test                      - Run the tests"
	@echo "  make test-unit                 - Run the unit tests"
	@echo "  make test-e2e                  - Run the CLI e2e tests"
	@echo "  make clean                     - Clean the project"
	@echo ""
	@echo "Publishing to PyPI:"
	@echo "  make publish-advice PKG=<curv|curvtools|curvpyutils>"
	@echo "                                 - Get advice on which other packages need to be published"
	@echo "                                   along with your desired publishing of `PKG`"
	@echo "  make publish PKG=<curv|curvtools|curvpyutils> LEVEL=<patch|minor|major>"
	@echo "                                 - Publish the package with the given level bump"
	@echo "  make untag                     - Undo a tag"
	@echo "  make show                      - Show the PyPI published versions and local tags"
	@echo "  make show-publish-status       - Show the CI status of the latest tag for each package"
	@echo ""
	@echo "Informational commands:"
	@echo "  make show                      - Show the PyPI published versions and local tags"
	@echo "  make show-publish-status       - Show the CI status of the latest tag for each package"
	@echo "  make help                      - Show this help message"
	@echo ""
	@echo "For more details, see the contributing guide:"
	@echo "  https://github.com/curvcpu/curv-python/blob/main/.github/CONTRIBUTING.md"
