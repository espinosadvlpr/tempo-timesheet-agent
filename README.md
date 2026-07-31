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
*   [uv](https://docs.astral.sh/uv/) (Python package manager)
*   [OpenCode](https://opencode.ai/)

### 2. Clone the Repository
```bash
git clone https://github.com/yourusername/tempo-timesheet-agent.git
cd tempo-timesheet-agent
```

### 3. Run the Setup Wizard
We have included a zero-dependency setup script that will securely prompt for your API tokens, automatically fetch your hidden Atlassian `accountId`, and generate your `.env` file.

```bash
python setup.py
```

*You will need:*
1.  **Tempo API Token:** From your Tempo Apps settings.
2.  **Jira Domain:** e.g., `yourcompany.atlassian.net`
3.  **Jira Email:** The email you log in with.
4.  **Jira API Token:** Generate one at [id.atlassian.com/manage-profile/security/api-tokens](https://id.atlassian.com/manage-profile/security/api-tokens).

### 4. Configure OpenCode
At the end of the `setup.py` script, it will print a JSON block. Copy and paste it into your `opencode.jsonc` (or `~/.config/opencode/opencode.json`) inside the `"mcp"` section.

Finally, install the global skill so OpenCode knows how to run the workflow:
```bash
mkdir -p ~/.config/opencode/skills/daily-timesheet
cp skills/daily-timesheet/SKILL.md ~/.config/opencode/skills/daily-timesheet/SKILL.md
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