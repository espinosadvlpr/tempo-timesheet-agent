# Tempo-Timesheet-Agent

An automated, AI-driven time-tracking workflow for software engineers using the **Jira Tempo app**.

This project combines an **MCP Server** (Model Context Protocol) and an **OpenCode Skill** to completely automate logging your daily work directly to Jira Tempo. Instead of clicking through menus and guessing how many hours you spent, you just tell your AI agent: *"Log my time"*. 

*(Note: While the MCP server works with any MCP client like Claude Desktop or Cursor, the automation Skill provided is currently designed for [OpenCode](https://opencode.ai/).)*

## 🚀 Features

*   **Proactive Discovery:** Automatically scans your local `git log` and `git status` to find what you worked on today.
*   **Intelligent Drafting:** Translates your quick notes (in any language) into professional, highly technical English descriptions.
*   **Smart Time Math:** Automatically calculates sequential start times (e.g., Task 1 at 08:00, Task 2 at 13:00) so your logs never overlap.
*   **Secure:** Connects locally to the Tempo and Jira APIs. Your tokens stay on your machine.

---

## 🛠️ Installation

### 1. Prerequisites
*   [Python 3.10+](https://www.python.org/)
*   [uv](https://docs.astral.sh/uv/) (**Highly Recommended** for installation and running the MCP server) or standard `pip`
*   [OpenCode](https://opencode.ai/)

### 2. Clone the Repository
```bash
git clone https://github.com/yourusername/tempo-timesheet-agent.git
cd tempo-timesheet-agent
```

### 3. Run the Setup Wizard
We have included a zero-dependency setup script that will securely prompt for your API tokens, automatically fetch your hidden Atlassian `accountId`, and generate your `.env` file.

**Using uv (Recommended):**
```bash
uv run setup.py
```

**Using standard Python:**
```bash
python setup.py
```

#### What Tokens Do I Need?
You will need **two different tokens** because Jira and Tempo are separate systems:

1.  **Tempo API Token:** (Used to log your hours)
    *   Open Jira and go to **Apps** -> **Tempo** -> **Settings** (gear icon) -> **API Integration**.
    *   Click **New Token**, set expiration, and copy the token.
    *   *(Direct link: `https://YOUR_DOMAIN.atlassian.net/plugins/servlet/ac/io.tempo.jira/tempo-app#!/configuration/api-integration`)*
2.  **Jira API Token:** (Used to read your tickets and project data)
    *   Go to your Atlassian Security settings: [id.atlassian.com/manage-profile/security/api-tokens](https://id.atlassian.com/manage-profile/security/api-tokens).
    *   Click **Create API token** and copy it.
3.  **Jira Domain:** Your company's Jira URL (e.g., `company.atlassian.net`).
4.  **Jira Email:** The exact email address you use to log into Jira.

### 4. Configure OpenCode
At the end of the `setup.py` script, it will print a JSON block. You need to copy and paste it into your OpenCode configuration file inside the `"mcp"` section.

**Where is my OpenCode config?**
*   **Windows:** `%USERPROFILE%\.config\opencode\opencode.json` (or `opencode.jsonc`)
*   **macOS / Linux:** `~/.config/opencode/opencode.json` (or `opencode.jsonc`)
*   **Project-Specific:** You can also put it in `.opencode/opencode.json` inside your current project.

*(Note: The generated JSON defaults to using `uv` to run the server. If you prefer standard Python, change `["uv", "run", ...]` to `["python", ...]` in the JSON block).*

Finally, install the global skills so OpenCode knows how to run the workflows.

**Unix (macOS / Linux):**
```bash
mkdir -p ~/.config/opencode/skills/daily-timesheet
cp skills/daily-timesheet/SKILL.md ~/.config/opencode/skills/daily-timesheet/SKILL.md

mkdir -p ~/.config/opencode/skills/catch-up-timesheet
cp skills/catch-up-timesheet/SKILL.md ~/.config/opencode/skills/catch-up-timesheet/SKILL.md
```

**Windows (PowerShell):**
```powershell
New-Item -ItemType Directory -Force -Path "$env:USERPROFILE\.config\opencode\skills\daily-timesheet"
Copy-Item -Path "skills\daily-timesheet\SKILL.md" -Destination "$env:USERPROFILE\.config\opencode\skills\daily-timesheet\SKILL.md"

New-Item -ItemType Directory -Force -Path "$env:USERPROFILE\.config\opencode\skills\catch-up-timesheet"
Copy-Item -Path "skills\catch-up-timesheet\SKILL.md" -Destination "$env:USERPROFILE\.config\opencode\skills\catch-up-timesheet\SKILL.md"
```

Restart OpenCode to apply the changes!

---

## 💡 How to Use It

Go to **any** project directory on your computer, open OpenCode, and type:

> **"Log my time"**

1. The agent will read your `git` activity for the day.
2. It will ask you for the Jira Ticket Key (e.g., `SCHE-1`) and the hours spent.
3. It will draft a professional timesheet entry and ask for your approval.
4. Once approved, it syncs the hours directly to Tempo!

### Manual Timesheet Entry
If you prefer, you can manually create a `timesheet.md` file in any directory using the template provided in `timesheet.template.md`, fill it out, and just tell OpenCode: *"Sync my timesheet"*.

## 📄 License
MIT License. See `LICENSE` for more information.