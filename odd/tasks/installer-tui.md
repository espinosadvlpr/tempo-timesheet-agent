# Installer TUI (questionary + rich)

## Objective
Replace the plain `input()`/`print()` prompts of the setup wizard with a polished TUI built on `questionary` and `rich`, without changing installer behavior or moving off Python.

## Why
The wizard should feel professional. A Go rewrite was rejected: the MCP server is Python/uv, the WSL/APPDATA detection is fragile and already tested, and there is no distribution need today.

## Scope
- `setup.py`: UI layer only (menus, token prompts, agent selection, summaries).
- `installer.py`: untouched unless a pure helper is needed.
- `test_installer.py`: keep existing tests green; add tests for the new UI seam and the fallback.
- Dependency declaration for `questionary` and `rich`; README update.

## Constraints
- `python setup.py` must still work when `questionary`/`rich` are missing (graceful fallback to plain prompts, with a hint to install them).
- Tokens are secrets: use password-style prompts, never echo them in summaries.
- Artifacts (code, comments, UI copy, docs) in English.
- Planning heuristic: ~400 authored changed lines per task; advisory only.

## Resolved settings
- TDD: not enabled (no project config); run ordinary functional checks.
- Runner: `uv run --directory mcp-server pytest ../test_installer.py`
- Delivery strategy: ask-on-risk. Push with `gh` account `espinosadvlpr`, then switch back to `despinosaqualit`.
- Branch: `feat/installer-tui` (from `main`, which was 0/0 vs `origin/main`).

## Tasks
- [x] T1 TUI layer in `wizard_ui.py` + `setup.py` with fallback + tests. Route: delegated writer (trigger: 2+ non-trivial files). Commit `d2e38e7`.
- [x] T2 `requirements-installer.txt` + README install section. Same writer and commit.
- [ ] T3 Verify, push as `espinosadvlpr`, restore `despinosaqualit`. Verification done; push pending.

## Acceptance criteria
- Existing tests pass; new tests cover the UI seam and the missing-dependency fallback.
- Wizard menu, token entry and agent selection use questionary/rich when available.
- No behavior change in what gets written to configs.

## Progress
- Branch created. Explored: setup.py (398 lines), installer.py, test_installer.py (491 lines).
- Writer delivered T1+T2 (374 insertions, 81 deletions across 5 files).
- Verification observed by the parent: `uv run --directory mcp-server pytest ../test_installer.py` -> 53 passed; `python3 -c "import setup"` -> ok; pty smoke test with real questionary/rich -> panel, colored tags, literal markup and spinner rendered, `_tui()` truthy.
- Review: RDD is off (global), so no native review. Assessed tier: not run.
- Known limits: interactive arrow-key prompts were not driven by a human; the spinner wraps `npm ci`, whose own output may interleave on a TTY.

## Next step
Push `feat/installer-tui` as `espinosadvlpr`, restore `despinosaqualit`, then decide PR/merge with the user.
