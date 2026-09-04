# Tempo-Timesheet-Agent

An automated, AI-driven time-tracking workflow for software engineers using the **Jira Tempo app**.

This project provides a universal **MCP Server** (Model Context Protocol) and a set of **Agent Skills** to completely automate logging your daily work directly to Jira Tempo. Instead of clicking through menus and guessing how many hours you spent, you just tell your AI agent: *"Log my time"*. 

Currently supported AI Agents:
- **OpenCode**
- **Claude Desktop / Claude CLI**
- **Antigravity**
- **Pi**

## 🚀 Features

*   **Universal Setup Wizard:** A single TUI script automatically configures MCP servers and injects skills across all your favorite AI agents with zero manual configuration.
*   **Proactive Discovery:** Automatically scans your local `git log` and `git status` to find what you worked on.
*   **Intelligent Drafting:** Translates your quick notes (in any language) into professional, highly technical English descriptions.
*   **Smart Time Math:** Automatically calculates sequential start times (e.g., Task 1 at 08:00, Task 2 at 13:00) so your logs never overlap.
*   **Secure:** Connects locally to the Tempo and Jira APIs. Your tokens stay on your machine.

---

## 🛠️ Installation

### 1. Prerequisites
*   [Python 3.10+](https://www.python.org/)
*   [uv](https://docs.astral.sh/uv/) (**Highly Recommended** for execution) or standard `pip`

### 2. Clone the Repository
```bash
git clone https://github.com/yourusername/tempo-timesheet-agent.git
cd tempo-timesheet-agent
```

### 3. Run the Universal Installer
We have built an interactive setup wizard that handles everything. It will ask for your Jira tokens, save them locally in a `.env` file, and then automatically configure any AI agent you have installed.

```bash
python setup.py
```

**The wizard will handle:**
1. Fetching your hidden Atlassian Account ID.
2. Inyecting the MCP JSON configuration directly into your agents (e.g., `claude_desktop_config.json`, `opencode.json`).
3. Generating WSL proxy `.bat` files automatically if you run Claude Desktop on Windows but your repo is in Linux/WSL.
4. Symlinking the AI Skills to ensure changes in this repository instantly reflect across all your agents.

### What Tokens Do I Need?
You will need **two different tokens** because Jira and Tempo are separate systems:

1.  **Tempo API Token:** (Used to log your hours)
    *   Open Jira and go to **Apps** -> **Tempo** -> **Settings** (gear icon) -> **API Integration**.
    *   Click **New Token**, set expiration, and copy the token.
2.  **Jira API Token:** (Used to read your tickets and project data)
    *   Go to your Atlassian Security settings: [id.atlassian.com/manage-profile/security/api-tokens](https://id.atlassian.com/manage-profile/security/api-tokens).
    *   Click **Create API token** and copy it.

---

## 💡 How to Use It

Go to **any** project directory on your computer, open your AI Agent (Claude, OpenCode, etc.), and type:

> **"Log my time"**

1. The agent will read your `git` activity for the day.
2. It will ask you for the Jira Ticket Key (e.g., `SCHE-1`) and the hours spent.
3. It will draft a professional timesheet entry and ask for your approval.
4. Once approved, it syncs the hours directly to Tempo!

### Need to catch up?
If you forgot to log your time for the past week, just tell your agent:
> **"Catch up my timesheet for the last 5 days"**

The agent will load the `catch-up-timesheet` skill, search your global workspace repositories, correlate the git commits, and walk you through a bulk upload.

---

## 🤝 Contributing (Open Source)
We welcome contributions! 
*   **Architecture:** The core MCP logic lives in `mcp-server/`. The agent instructions live in `skills/`. The installation logic lives in `installer.py` and `setup.py`.
*   **Tests:** The installation architecture is fully tested. To run tests, execute `uv run --directory mcp-server pytest ../test_installer.py`.

Please open an issue to discuss major architectural changes before submitting a PR.

## 📄 License
MIT License. See `LICENSE` for more information.