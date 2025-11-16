# CLAUDE.md

## Repo overview

- This is a **monorepo** that publishes three pip packages:
  - `curv` under `packages/curv`
  - `curvpyutils` under `packages/curvpyutils`
  - `curvtools` under `packages/curvtools`

## Running tests

- To run **all tests**, from the repo root:
  - `make test`

## PR titles and bodies

When you need to generate a PR title and PR body from a feature branch:

1. Inspect everything that changed since it diverged from `main`:
   - `git log --stat main..HEAD`
   - `git diff main..HEAD | cat`

2. Based on that output:
   - Create a **clear, succinct PR title**.
   - Write the **PR body** as **concise Markdown bullet points** summarizing the changes.
