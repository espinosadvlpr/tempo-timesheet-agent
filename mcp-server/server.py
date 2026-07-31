import os
import requests
from requests.auth import HTTPBasicAuth
from mcp.server.fastmcp import FastMCP
from dotenv import load_dotenv

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

if __name__ == "__main__":
    mcp.run()
