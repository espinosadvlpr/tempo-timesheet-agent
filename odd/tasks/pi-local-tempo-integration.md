# Local Pi Tempo Integration

## Objective
Make the Tempo timesheet workflow usable from Pi when this repository is opened as a trusted local project, without publishing or installing a Pi package.

## Problem
The current installer writes an unsupported `mcpServers` configuration for Pi and links skills to an undiscovered path. Pi needs project-local resource discovery and a native extension that adapts the existing stdio MCP server.

## Scope
- Add trusted project-local Pi discovery for the existing skills and a Tempo extension.
- Add a TypeScript Pi extension that starts the existing Python stdio MCP server and exposes its four supported operations as Pi-native tools.
- Make the Python server load its own `.env` file regardless of Pi's working directory.
- Correct the installer, documentation, templates, and tests so they describe the local Pi route accurately.

## Constraints
- Keep the repository local; do not create a distributable Pi package.
- Reuse `mcp-server/server.py`; do not duplicate Jira or Tempo API logic.
- Do not store credentials in Pi settings or tracked files.
- Preserve support for the other existing agent installers.
- No commit without explicit user authorization.

## TDD and verification
- Mode: off (no repository or session TDD configuration found).
- Source: repository inspection.
- Runners: `uv run --directory mcp-server pytest ../test_installer.py test_server.py`; Node checks selected after the extension test layout exists.

## Delivery strategy
- Strategy: ask-on-risk.
- Forecast: approximately 300 authored changed lines; below the 400-line review-slice threshold.
- Work-unit commits: deferred; explicit user authorization is required.

## Tasks

- [x] **T1 — Define local Pi resources and installer behavior**
  - Route: delegated direct (multi-file write rule).
  - Allowed surfaces: `.pi/settings.json`, `installer.py`, `setup.py`, `test_installer.py`.
  - Acceptance: opening this repository in trusted Pi discovers the root `skills/` directory and the local extension; the setup wizard no longer emits an unsupported Pi MCP configuration or links to `~/.pi/skills`.
  - Checks: focused Python installer tests; readback of the generated Pi configuration.

- [x] **T2 — Implement the Pi-to-Tempo stdio adapter**
  - Route: delegated direct (multi-file write rule).
  - Allowed surfaces: `.pi/extensions/tempo-mcp/index.ts`, `.pi/extensions/tempo-mcp/package.json`, `.pi/extensions/tempo-mcp/package-lock.json`, `.pi/extensions/tempo-mcp/test/**`, `mcp-server/server.py`, `mcp-server/pyproject.toml`.
  - Acceptance: Pi registers native tools for the four MCP operations, starts the Python server lazily, forwards arguments and results, shuts down cleanly, and the Python server loads `mcp-server/.env` by explicit path.
  - Checks: extension unit/type checks and focused Python server tests.

- [x] **T3 — Align user guidance and validate the local workflow**
  - Route: delegated direct (multi-file write rule).
  - Allowed surfaces: `README.md`, `timesheet.template.md`, `skills/daily-timesheet/SKILL.md`, `skills/catch-up-timesheet/SKILL.md`, `test_installer.py`, `.pi/extensions/tempo-mcp/test/**`.
  - Acceptance: documentation and skills refer to Pi-native Tempo tool names and explain trusted-project setup; tests cover the corrected Pi installer path and adapter behavior.
  - Checks: all focused test suites and manual static readback of local setup instructions.

- [x] **T4 — Install Pi extension dependencies from the setup wizard**
  - Route: delegated direct (multi-file write rule).
  - Allowed surfaces: `setup.py`, `test_installer.py`, `README.md`.
  - Acceptance: choosing Pi runs deterministic local dependency installation with `npm ci` in `.pi/extensions/tempo-mcp`; a missing npm executable produces actionable guidance without changing global Pi configuration; installer tests cover both outcomes.
  - Checks: focused installer tests and an observed local `npm ci` run.

## Progress and evidence
- 2026-03-31: Feature branch `feat/pi-local-tempo-integration` created from `main` at `6e53e27`.
- 2026-03-31: T1 worker completed `.pi/settings.json`, `installer.py`, `setup.py`, and `test_installer.py`; `uv run --directory mcp-server pytest ../test_installer.py` passed (29 tests).
- 2026-03-31: Native risk assessment was unavailable; independent verification was required before T1 could close.
- 2026-03-31: T1 independent verification passed: `uv run --directory mcp-server pytest ../test_installer.py` reported 29 passing tests. Parent readback confirmed the project-local skills configuration and no unsupported MCP configuration.
- 2026-03-31: T2 worker added the local stdio adapter, its package metadata, TypeScript tests, and explicit server-local `.env` loading. Worker checks passed: `npm run typecheck`, `npm test` (3 tests), and `uv run --directory mcp-server pytest test_server.py` (7 tests). No live Jira/Tempo request was made.
- 2026-03-31: Native risk assessment was unavailable; independent verification was required before T2 could close.
- 2026-03-31: T2 independent verification passed: `npm run check` completed type checking and 3 tests; `uv run --directory mcp-server pytest test_server.py` reported 7 passing tests. The verifier confirmed all tests mock external boundaries and make no live Jira/Tempo requests.
- 2026-03-31: T3 worker aligned the README, template, and skills. Parent readback found and corrected the README Python requirement to match `mcp-server/pyproject.toml` (Python 3.13+). Worker checks passed: `uv run --directory mcp-server pytest ../test_installer.py test_server.py` (36 tests) and `npm run check` (type checking plus 3 tests).
- 2026-03-31: Native risk assessment was unavailable; independent verification was required before T3 could close.
- 2026-03-31: T3 independent verification passed: the README and skills accurately describe the trusted project-local Pi route, exact native tool names, Python 3.13+, and credential boundaries. `uv run --directory mcp-server pytest ../test_installer.py test_server.py` reported 36 passing tests; `npm run check` completed type checking and 3 tests.
- 2026-03-31: T4 worker added local `npm ci` setup with successful, missing-npm, and failed-install test coverage. Worker checks passed: installer tests (32 tests), `npm ci` (268 packages), and extension typecheck plus 3 tests. npm reported one low-severity audit finding and four unapproved dependency install scripts; no remediation was attempted.
- 2026-03-31: Native risk assessment was unavailable; independent verification was required before T4 could close.
- 2026-03-31: T4 independent verification passed: `uv run --directory mcp-server pytest ../test_installer.py` reported 32 passing tests; `npm ci` installed 268 local packages; `npm run check` completed TypeScript checking and 3 tests. npm reported one low-severity audit finding and dependency install-script warnings; no remediation was attempted.
- Engram mirror: pending because the local Engram provider is unavailable.

## Next step
Implementation committed on `feat/pi-local-tempo-integration` as `feat(pi): add local Tempo tools integration`. Open the trusted repository in Pi and test the local Tempo workflow.
