# Global Tempo Pi install

## Objective
Install Tempo's Pi extension and both timesheet skills for every Pi session, independently of the working repository; apply the new installer to this user's Pi configuration.

## Problem and rationale
The current Pi installer only installs npm dependencies inside this checkout. Project-local resource discovery makes the tools and skills disappear in sessions opened elsewhere, despite their working here. The extension also requires `uv` but Pi installation does not check for it.

## Scope and constraints
- Update `setup.py` to install global Pi resources through the user-level agent directory, respecting `PI_CODING_AGENT_DIR`; preserve existing settings and unrelated extensions/skills.
- Keep the extension at its source path so its relative MCP-server resolution and credentials in `mcp-server/.env` remain intact. Do not add an `mcpServers` entry or expose credentials.
- Add deterministic installer tests for idempotence, conflicts/failures, and resource scope; update README documentation.
- Run the installer for the current user only after its tests pass, then verify both resource registrations from an unrelated repository without creating worklogs.
- Do not change unrelated user settings, publish time entries, push, or open a PR.

## Tasks
- [x] T1 — Implement and test global Pi resource installation, document it, activate it for this user, and verify it from another repository. Evidence: 40 installer tests and 3 extension tests passed; fresh in-memory Pi SDK sessions in GradeSkill and Tempo each loaded two skills and four tools without Tempo diagnostics; user-level settings retained other keys. Commit: `f0d1b25` (`feat(pi): install Tempo tools and skills for every session`).

## Acceptance and checks
- `python3 -B -m unittest test_installer` passes with new regression coverage and an observed test-first RED/GREEN cycle.
- `.pi/extensions/tempo-mcp` `npm run check` passes.
- User-level Pi settings contain the extension and both skills (or the skills directory), without losing any existing configuration; a repeated install is idempotent.
- A fresh Pi session from GradeSkill can discover the two skills and four tools; if fresh-session testing is unavailable, report the limitation rather than claiming it.
- Preserve repository's unrelated pre-existing `.codegraph/` untracked state. Record commit ID and any skipped checks.

## Progress
Branch: `feat/global-tempo-pi-install`. T1 completed. Test-first RED/GREEN observed by the bounded writer; independent GREEN checks passed. `npm ci` reported four dependency advisories (one low, one moderate, two high), not changed under this task. Current interactive sessions outside the new SDK verification require restart or `/reload`; no worklogs were created. Next: user reviews branch and optionally addresses dependency advisories separately.
