import os
import json
import urllib.request
import urllib.error
import base64
import platform
import subprocess
import shutil
from pathlib import Path
import installer

def print_header(title):
    print("\n========================================")
    print(f"  {title}")
    print("========================================")

def configure_project():
    print_header("Configure Project (Tokens & .env)")
    print("To automate your timesheet, we need two DIFFERENT tokens:")
    print("\n[Token 1] Jira API Token (For reading your tickets)")
    print("   > Generate here: https://id.atlassian.com/manage-profile/security/api-tokens")
    print("\n[Token 2] Tempo API Token (For logging your time)")
    print("   > Go to Jira -> Apps -> Tempo -> Settings -> API Integration")
    print("   > Or visit: https://YOUR_DOMAIN.atlassian.net/plugins/servlet/ac/io.tempo.jira/tempo-app#!/configuration/api-integration\n")

    tempo_token = input("1. Enter your Tempo API Token: ").strip()
    jira_domain = input("2. Enter your Jira Domain (e.g. company.atlassian.net): ").strip()
    
    # Clean up domain if user pasted a full URL
    if jira_domain.startswith("https://"):
        jira_domain = jira_domain.replace("https://", "")
    if jira_domain.endswith("/"):
        jira_domain = jira_domain[:-1]

    jira_email = input("3. Enter your Jira Email: ").strip()
    jira_token = input("4. Enter your Jira API Token: ").strip()

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
                print(f"[OK] Successfully found Account ID: {account_id}")
            else:
                print(f"[ERROR] Failed to fetch Account ID. Status Code: {response.status}")
                return
    except urllib.error.URLError as e:
        print(f"[ERROR] Error connecting to Jira: {e}")
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
        
    print(f"\n[OK] Created {env_path.resolve()} successfully!\n")

def configure_agents():
    print_header("Configure Agents")
    
    mcp_dir = Path(__file__).parent / "mcp-server"
    
    while True:
        print("Which agents do you want to configure? (Comma-separated, e.g., 1,2 or 5)")
        print("[1] OpenCode")
        print("[2] Claude")
        print("[3] Antigravity")
        print("[4] Pi")
        print("[5] All")
        print("[0] Cancel")
        
        choice = input("\nEnter your choice: ").strip()
        
        if choice == "0":
            return
            
        choices = [c.strip() for c in choice.split(",") if c.strip()]
        
        agents_to_install = []
        if "5" in choices or "All".lower() in choices or "all".lower() in choices:
            agents_to_install = ["opencode", "claude", "antigravity", "pi"]
            break
        
        mapping = {"1": "opencode", "2": "claude", "3": "antigravity", "4": "pi"}
        for c in choices:
            if c in mapping:
                agents_to_install.append(mapping[c])
        
        if agents_to_install:
            break
        print("[WARN] Invalid choice, please try again.\n")
        
    agents_to_install = list(set(agents_to_install))

    os_env = installer.get_os_env()
    binary = installer.get_available_binary()
    repo_root = Path(__file__).parent.resolve()
    mcp_dir_str = str(mcp_dir.resolve()).replace('\\', '/')
    
    summary_configs = []
    summary_skills = []
    
    for agent in agents_to_install:
        config_path_str = installer.get_config_path(agent, os_env)
        
        # Determine command
        if agent == "claude" and os_env == "wsl":
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
                print(f"[ERROR] Failed to resolve Windows path for bat file: {e}")
                bat_win_path = str(bat_path)
                
            command = [bat_win_path]
        else:
            if binary == "uv":
                command = ["uv", "run", "--directory", mcp_dir_str, "server.py"]
            else:
                command = ["python", str(mcp_dir / "server.py")]

        # Read JSON
        config_path = Path(os.path.expandvars(config_path_str)).expanduser()
        config_data = {}
        if config_path.exists():
            try:
                with open(config_path, "r", encoding="utf-8") as f:
                    config_data = json.load(f)
            except json.JSONDecodeError:
                print(f"[WARN] Could not parse {config_path}. Starting fresh.")
        
        # Inject
        config_data = installer.inject_mcp_config(config_data, agent, "tempo-mcp", command)
        
        # Write JSON
        config_path.parent.mkdir(parents=True, exist_ok=True)
        try:
            with open(config_path, "w", encoding="utf-8") as f:
                json.dump(config_data, f, indent=2)
            summary_configs.append(f"{agent.title()}: {config_path}")
        except Exception as e:
            print(f"[ERROR] Failed to write config for {agent}: {e}")

        # Symlink Skills
        skills_src_dir = repo_root / "skills"
        if skills_src_dir.exists():
            if agent == "opencode":
                dest_dir = Path("~/.config/opencode/skills").expanduser()
            elif agent == "claude":
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
                        print(f"[ERROR] Failed to symlink {skill_dir.name} for {agent}: {e}")
            
            if linked_any:
                summary_skills.append(f"{agent.title()}: {dest_dir}")

    print("\n========================================")
    print("  INSTALLATION COMPLETE! Summary:")
    print("========================================")
    print("\n[Configs Updated]")
    for c in summary_configs:
        print(f"  > {c}")
    print("\n[Skills Linked]")
    if summary_skills:
        for s in summary_skills:
            print(f"  > {s}")
    else:
        print("  > None")
    print("\nRestart your agents and say 'Log my time'!")
    print("========================================\n")

def main_menu():
    while True:
        print_header("Tempo-Timesheet-Agent Setup Wizard")
        print("Please choose an option:")
        print("[1] Configure Project (Tokens & .env)")
        print("[2] Configure Agents (MCP & Skills)")
        print("[0] Exit")
        
        choice = input("\nEnter your choice: ").strip()
        
        if choice == "1":
            configure_project()
        elif choice == "2":
            configure_agents()
        elif choice == "0":
            print("\nExiting. Goodbye!\n")
            break
        else:
            print("\n[WARN] Invalid choice, please try again.")

if __name__ == "__main__":
    main_menu()
