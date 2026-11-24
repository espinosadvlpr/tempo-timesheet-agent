# Tempo-Timesheet-Agent

An automated, AI-driven time-tracking workflow for software engineers using the **Jira Tempo app**.

This project provides a universal **MCP Server** (Model Context Protocol) and a set of **Agent Skills** to completely automate logging your daily work directly to Jira Tempo. Instead of clicking through menus and guessing how many hours you spent, you just tell your AI agent: *"Log my time"*. 

Currently supported AI Agents:
- **OpenCode**
- **Claude Desktop / Claude CLI**
- **Antigravity**
- **Pi**

## 🚀 Features

*   **Interactive Setup TUI:** `uv run setup.py` opens a terminal UI with arrow-key menus, agent checkboxes, masked token prompts and spinners, and falls back to plain prompts when it is unavailable.
*   **Global Pi Setup:** The setup wizard registers this checkout's Tempo extension and skills in user-level Pi settings, making them available across repositories without a global MCP server configuration.
*   **Proactive Discovery:** Automatically scans your local `git log` and `git status` to find what you worked on.
*   **GitHub Activity:** Reads the PRs you opened, the reviews you submitted (including approvals) and your PR comments through the GitHub CLI, so review work gets logged too.
*   **Intelligent Drafting:** Translates your quick notes (in any language) into professional, highly technical English descriptions.
*   **Smart Time Math:** Automatically calculates sequential start times (e.g., Task 1 at 08:00, Task 2 at 13:00) so your logs never overlap.
*   **Secure:** Connects locally to the Tempo and Jira APIs. Your tokens stay on your machine.

---

## 🛠️ Installation

### 1. Prerequisites
*   [Python 3.13+](https://www.python.org/)
*   [uv](https://docs.astral.sh/uv/) (**Highly Recommended** for execution) or standard `pip`
*   **For the GitHub activity tool only** (`get_github_activity`; everything else works without it), one of:
    *   [GitHub CLI (`gh`)](https://cli.github.com/), installed and authenticated with `gh auth login`. It reads the account that is active in `gh` (check with `gh auth status`; with several accounts, use `gh auth switch`).
    *   A `GITHUB_TOKEN` in `mcp-server/.env`, so `gh` is not needed (see [GitHub activity backend](#github-activity-backend)).

### 2. Clone the Repository
```bash
git clone https://github.com/yourusername/tempo-timesheet-agent.git
cd tempo-timesheet-agent
```

### 3. Run the Setup Wizard
The interactive setup wizard asks for your Tempo and Jira credentials, plus an optional `GITHUB_TOKEN` (press Enter to skip and use the `gh` CLI), and saves them only in `mcp-server/.env`.

```bash
uv run setup.py
```

#### Interactive TUI
Running the wizard with `uv` gives you a terminal UI built on [questionary](https://github.com/tmbo/questionary) and [rich](https://github.com/Textualize/rich):

*   Arrow-key menus for the main menu.
*   A checkbox list (space to toggle, enter to confirm) to choose which agents to configure.
*   Masked prompts for your Tempo and Jira tokens, so they are never echoed.
*   A spinner while dependencies install, and colored `[OK]`, `[WARN]` and `[ERROR]` messages.

The two libraries are declared inside `setup.py` as [inline script metadata (PEP 723)](https://peps.python.org/pep-0723/), so `uv run setup.py` installs them into a cached, isolated environment. Nothing is added to your system Python.

#### Plain mode
`python setup.py` still works without `uv`. When `questionary` or `rich` is missing, or the terminal is not interactive (for example, piped input or CI), the wizard falls back to plain numbered prompts and prints a one-line hint. Both modes write exactly the same configuration.

For supported MCP clients other than Pi, the wizard also:
1. Fetches your Atlassian Account ID.
2. Injects MCP JSON configuration into the client (for example, `claude_desktop_config.json` or `opencode.json`).
3. Generates WSL proxy `.bat` files when Claude Desktop runs on Windows and the repository is in Linux/WSL.
4. Symlinks the skills so repository changes are available to those clients.

### 4. Install Pi Resources Globally
Select Pi in the setup wizard to install the extension's locked dependencies with `npm ci` and register the extension and skills in the user-level Pi `settings.json`. The extension source remains in this checkout so it can resolve the MCP server and credentials relative to the repository. The wizard preserves existing settings and adds only the absolute extension path and skills directory path; it does not add an `mcpServers` entry. It requires `uv`, used by the extension at runtime.

Pi's default agent directory is `~/.pi/agent`. To use another directory, set `PI_CODING_AGENT_DIR` before running the wizard; the settings file is `<agent-dir>/settings.json`. If Node.js/npm is unavailable or dependency installation fails, retry manually from the repository root:

```bash
cd .pi/extensions/tempo-mcp && npm ci
```

The registered resources are global to your Pi agent directory and are available regardless of the repository you open. Restart existing Pi sessions (or start a new session) in another repository after installation so they discover the extension and skills. Do not add an `mcpServers` configuration for Pi. Credentials remain only in `mcp-server/.env`, not in Pi settings or extension configuration.

### GitHub activity backend
`get_github_activity` picks its data source from `mcp-server/.env`:

| `GITHUB_ACTIVITY_BACKEND` | Behavior |
|---------------------------|----------|
| `auto` (default) | Uses `GITHUB_TOKEN` if it is set, otherwise the `gh` CLI. |
| `gh` | Always uses the `gh` CLI, even if a token is set. |
| `token` | Always uses `GITHUB_TOKEN`; errors if it is missing. |
| `off` | Disables the tool: it returns a "disabled" message and never calls GitHub. |

Create the token at [github.com/settings/tokens](https://github.com/settings/tokens) with read access to the repositories you review (classic token: `repo` scope; fine-grained: Pull requests and Contents read-only, plus the organization's approval if required). The token only needs to read; the tool never writes to GitHub.

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
Open any repository in Pi after installing the global resources, then ask:

> **"Log my time"**

Pi discovers the registered skills and extension across repositories. The extension provides the native tools `tempo_log_work`, `tempo_search_jira_issues` (optional `assignee`, e.g. `me`), `tempo_get_jira_issue` (description and comments), `tempo_search_jira_projects`, `tempo_get_historical_git_activity`, and `tempo_get_github_activity` (PRs opened, reviews with their state, and PR comments; requires `gh`); no `mcpServers` configuration is required.

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
*   **Architecture:** The core MCP logic lives in `mcp-server/`. The agent instructions live in `skills/`. The installation logic lives in `installer.py` and `setup.py`, and all wizard prompts and messages go through the UI layer in `wizard_ui.py` (questionary/rich with a plain-prompt fallback). Keep new wizard output behind that layer so both modes stay in sync.
*   **Tests:** The installation architecture is fully tested. To run tests, execute `uv run --directory mcp-server pytest ../test_installer.py`.

Please open an issue to discuss major architectural changes before submitting a PR.

## 📄 License
MIT License. See `LICENSE` for more information.