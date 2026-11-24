# GitHub activity tool (gh CLI)

## Objective
Add a `get_github_activity` tool so PRs opened, reviews (including approvals) and PR comments can feed timesheet drafting and Tempo uploads.

## Why
Code review work leaves no commits, so `get_historical_git_activity` misses it.

## Scope
- `mcp-server/server.py`: new tool backed by the `gh` CLI (GraphQL `contributionsCollection` for PRs and reviews; search + comments endpoints for PR comments).
- `.pi/extensions/tempo-mcp`: register `tempo_get_github_activity`.
- Skills and README: use the tool, document `gh` as a requirement for this tool only.

## Constraints
- Backends selected by `GITHUB_ACTIVITY_BACKEND` (`auto` default: token if set else `gh`; `gh`; `token`; `off` disables the tool). Requested by the user.
- Reads the account active in `gh`; times reported in UTC.
- Artifacts in English.

## Resolved settings
- TDD: not enabled; ordinary functional checks.
- Runner: `uv run --directory mcp-server pytest`, `npm test` and `npm run typecheck` in the extension, `uv run --directory mcp-server pytest ../test_installer.py`.
- Branch: `feat/github-activity-tool`.

## Tasks
- [x] T1 Server tool + tests. Route: direct inline (single cohesive module, understood pattern).
- [x] T2 Pi extension registration + test.
- [x] T3 README and skills updates.
- [x] T4 `GITHUB_TOKEN` backend: `GhCliClient` / `GithubTokenClient` behind `get_github_client()`, `off` switch, tests, README section. Route: direct inline (one module, understood refactor).

## Verification
- Server tests 23 passed; extension tests 3 passed, typecheck clean; installer tests 54 passed.
- Live: token backend (borrowing the existing `gh` OAuth token in memory, never printed) returned output identical to the `gh` backend over 2026-11-10..2026-11-24 (18 events); an invalid token returned a clear 401 error and the token never appears in output.

## Known gaps
- `mcp-server/.env.example` could not be updated (blocked by the user's permission settings); the settings are documented in the README only.
- Not tested live: a fine-grained PAT's scope behavior (the live run used an OAuth token with `repo`).
