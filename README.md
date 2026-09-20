# Tempo-Timesheet-Agent

An automated, AI-driven time-tracking workflow for software engineers using the **Jira Tempo app**.

This project provides a universal **MCP Server** (Model Context Protocol) and a set of **Agent Skills** to completely automate logging your daily work directly to Jira Tempo. Instead of clicking through menus and guessing how many hours you spent, you just tell your AI agent: *"Log my time"*. 

Currently supported AI Agents:
- **OpenCode**
- **Claude Desktop / Claude CLI**
- **Antigravity**
- **Pi**

## 🚀 Features

*   **Local and Secure Setup:** The setup wizard configures supported MCP clients, while Pi uses this repository's project-local skills and extension without a global MCP configuration.
*   **Proactive Discovery:** Automatically scans your local `git log` and `git status` to find what you worked on.
*   **Intelligent Drafting:** Translates your quick notes (in any language) into professional, highly technical English descriptions.
*   **Smart Time Math:** Automatically calculates sequential start times (e.g., Task 1 at 08:00, Task 2 at 13:00) so your logs never overlap.
*   **Secure:** Connects locally to the Tempo and Jira APIs. Your tokens stay on your machine.

---

## 🛠️ Installation

### 1. Prerequisites
*   [Python 3.13+](https://www.python.org/)
*   [uv](https://docs.astral.sh/uv/) (**Highly Recommended** for execution) or standard `pip`

### 2. Clone the Repository
```bash
git clone https://github.com/yourusername/tempo-timesheet-agent.git
cd tempo-timesheet-agent
```

### 3. Run the Setup Wizard
The interactive setup wizard asks for your Jira tokens and saves them only in `mcp-server/.env`.

```bash
python setup.py
```

For supported MCP clients other than Pi, the wizard also:
1. Fetches your Atlassian Account ID.
2. Injects MCP JSON configuration into the client (for example, `claude_desktop_config.json` or `opencode.json`).
3. Generates WSL proxy `.bat` files when Claude Desktop runs on Windows and the repository is in Linux/WSL.
4. Symlinks the skills so repository changes are available to those clients.

### 4. Use Pi from This Repository
Pi is project-local: select Pi in the setup wizard to install the extension's locked local dependencies with `npm ci`, then open this cloned repository as a **trusted** project in Pi. If Node.js/npm is unavailable or installation fails, retry manually from the repository root:

```bash
cd .pi/extensions/tempo-mcp && npm ci
```

Pi automatically discovers the Tempo extension from `.pi/extensions` and the repository skills through the local Pi settings. Do not add an `mcpServers` configuration for Pi. Credentials remain only in `mcp-server/.env`, not in Pi settings or extension configuration.

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

### Pi
Open this trusted repository in Pi, then ask:

> **"Log my time"**

Pi discovers the local skills and extension automatically. The extension provides the native tools `tempo_log_work`, `tempo_search_jira_issues`, `tempo_search_jira_projects`, and `tempo_get_historical_git_activity`; no `mcpServers` configuration is required.

### Other supported clients
Open an AI client configured by the setup wizard and ask:

> **"Log my time"**

1. The agent reads your `git` activity for the day.
2. It asks for the Jira ticket key (for example, `SCHE-1`) and hours spent.
3. It drafts a professional timesheet entry and asks for approval.
4. Once approved, it syncs the hours directly to Tempo.

### Need to catch up?
Ask your configured client:

> **"Catch up my timesheet for the last 5 days"**

The agent loads the `catch-up-timesheet` skill, searches the requested workspace repositories, correlates commits, and walks you through a bulk upload.

---

## 🤝 Contributing (Open Source)
We welcome contributions! 
*   **Architecture:** The core MCP logic lives in `mcp-server/`. The agent instructions live in `skills/`. The installation logic lives in `installer.py` and `setup.py`.
*   **Tests:** The installation architecture is fully tested. To run tests, execute `uv run --directory mcp-server pytest ../test_installer.py`.

Please open an issue to discuss major architectural changes before submitting a PR.

## 📄 License
MIT License. See `LICENSE` for more information.