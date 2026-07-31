---
name: daily-timesheet
description: Use when the user asks to "log my time", "update my timesheet", or "what did I do today?". Automates local timesheets, summarizes daily activity in technical English, and logs time to Tempo.
---

# Daily Timesheet Logger

## Overview
This skill acts as a proactive time-tracking assistant. It discovers what the user worked on today, helps them format it into a timesheet directly in professional English, allows for manual review, and pushes the data to Jira/Tempo via the MCP server.

## Workflow

### Step 1: File Verification
Check if `timesheet.md` exists in the current working directory.
- If it DOES NOT exist, use the `write` tool to create it with the following exact template:
  ```markdown
  # Daily Timesheet
  
  *Instructions for OpenCode: Read this table and use the `tempo-mcp_log_tempo_work` tool to upload each record to Tempo.*
  
  | Date       | Start Time | Ticket | Time | Description |
  |------------|------------|--------|------|-------------|
  ```

### Step 2: Activity Discovery
Figure out what the user did today in this project:
1. Run `bash` tool with: `git log --since="midnight" --oneline`
2. Run `bash` tool with: `git status`
*(If the directory is not a git repository or has no history, gracefully skip this and just ask the user what they worked on).*

### Step 3: The Interview
Ask the user:
1. "I see you worked on [summarize changes]. What Jira Ticket Key (e.g., SCHE-1) should I bill this to?"
2. "How many hours did you spend on this today?"

### Step 4: Draft the Timesheet
1. Once the user provides the Ticket Key and Hours, draft a 1-2 sentence description directly in **professional, highly technical English**.
2. Use the `edit` or `bash` tool to append the new row to the local `timesheet.md` table using today's date (YYYY-MM-DD) and `auto` for the Start Time.

### Step 5: Review Phase
Display the exact row you just added to the file.
- Ask the user: **"I have updated timesheet.md with this entry. Does this look good to sync, or do you want to edit it first?"**
- **STOP HERE.** Do not sync until the user explicitly approves.

### Step 6: Sync to Tempo
Once the user approves:
1. Read the newly approved rows from `timesheet.md`.
2. **Calculate Start Times:** If the Start Time column is `auto`, calculate it sequentially for that day. 
   - Start the first task of the day at `08:00:00`.
   - For subsequent tasks on the same date, add the previous task's duration to its start time to determine the new start time (e.g., Task 1: 08:00:00 + 5h = Task 2 starts at 13:00:00).
   - If a user manually provides a time (e.g., `15:00:00`), use that instead.
3. Call the `tempo-mcp_log_tempo_work` tool with the Ticket Key, Hours, Date, Description, and calculated Start Time.
4. Report the success back to the user!
