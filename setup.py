import os
import json
import urllib.request
import urllib.error
import base64
from pathlib import Path

def main():
    print("========================================")
    print("  Tempo-Timesheet-Agent Setup Wizard")
    print("========================================\n")
    print("This script will help you configure your Jira/Tempo credentials.")
    print("You can generate an Atlassian API Token here:")
    print("👉 https://id.atlassian.com/manage-profile/security/api-tokens\n")

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
                print(f"✅ Successfully found Account ID: {account_id}")
            else:
                print(f"❌ Failed to fetch Account ID. Status Code: {response.status}")
                return
    except urllib.error.URLError as e:
        print(f"❌ Error connecting to Jira: {e}")
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
        
    print(f"\n✅ Created {env_path.resolve()} successfully!\n")
    
    # Generate the OpenCode JSON snippet
    mcp_absolute_path = str(mcp_dir.resolve()).replace('\\', '/')
    
    json_snippet = f"""========================================
🎉 ALL SET! Next Steps:

1. Copy the JSON block below.
2. Paste it into your OpenCode configuration file inside the `"mcp": {{}}` block:
   (Windows: `%USERPROFILE%\\.config\\opencode\\opencode.json`)
   (Unix: `~/.config/opencode/opencode.json`)

"tempo-mcp": {{
  "type": "local",
  "command": [
    "uv",
    "run",
    "--directory",
    "{mcp_absolute_path}",
    "server.py"
  ],
  "enabled": true,
  "env": {{}}
}}

(Note: If you are NOT using `uv`, change the command array above to `["python", "-m", "server"]` and ensure your virtual environment is activated, or provide the absolute path to your python executable.)

3. Copy the OpenCode skills to your global config (see README.md for commands).

4. Restart OpenCode and say "Log my time"!
========================================"""
    
    print(json_snippet)

if __name__ == "__main__":
    main()