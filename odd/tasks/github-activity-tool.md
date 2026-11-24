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
- `gh` only for now. Follow-up requested by the user: optional `GITHUB_TOKEN` path, and a way to disable the CLI option without the tool being usable.
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

## Verification
- Server tests 19 passed; extension tests 3 passed, typecheck clean; installer tests 54 passed.
- Live smoke test against the real `gh` session returned comments grouped by day.

## Next step
- Follow-up: `GITHUB_TOKEN` fallback and a switch to turn the `gh` path off.
