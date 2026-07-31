import os
import requests
import subprocess
from pathlib import Path
from requests.auth import HTTPBasicAuth
from mcp.server.fastmcp import FastMCP
from dotenv import load_dotenv, set_key

load_dotenv()

# Initialize the FastMCP server
mcp = FastMCP("Tempo MCP Server")

def get_jira_issue_id(issue_key: str) -> int:
    """Fetches the internal Jira Issue ID for a given Issue Key (e.g., SCHE-1)."""
    jira_domain = os.getenv("JIRA_DOMAIN")
    jira_email = os.getenv("JIRA_EMAIL")
    jira_token = os.getenv("JIRA_API_TOKEN")

    if not all([jira_domain, jira_email, jira_token]):
        raise ValueError("Missing Jira configuration in environment variables.")

    url = f"https://{jira_domain}/rest/api/3/issue/{issue_key}"
    
    response = requests.get(
        url,
        auth=HTTPBasicAuth(jira_email, jira_token),
        headers={"Accept": "application/json"},
        timeout=10
    )

    if response.status_code == 200:
        data = response.json()
        return int(data["id"])
    else:
        raise Exception(f"Failed to fetch Jira issue {issue_key}: {response.status_code} - {response.text}")

@mcp.tool()
def log_tempo_work(issue_key: str, time_spent_hours: float, date: str, description_en: str, start_time: str = "08:00:00") -> str:
    """
    Logs work time to Tempo using the Jira Issue Key.
    
    Args:
        issue_key: The Jira Issue Key (e.g., 'SCHE-1').
        time_spent_hours: Time spent in hours (e.g., 2.5).
        date: The date of the worklog in YYYY-MM-DD format (e.g., '2026-06-19').
        description_en: A professional technical description of the work done, translated to English.
        start_time: The start time of the task in HH:MM:SS format (defaults to 08:00:00).
    """
    tempo_token = os.getenv("TEMPO_TOKEN")
    author_id = os.getenv("AUTHOR_ACCOUNT_ID")
    
    if not tempo_token or not author_id:
        return "Error: Missing TEMPO_TOKEN or AUTHOR_ACCOUNT_ID in environment variables."
        
    try:
        # Step 1: Resolve Issue Key to Issue ID
        issue_id = get_jira_issue_id(issue_key)
        
        # Step 2: Prepare Tempo Worklog payload
        time_spent_seconds = int(time_spent_hours * 3600)
        
        payload = {
            "issueId": issue_id,
            "timeSpentSeconds": time_spent_seconds,
            "startDate": date,
            "startTime": start_time,
            "description": description_en,
            "authorAccountId": author_id
        }
        
        headers = {
            "Authorization": f"Bearer {tempo_token}",
            "Content-Type": "application/json",
        }
        
        import json
        response = requests.post(
            "https://api.tempo.io/4/worklogs",
            headers=headers,
            data=json.dumps(payload),
            timeout=10
        )
        
        if response.status_code in [200, 201]:
            return f"Successfully logged {time_spent_hours} hours to {issue_key} ({issue_id}) on {date}."
        else:
            return f"Failed to log work to Tempo: {response.status_code} - {response.text}"
            
    except Exception as e:
        return f"Error logging work: {str(e)}"

@mcp.tool()
def search_jira_issues(project_key: str, max_results: int = 10) -> str:
    """
    Searches Jira for recent active tickets in a specific project.
    Useful when the user doesn't know the exact issue key.
    
    Args:
        project_key: The Jira Project Key (e.g., 'SCHE' or 'IA').
        max_results: Maximum number of tickets to return (default 10).
    """
    jira_domain = os.getenv("JIRA_DOMAIN")
    jira_email = os.getenv("JIRA_EMAIL")
    jira_token = os.getenv("JIRA_API_TOKEN")

    if not all([jira_domain, jira_email, jira_token]):
        return "Error: Missing Jira configuration in environment variables."

    # JQL: Search for tickets in the project that are not 'Done' (or equivalent closed statuses), ordered by recently updated
    jql = f'project = "{project_key}" AND statusCategory != Done ORDER BY updated DESC'
    url = f"https://{jira_domain}/rest/api/3/search"
    
    try:
        response = requests.get(
            url,
            auth=HTTPBasicAuth(jira_email, jira_token),
            headers={"Accept": "application/json"},
            params={"jql": jql, "maxResults": max_results, "fields": "summary,assignee,status"},
            timeout=10
        )

        if response.status_code == 200:
            issues = response.json().get("issues", [])
            if not issues:
                return f"No active tickets found for project {project_key}."
            
            result = []
            for issue in issues:
                key = issue.get("key")
                fields = issue.get("fields", {})
                summary = fields.get("summary", "No summary")
                status = fields.get("status", {}).get("name", "Unknown")
                assignee_dict = fields.get("assignee")
                assignee = assignee_dict.get("displayName") if assignee_dict else "Unassigned"
                
                result.append(f"- [{key}] {summary} (Status: {status} | Assignee: {assignee})")
            
            return "\n".join(result)
        else:
            return f"Failed to search Jira: {response.status_code} - {response.text}"
    except Exception as e:
        return f"Error searching Jira: {str(e)}"

@mcp.tool()
def get_historical_git_activity(repo_paths: str, since: str, until: str = "now") -> str:
    """
    Scans specific git repositories and extracts commit history.
    
    Args:
        repo_paths: Comma-separated absolute paths to the git repositories to scan (e.g., 'D:/projects/app1, D:/projects/app2').
        since: The start date/time for the git log (e.g., '3 weeks ago', '2026-06-01').
        until: The end date/time for the git log (defaults to 'now').
    """
    if not repo_paths:
        return "Error: Please provide at least one repository path."
        
    dir_list = [Path(d.strip()) for d in repo_paths.split(",") if d.strip()]
    
    # Try to find git author email/name
    try:
        author = subprocess.check_output(["git", "config", "user.email"], text=True).strip()
    except Exception:
        return "Error: Could not determine git user.email. Make sure git is installed and configured globally."

    results = []
    
    for repo in dir_list:
        if not repo.exists() or not repo.is_dir():
            results.append(f"\nSkipped {repo} (Not a valid directory)")
            continue
            
        try:
            cmd = [
                "git", "log", "--all", f"--author={author}",
                f"--since={since}", f"--until={until}", 
                "--date=short", "--format=%ad | %h | %s"
            ]
            output = subprocess.check_output(cmd, cwd=str(repo), text=True, stderr=subprocess.DEVNULL).strip()
            if output:
                results.append(f"\nRepository: {repo.name} ({repo})\n" + output)
            else:
                results.append(f"\nRepository: {repo.name} ({repo})\n(No commits found in this date range)")
        except subprocess.CalledProcessError:
            results.append(f"\nRepository: {repo.name} ({repo})\n(Not a valid git repository or command failed)")

    if not results:
        return f"No activity found for author '{author}' between '{since}' and '{until}'."
        
    return f"Found activity for '{author}':\n" + "\n".join(results)

if __name__ == "__main__":
    mcp.run()
