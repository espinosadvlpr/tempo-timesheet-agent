---
name: catch-up-timesheet
description: Use when the user asks to log time for the past week, last 3 weeks, or catch up on old unlogged time. Automates historical git scanning across all workspace repos and generates a bulk timesheet.
---

# Catch-Up Timesheet Logger

## Overview
This skill acts as a historical time-tracking assistant. It scans all repositories on the user's PC (within configured workspaces), finds commits for a specific date range, helps match those commits to Jira tickets, and bulk logs the time to Tempo.

## Workflow

### Step 1: Gather Requirements
Ask the user two things:
1. "What is the date range you want to catch up on? (e.g., 'last 3 weeks', 'from 2026-06-01 to 2026-06-15')"
2. "What are the absolute paths to the repositories you want to scan? (You can provide one or multiple, separated by commas. e.g., /projects/my-project, /projects/another-app)"

### Step 2: The Historical Scan
Once the user provides the date range and the repository paths:
- In Pi, call `tempo_get_historical_git_activity` using the provided `repo_paths`, `since`, and `until` parameters. In other supported clients, call the configured historical Git activity tool using those parameters.
- Also read the user's GitHub review work for the same range. In Pi, call `tempo_get_github_activity` with `since` and `until` (optionally `repos` as `owner/name` values). In other supported clients, call the configured GitHub activity tool. It returns PRs opened, reviews (including approvals) and PR comments with UTC timestamps. If it reports that `gh` is missing or not authenticated, tell the user once and continue with commits only.
- Analyze the output. Group commits and GitHub events by day. Treat review and comment activity as time spent on code review, and ask the user how long it took, since timestamps alone do not give a duration.

### Step 3: Ticket Matching
For each day of activity:
1. Show the user a summary of what they did that day.
2. Ask them which Jira Ticket it belongs to and how many hours it took.
   - **Important:** If they don't know the ticket ID or project key, search projects with the keyword they provide, then search issues in the identified project to find the exact Ticket Key. In Pi, use `tempo_search_jira_projects` followed by `tempo_search_jira_issues`. In other supported clients, use the configured Jira project and issue search tools.

### Step 4: Draft the Timesheet
1. For each entry, draft a highly technical, professional English description of the work.
2. Use the `write` or `edit` tool to append these rows to a local `timesheet.md` file (create it if it doesn't exist). Use `auto` for the Start Time column.

### Step 5: Review Phase
Display the drafted rows to the user.
- Ask: **"Here is the historical timesheet I drafted based on your commits. Does this look good to sync, or do you want to edit it first?"**
- **STOP HERE.** Do not sync until the user explicitly approves.

### Step 6: Sync to Tempo
Once the user approves:
1. Read the newly approved rows from `timesheet.md`.
2. **Calculate Start Times:** If the Start Time column is `auto`, calculate it sequentially for each individual day starting at `08:00:00`.
3. In Pi, call `tempo_log_work` for each entry. In other supported clients, call the configured Tempo work-log tool.
4. Report the massive success back to the user!
