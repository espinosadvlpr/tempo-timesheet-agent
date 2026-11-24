# /// script
# requires-python = ">=3.13"
# dependencies = [
#     "questionary>=2.0.1",
#     "rich>=13.7.0",
# ]
# ///
import os
import json
import urllib.request
import urllib.error
import base64
import platform
import subprocess
import shutil
import tempfile
from pathlib import Path
import installer
import wizard_ui as ui

def print_header(title):
    ui.header(title)

def configure_project():
    print_header("Configure Project (Tokens & .env)")
    print("To automate your timesheet, we need two DIFFERENT tokens:")
    print("\n[Token 1] Jira API Token (For reading your tickets)")
    print("   > Generate here: https://id.atlassian.com/manage-profile/security/api-tokens")
    print("\n[Token 2] Tempo API Token (For logging your time)")
    print("   > Go to Jira -> Apps -> Tempo -> Settings -> API Integration")
    print("   > Or visit: https://YOUR_DOMAIN.atlassian.net/plugins/servlet/ac/io.tempo.jira/tempo-app#!/configuration/api-integration\n")

    tempo_token = ui.secret("1. Enter your Tempo API Token")
    jira_domain = ui.text("2. Enter your Jira Domain (e.g. company.atlassian.net)")
    
    # Clean up domain if user pasted a full URL
    if jira_domain.startswith("https://"):
        jira_domain = jira_domain.replace("https://", "")
    if jira_domain.endswith("/"):
        jira_domain = jira_domain[:-1]

    jira_email = ui.text("3. Enter your Jira Email")
    jira_token = ui.secret("4. Enter your Jira API Token")

    print("\nFetching your Atlassian Account ID from Jira...")

    # Fetch Account ID using built-in urllib (no external dependencies required)
    url = f"https://{jira_domain}/rest/api/3/myself"
    auth_string = f"{jira_email}:{jira_token}"
    base64_auth = base64.b64encode(auth_string.encode('utf-8')).decode('utf-8')
    
    req = urllib.request.Request(
        url, 
        headers={
            "Authorization": f"Basic {base64_auth}", 
            "Accept": "application/json"
        }
    )

    try:
        with urllib.request.urlopen(req) as response:
            if response.status == 200:
                data = json.loads(response.read().decode('utf-8'))
                account_id = data.get("accountId")
                ui.success(f"Successfully found Account ID: {account_id}")
            else:
                ui.error(f"Failed to fetch Account ID. Status Code: {response.status}")
                return
    except urllib.error.URLError as e:
        ui.error(f"Error connecting to Jira: {e}")
        print("Please check your Domain, Email, and API Token.")
        return

    # Write the .env file in the mcp-server directory
    env_content = f"""TEMPO_TOKEN="{tempo_token}"
JIRA_DOMAIN="{jira_domain}"
JIRA_EMAIL="{jira_email}"
JIRA_API_TOKEN="{jira_token}"
AUTHOR_ACCOUNT_ID="{account_id}"
"""
    
    mcp_dir = Path(__file__).parent / "mcp-server"
    mcp_dir.mkdir(exist_ok=True)
    env_path = mcp_dir / ".env"
    
    with open(env_path, "w", encoding="utf-8") as f:
        f.write(env_content)
        
    ui.success(f"Created {env_path.resolve()} successfully!")

def install_pi_resources(repo_root):
    """Install this checkout's Tempo extension and skills in the user-level Pi settings."""
    repo_root = Path(repo_root).resolve()
    extension_dir = repo_root / ".pi" / "extensions" / "tempo-mcp"
    extension_path = extension_dir / "index.ts"
    skills_path = repo_root / "skills"
    manual_command = "cd .pi/extensions/tempo-mcp && npm ci"

    if not extension_path.is_file() or not skills_path.is_dir():
        ui.error("Pi extension or skills source path is missing; settings were not changed.")
        return False
    if not shutil.which("uv"):
        ui.error("uv was not found; the Tempo Pi extension requires uv. Settings were not changed.")
        return False
    if not shutil.which("npm"):
        ui.warn("npm was not found; Pi extension dependencies were not installed.")
        print(f"Install Node.js/npm, then run: {manual_command}")
        return False

    agent_dir_value = os.environ.get("PI_CODING_AGENT_DIR") or "~/.pi/agent"
    agent_dir = Path(agent_dir_value).expanduser()
    settings_path = agent_dir / "settings.json"

    with ui.status("Installing Tempo Pi extension dependencies with npm ci..."):
        result = subprocess.run(["npm", "ci"], cwd=extension_dir, check=False)
    if result.returncode != 0:
        ui.error(f"Pi extension dependency installation failed (npm ci exited {result.returncode}).")
        print(f"Retry manually from the repository root: {manual_command}")
        return False

    try:
        original_settings = settings_path.read_bytes() if settings_path.exists() else None
        settings = json.loads(original_settings) if original_settings is not None else {}
        if not isinstance(settings, dict):
            raise ValueError("settings.json must contain a JSON object")
        for key in ("extensions", "skills"):
            if key in settings and not isinstance(settings[key], list):
                raise ValueError(f"settings.json '{key}' must be a list")
    except (OSError, UnicodeError, json.JSONDecodeError, ValueError) as error:
        ui.error(f"Cannot safely read Pi settings at {settings_path}: {error}")
        return False

    resources = {
        "extensions": str(extension_path.resolve()),
        "skills": str(skills_path.resolve()),
    }
    changed = False
    for key, resource_path in resources.items():
        entries = settings.setdefault(key, [])
        if resource_path not in entries:
            entries.append(resource_path)
            changed = True

    if changed:
        temporary_path = None
        try:
            agent_dir.mkdir(parents=True, exist_ok=True)
            with tempfile.NamedTemporaryFile(
                mode="w", encoding="utf-8", dir=agent_dir,
                prefix=".settings.", suffix=".tmp", delete=False,
            ) as settings_file:
                json.dump(settings, settings_file, indent=2)
                settings_file.write("\n")
                temporary_path = Path(settings_file.name)
            current_settings = settings_path.read_bytes() if settings_path.exists() else None
            if current_settings != original_settings:
                ui.error(f"Pi settings changed during installation; refusing to overwrite {settings_path}.")
                return False
            os.replace(temporary_path, settings_path)
            temporary_path = None
        except OSError as error:
            ui.error(f"Failed to atomically update Pi settings at {settings_path}: {error}")
            return False
        finally:
            if temporary_path is not None:
                try:
                    temporary_path.unlink(missing_ok=True)
                except OSError as error:
                    ui.error(f"Failed to remove temporary Pi settings file {temporary_path}: {error}")

    ui.success(f"Tempo Pi extension and skills are registered globally in {settings_path}.")
    print("Restart Pi sessions in other repositories to discover the resources.")
    return True


def configure_agents():
    print_header("Configure Agents")

    mcp_dir = Path(__file__).parent / "mcp-server"

    # Detect the real environment and installed Claude product(s) up front, so
    # the menu reflects what's actually on disk and the install path is
    # already resolved by the time the user picks an entry.
    os_env = installer.get_os_env()
    binary = installer.get_available_binary()
    claude_installs = installer.detect_claude_installations(os_env)

    menu_entries = [("OpenCode", "opencode")]

    if claude_installs["cli"]:
        menu_entries.append((f"Claude Code (CLI) - detected: {claude_installs['cli']}", "claude-cli"))
    if claude_installs["desktop"]:
        menu_entries.append((f"Claude Desktop - detected: {claude_installs['desktop']}", "claude-desktop"))
    if not claude_installs["cli"] and not claude_installs["desktop"]:
        menu_entries.append(("Claude (not detected - will use default path)", "claude"))

    menu_entries.append(("Antigravity", "antigravity"))
    menu_entries.append(("Pi", "pi"))

    agent_labels = {
        "opencode": "OpenCode",
        "claude-cli": "Claude Code (CLI)",
        "claude-desktop": "Claude Desktop",
        "claude": "Claude",
        "antigravity": "Antigravity",
        "pi": "Pi",
    }

    agents_to_install = ui.select_many(
        "Which agents do you want to configure?",
        [(label, key) for label, key in menu_entries],
    )
    if not agents_to_install:
        return

    agents_to_install = list(set(agents_to_install))

    repo_root = Path(__file__).parent.resolve()
    mcp_dir_str = str(mcp_dir.resolve()).replace('\\', '/')

    summary_configs = []
    summary_skills = []
    summary_pi = []

    for agent in agents_to_install:
        if agent == "pi":
            installed = install_pi_resources(repo_root)
            if installed:
                summary_pi.append(
                    "Pi: Tempo extension and skills are registered globally; restart Pi sessions."
                )
            else:
                summary_pi.append(
                    "Pi: global resource installation failed; see the message above and retry."
                )
            continue

        # Resolve the config path. claude-cli/claude-desktop are already
        # resolved by detection; everything else (including the undetected
        # "claude" fallback) still goes through get_config_path as before.
        use_wsl_bat_proxy = False
        if agent == "claude-cli":
            config_path = Path(claude_installs["cli"])
        elif agent == "claude-desktop":
            config_path = Path(claude_installs["desktop"])
            use_wsl_bat_proxy = (os_env == "wsl")
        else:
            config_path_str = installer.get_config_path(
                "claude" if agent == "claude" else agent, os_env
            )
            config_path = Path(os.path.expandvars(config_path_str)).expanduser()
            use_wsl_bat_proxy = (agent == "claude" and os_env == "wsl")

        # Determine command
        if use_wsl_bat_proxy:
            bat_path = repo_root / "tempo-mcp-proxy.bat"

            if binary == "uv":
                script_args = "run server.py"
            else:
                script_args = "server.py"

            bat_content = installer.generate_wsl_proxy_bat(
                linux_dir=mcp_dir_str,
                binary=binary,
                script=script_args
            )
            with open(bat_path, "w") as f:
                f.write(bat_content)

            try:
                bat_win_path = subprocess.check_output(['wslpath', '-w', str(bat_path)]).decode('utf-8').strip()
            except Exception as e:
                ui.error(f"Failed to resolve Windows path for bat file: {e}")
                bat_win_path = str(bat_path)

            command = [bat_win_path]
        else:
            if binary == "uv":
                command = ["uv", "run", "--directory", mcp_dir_str, "server.py"]
            else:
                command = ["python", str(mcp_dir / "server.py")]

        # Read JSON
        config_data = {}
        if config_path.exists():
            try:
                with open(config_path, "r", encoding="utf-8") as f:
                    config_data = json.load(f)
            except json.JSONDecodeError:
                ui.warn(f"Could not parse {config_path}. Starting fresh.")

        # Inject -- schema is keyed by product family, "claude" covers both
        # claude-cli and claude-desktop
        schema_agent = "claude" if agent in ("claude-cli", "claude-desktop", "claude") else agent
        config_data = installer.inject_mcp_config(config_data, schema_agent, "tempo-mcp", command)

        # Write JSON
        config_path.parent.mkdir(parents=True, exist_ok=True)
        try:
            with open(config_path, "w", encoding="utf-8") as f:
                json.dump(config_data, f, indent=2)
            summary_configs.append(f"{agent_labels.get(agent, agent.title())}: {config_path}")
        except Exception as e:
            ui.error(f"Failed to write config for {agent}: {e}")

        # Symlink Skills -- Claude Desktop has no filesystem skills mechanism
        if agent == "claude-desktop":
            continue

        skills_src_dir = repo_root / "skills"
        if skills_src_dir.exists():
            if agent == "opencode":
                dest_dir = Path("~/.config/opencode/skills").expanduser()
            elif agent in ("claude-cli", "claude"):
                dest_dir = Path("~/.claude/skills").expanduser()
            elif agent == "antigravity":
                dest_dir = Path("~/.config/antigravity/skills").expanduser()
            elif agent == "pi":
                dest_dir = Path("~/.pi/skills").expanduser()

            dest_dir.mkdir(parents=True, exist_ok=True)

            linked_any = False
            for skill_dir in skills_src_dir.iterdir():
                if skill_dir.is_dir() and (skill_dir / "SKILL.md").exists():
                    dest_link = dest_dir / skill_dir.name
                    if dest_link.exists() or dest_link.is_symlink():
                        try:
                            dest_link.unlink()
                        except Exception:
                            shutil.rmtree(dest_link, ignore_errors=True)
                    try:
                        os.symlink(skill_dir, dest_link)
                        linked_any = True
                    except Exception as e:
                        ui.error(f"Failed to symlink {skill_dir.name} for {agent}: {e}")

            if linked_any:
                summary_skills.append(f"{agent_labels.get(agent, agent.title())}: {dest_dir}")

    ui.header("INSTALLATION COMPLETE! Summary:")
    ui.info("\n[Configs Updated]")
    for c in summary_configs:
        ui.info(f"  > {c}")
    ui.info("\n[Skills Linked]")
    if summary_skills:
        for s in summary_skills:
            ui.info(f"  > {s}")
    else:
        ui.info("  > None")
    if summary_pi:
        ui.info("\n[Pi Local Resources]")
        for resource in summary_pi:
            ui.info(f"  > {resource}")
    ui.info("\nRestart your agents and say 'Log my time'!\n")

def main_menu():
    ui.notify_fallback()
    while True:
        print_header("Tempo-Timesheet-Agent Setup Wizard")
        choice = ui.select(
            "Please choose an option:",
            [
                ("Configure Project (Tokens & .env)", "project"),
                ("Configure Agents (MCP & Skills)", "agents"),
            ],
            cancel_label="Exit",
        )

        if choice == "project":
            configure_project()
        elif choice == "agents":
            configure_agents()
        else:
            ui.info("\nExiting. Goodbye!\n")
            break

if __name__ == "__main__":
    try:
        main_menu()
    except KeyboardInterrupt:
        print("\nCancelled. Goodbye!")
