---
name: catch-up-timesheet
description: Use when the user asks to log time for the past week, last 3 weeks, or catch up on old unlogged time. Automates historical git scanning across all workspace repos and generates a bulk timesheet.
---

# Catch-Up Timesheet Logger

## Overview
This skill acts as a historical time-tracking assistant. It scans all repositories on the user's PC (within configured workspaces), finds commits for a specific date range, helps match those commits to Jira tickets, and bulk logs the time to Tempo.

## Workflow

### Step 1: Workspace Check
Check if the user has workspace directories configured by calling the `get_historical_git_activity` tool with a simple test (e.g., since "1 day ago").
- If the tool says "No workspace directories configured", ask the user: **"I need to know where your code lives to scan your history. What is the absolute path to your main projects folder (e.g., D:\python\workbooks)?"**
- When the user provides the path, use the `add_workspace_dir` tool to save it. You can repeat this if they have multiple folders.

### Step 2: The Historical Scan
Ask the user for the date range they want to catch up on (e.g., "last 3 weeks", "from 2026-06-01 to 2026-06-15").
- Call the `get_historical_git_activity` tool using the provided `since` and `until` parameters.
- Analyze the output. Group the commits by day.

### Step 3: Ticket Matching
For each day of activity:
1. Show the user a summary of what they did that day.
2. Ask them which Jira Ticket it belongs to and how many hours it took.
   - **Important:** If they don't know the ticket ID, ask them for the project name and use the `search_jira_issues` tool to find the exact Ticket Key for them.

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
3. Call the `tempo-mcp_log_tempo_work` tool for each entry.
4. Report the massive success back to the user!
