# <repo-root>/Makefile
SHELL := /usr/bin/env bash
.SHELLFLAGS := -euo pipefail -c

UV ?= uv
VENVDIR ?= .venv
PYTEST := uv run pytest
PYTEST_OPTS := -q --numprocesses auto
PACKAGES := packages/curv packages/curvtools packages/curvpyutils
REMOTE ?= origin
PKG_CURV := packages/curv
PKG_CURVTOOLS := packages/curvtools
PKG_CURVPYUTILS := packages/curvpyutils
SCRIPT_GH_RUN_ID := scripts/get_gh_run_id_for_last_commit.sh
SCRIPT_WAIT_CI := scripts/wait_ci.py
SCRIPT_SUBST := curv-subst
SCRIPT_SUBST_OPTS := -f -1 -m
SCRIPT_CHK_LATEST_VER := scripts/chk-latest-version.py
SCRIPT_TOUCH_STAMP_FILES := scripts/touch_stamp_files.py

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
	@echo "🤔 Fetching latest tags from remote '$(REMOTE)'..."
	@git fetch $(REMOTE) --tags --quiet

.PHONY:  setup-precommit
setup-precommit:
	@echo "🔄 Installing pre-commit hooks for this repo..."
	@$(UV) run pre-commit install

.PHONY: setup
setup: install-min fetch-latest-tags setup-precommit
	@#SETUPTOOLS_SCM_PRETEND_VERSION=$$($(SCRIPT_CHK_LATEST_VER) curvtools -Gb) $(UV) tool install --editable $(PKG_CURVTOOLS)
	@$(UV) tool install --editable $(PKG_CURVTOOLS)
	@echo "✓ All CLI tools (editable) available on PATH"
	@# Edit shell's rc file to keep the PATH update persistent
	@$(UV) tool update-shell -q || true

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
unsetup: unsetup-editable-installs clean-venv clean
	@$(UV) tool uninstall --all -q
	@echo "✅ Removed CLI tools from uv tool environment"


.PHONY: build
build:
	for p in $(PACKAGES); do \
		$(UV) run -m build --sdist --wheel $$p; \
	done

.PHONY: clean
clean:
	@find . -type d -name __pycache__ -prune -exec rm -rf {} +
	@rm -rf build dist .pytest_cache .ruff_cache $(VENVDIR)
	@for p in $(PACKAGES); do \
		rm -rf $$p/dist $$p/build $$p/*.egg-info $$p/src/*.egg-info ; \
	done

.PHONY: clean-venv
clean-venv: clean
	@$(RM) -rf $(VENVDIR)/bin/python
	@echo "✅ Removed $(VENVDIR)/bin/python"

.PHONY: check-git-clean
check-git-clean:
	@test -z "$$(git status --porcelain)" || (echo "Error: git working tree is not clean. Commit/stash first."; exit 1)

# # Default value for README_VERSION_SRC (when readme.md is built directly)
# # Set README_VERSION_SRC to -V when building advance-readme-to-next-version
# README_VERSION_SRC ?= -L
# .PHONY: advance-readme-to-next-version
# advance-readme-to-next-version: README_VERSION_SRC=-V
# advance-readme-to-next-version: readme.md

# readme.md: build
# 	@echo "🔄 Checking $@ for out-of-date version numbers...";
# 	@CURV_VER_MAJMINPTCH=$$($(SCRIPT_CHK_LATEST_VER) curv $(README_VERSION_SRC)) \
# 		CURVTOOLS_VER_MAJMINPTCH=$$($(SCRIPT_CHK_LATEST_VER) curvtools $(README_VERSION_SRC)) \
# 		CURVPYUTILS_VER_MAJMINPTCH=$$($(SCRIPT_CHK_LATEST_VER) curvpyutils $(README_VERSION_SRC)) \
# 		$(SCRIPT_SUBST) $(SCRIPT_SUBST_OPTS) $@ \
# 			&& echo "✔️ No change needed for $@" \
# 			|| { echo "❌ Updated $@ with new version numbers"; \
# 				commit_msg="chore(release): update readme.md to next version numbers before publishing"; \
# 				git add $@; \
# 				git commit -m "$$commit_msg" || { echo "❌ Failed to commit changes"; exit 1; }; \
# 				git push $(REMOTE) HEAD || { echo "❌ Failed to push commit; please do it manually"; exit 1; }; \
# 				echo "🔄 Waiting for CI to pass on '$$commit_msg'..."; \
# 				$(SCRIPT_WAIT_CI) $$($(SCRIPT_GH_RUN_ID)) || { echo "Error: CI failed on '$$commit_msg'"; exit 1; }; \
# 				echo "✅ Pushed commit to update $@ with new version numbers before publishing"; \
# 				echo "🔄 Please re-run your make command again and it will now succeed"; \
# 				exit 1; };


#
# make publish [PKG=curv|curvpyutils|curvtools|all] [LEVEL=patch|minor|major]
# example: make publish PKG=curvpyutils LEVEL=minor
# - defaults: PKG=all, LEVEL=patch
#
.PHONY: publish
publish: fetch-latest-tags check-git-clean test
	@set -euo pipefail; \
	LEVEL=$${LEVEL:-patch}; \
	: "$${PKG:?Set PKG to one of: curvpyutils|curv|curvtools|all}"; \
	CURV_VER_MAJMINPTCH=$${CURV_VER_MAJMINPTCH:-$$($(SCRIPT_CHK_LATEST_VER) curv -L)}; \
	CURVTOOLS_VER_MAJMINPTCH=$${CURVTOOLS_VER_MAJMINPTCH:-$$($(SCRIPT_CHK_LATEST_VER) curvtools -L)}; \
	CURVPYUTILS_VER_MAJMINPTCH=$${CURVPYUTILS_VER_MAJMINPTCH:-$$($(SCRIPT_CHK_LATEST_VER) curvpyutils -L)}; \
	case "$$PKG" in \
	  all) ORDER="curvpyutils curv curvtools" ;; \
	  curv|curvtools|curvpyutils) ORDER="$$PKG" ;; \
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
	  case "$$pfx" in \
	    curv-v) CURV_VER_MAJMINPTCH=$$ver ;; \
	    curvtools-v) CURVTOOLS_VER_MAJMINPTCH=$$ver ;; \
	    curvpyutils-v) CURVPYUTILS_VER_MAJMINPTCH=$$ver ;; \
	    *) echo "Unknown package prefix: $$pfx"; exit 1 ;; \
	  esac; \
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
	  echo "🔄 Checking readme.md for out-of-date version numbers..."; \
	  CURV_VER_MAJMINPTCH=$${CURV_VER_MAJMINPTCH:-$$($(SCRIPT_CHK_LATEST_VER) curv -V)}; \
		CURVTOOLS_VER_MAJMINPTCH=$${CURVTOOLS_VER_MAJMINPTCH:-$$($(SCRIPT_CHK_LATEST_VER) curvtools -V)}; \
		CURVPYUTILS_VER_MAJMINPTCH=$${CURVPYUTILS_VER_MAJMINPTCH:-$$($(SCRIPT_CHK_LATEST_VER) curvpyutils -V)}; \
		$(SCRIPT_SUBST) $(SCRIPT_SUBST_OPTS) readme.md \
			&& echo "✔️ No change needed to readme.md for $$tag release" \
			|| { echo "✅ Updated readme.md with new version numbers for $$tag release"; \
				readme_commit_msg="chore(release): update readme.md to next version numbers before publishing $$tag release"; \
				git add readme.md; \
				git commit -m "$$readme_commit_msg" || { echo "❌ Failed to commit changes"; exit 1; }; \
				git push $(REMOTE) HEAD || { echo "❌ Failed to push commit; please do it manually"; exit 1; }; \
				echo "🔄 Waiting for CI to pass on '$$readme_commit_msg'..."; \
				$(SCRIPT_WAIT_CI) $$($(SCRIPT_GH_RUN_ID)) || { echo "Error: CI failed on '$$readme_commit_msg'"; exit 1; }; \
				echo "✅ Pushed commit to update readme.md with new version numbers before publishing $$tag release"; \
				}; \
	  echo "🔄 Committing and pushing empty commit to trigger CI for $$tag release..."; \
	  commit_msg="chore(release): prepare $$name for $$tag release"; \
	  git commit --allow-empty -m "$$commit_msg" && git push $(REMOTE) HEAD; \
	  echo "🔄 Waiting for CI to pass on '$$commit_msg'..."; \
	  $(SCRIPT_WAIT_CI) $$($(SCRIPT_GH_RUN_ID)) || { echo "Error: CI failed on '$$commit_msg'"; exit 1; }; \
	  echo "🔥 Tagging $$name → $$tag"; \
	  git tag -a "$$tag" -m "Release ($$name): $$tag" && git push $(REMOTE) "$$tag"; \
	  echo "📣 Published PKG=$$name (level=$$LEVEL, tag=$$tag)."; \
	done; \
	git push $(REMOTE) --tags;

.PHONY: sync-published-stamps
sync-published-stamps:
	@$(SCRIPT_TOUCH_STAMP_FILES)

packages/%/.package_published_stamp.stamp: packages/%/.package_changed_stamp.stamp | sync-published-stamps
	@echo "🔄 $(notdir $*) needs republish"

.PHONY: publish-curv-patch
publish-curv-patch: packages/curv/src/curv/.package_published_stamp.stamp
	@$(MAKE) publish PKG=curv LEVEL=patch
.PHONY: publish-curvpyutils-patch
publish-curvpyutils-patch: packages/curvpyutils/src/curvpyutils/.package_published_stamp.stamp
	@$(MAKE) publish PKG=curvpyutils LEVEL=patch
.PHONY: publish-curvtools-patch
publish-curvtools-patch: packages/curvtools/src/curvtools/.package_published_stamp.stamp
	@$(MAKE) publish PKG=curvtools LEVEL=patch

# This is just a temporary rule that I've been using to test ./scripts/wait_ci.py...
.PHONY: push
push: fetch-latest-tags
	set -euo pipefail; \
	LEVEL=$${LEVEL:-patch}; \
	PKG=$${PKG:-curv}; \
	CURV_VER_MAJMINPTCH=$${CURV_VER_MAJMINPTCH:-$$($(SCRIPT_CHK_LATEST_VER) curv -L)}; \
	CURVTOOLS_VER_MAJMINPTCH=$${CURVTOOLS_VER_MAJMINPTCH:-$$($(SCRIPT_CHK_LATEST_VER) curvtools -L)}; \
	CURVPYUTILS_VER_MAJMINPTCH=$${CURVPYUTILS_VER_MAJMINPTCH:-$$($(SCRIPT_CHK_LATEST_VER) curvpyutils -L)}; \
	case "$$PKG" in \
	  all) ORDER="curvpyutils curv curvtools" ;; \
	  curv|curvtools|curvpyutils) ORDER="$$PKG" ;; \
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
	  case "$$pfx" in \
	    curv-v) CURV_VER_MAJMINPTCH=$$ver ;; \
	    curvtools-v) CURVTOOLS_VER_MAJMINPTCH=$$ver ;; \
	    curvpyutils-v) CURVPYUTILS_VER_MAJMINPTCH=$$ver ;; \
	    *) echo "Unknown package prefix: $$pfx"; exit 1 ;; \
	  esac; \
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
	  echo "🔄 Checking readme.md for out-of-date version numbers..."; \
	  CURV_VER_MAJMINPTCH=$${CURV_VER_MAJMINPTCH:-$$($(SCRIPT_CHK_LATEST_VER) curv -V)}; \
		CURVTOOLS_VER_MAJMINPTCH=$${CURVTOOLS_VER_MAJMINPTCH:-$$($(SCRIPT_CHK_LATEST_VER) curvtools -V)}; \
		CURVPYUTILS_VER_MAJMINPTCH=$${CURVPYUTILS_VER_MAJMINPTCH:-$$($(SCRIPT_CHK_LATEST_VER) curvpyutils -V)}; \
		$(SCRIPT_SUBST) $(SCRIPT_SUBST_OPTS) readme.md \
			&& echo "✔️ No change needed to readme.md for $$tag release" \
			|| { echo "✅ Updated readme.md with new version numbers for $$tag release"; \
				readme_commit_msg="chore(release): update readme.md to next version numbers before publishing $$tag release"; \
				git add readme.md; \
				git commit -m "$$readme_commit_msg" || { echo "❌ Failed to commit changes"; exit 1; }; \
				git push $(REMOTE) HEAD || { echo "❌ Failed to push commit; please do it manually"; exit 1; }; \
				echo "🔄 Waiting for CI to pass on '$$readme_commit_msg'..."; \
				$(SCRIPT_WAIT_CI) $$($(SCRIPT_GH_RUN_ID)) || { echo "Error: CI failed on '$$readme_commit_msg'"; exit 1; }; \
				echo "✅ Pushed commit to update readme.md with new version numbers before publishing $$tag release"; \
				}; \
	done
	@git push $(REMOTE) HEAD
	@$(SCRIPT_WAIT_CI) $$($(SCRIPT_GH_RUN_ID)) || { echo "Error: CI failed"; exit 1; };

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
		echo "Error: PKG= must be specified (curv|curvtools|curvpyutils)"; \
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
show:
	@set -e; \
	echo "Fetching all remote tags to make sure we're up to date..."; \
	git fetch origin --tags; \
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
	@echo "  make setup               - Setup dev env, install packages (editable), and"
	@echo "                             install CLI tools into your shell via uv"
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
