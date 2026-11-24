import json
import os
import re
import requests
import subprocess
from datetime import datetime, timedelta, timezone
from pathlib import Path
from requests.auth import HTTPBasicAuth
from mcp.server.fastmcp import FastMCP
from dotenv import load_dotenv, set_key

SERVER_DIR = Path(__file__).resolve().parent


def load_server_environment() -> None:
    load_dotenv(dotenv_path=SERVER_DIR / ".env")


load_server_environment()

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

def adf_to_text(node) -> str:
    """Flattens an Atlassian Document Format (ADF) node into plain text."""
    if not node:
        return ""
    if isinstance(node, list):
        return "\n".join(part for part in (adf_to_text(child) for child in node) if part)

    node_type = node.get("type")
    if node_type == "text":
        return node.get("text", "")
    if node_type == "hardBreak":
        return "\n"
    if node_type == "mention":
        return node.get("attrs", {}).get("text", "@user")
    if node_type == "inlineCard":
        return node.get("attrs", {}).get("url", "")
    if node_type in ("media", "mediaSingle", "mediaGroup"):
        return "[attachment]" if node_type == "media" else adf_to_text(node.get("content"))

    children = node.get("content") or []
    if node_type in ("paragraph", "heading"):
        return "".join(adf_to_text(child) for child in children)
    if node_type == "listItem":
        return "- " + adf_to_text(children).replace("\n", "\n  ")
    return adf_to_text(children)


@mcp.tool()
def get_jira_issue(issue_key: str) -> str:
    """
    Reads the full detail of a Jira ticket: status, assignee, description and comments.
    Use it after search_jira_issues to understand what a ticket asks for.

    Args:
        issue_key: The Jira Issue Key (e.g., 'SCHE-1').
    """
    jira_domain = os.getenv("JIRA_DOMAIN")
    jira_email = os.getenv("JIRA_EMAIL")
    jira_token = os.getenv("JIRA_API_TOKEN")

    if not all([jira_domain, jira_email, jira_token]):
        return "Error: Missing Jira configuration in environment variables."

    url = f"https://{jira_domain}/rest/api/3/issue/{issue_key}"

    try:
        response = requests.get(
            url,
            auth=HTTPBasicAuth(jira_email, jira_token),
            headers={"Accept": "application/json"},
            params={"fields": "summary,status,assignee,description,comment"},
            timeout=10
        )

        if response.status_code != 200:
            return f"Failed to fetch Jira issue {issue_key}: {response.status_code} - {response.text}"

        data = response.json()
        fields = data.get("fields", {})
        status = (fields.get("status") or {}).get("name", "Unknown")
        assignee_dict = fields.get("assignee")
        assignee = assignee_dict.get("displayName") if assignee_dict else "Unassigned"
        description = adf_to_text(fields.get("description")) or "(No description)"

        comments = (fields.get("comment") or {}).get("comments", [])
        if comments:
            comment_lines = []
            for comment in comments:
                author = (comment.get("author") or {}).get("displayName", "Unknown")
                created = comment.get("created", "")
                comment_lines.append(f"- {author} ({created}): {adf_to_text(comment.get('body'))}")
            comments_text = "\n".join(comment_lines)
        else:
            comments_text = "(No comments)"

        return (
            f"[{data.get('key', issue_key)}] {fields.get('summary', 'No summary')}\n"
            f"Status: {status} | Assignee: {assignee}\n\n"
            f"Description:\n{description}\n\n"
            f"Comments:\n{comments_text}"
        )
    except Exception as e:
        return f"Error fetching Jira issue: {str(e)}"


@mcp.tool()
def search_jira_issues(project_key: str, max_results: int = 10, assignee: str = "") -> str:
    """
    Searches Jira for recent active tickets in a specific project.
    Useful when the user doesn't know the exact issue key.

    Args:
        project_key: The Jira Project Key (e.g., 'SCHE' or 'IA').
        max_results: Maximum number of tickets to return (default 10).
        assignee: Optional. Use 'me' for tickets assigned to the authenticated user, or a Jira accountId to filter by someone else. Empty returns all assignees.
    """
    jira_domain = os.getenv("JIRA_DOMAIN")
    jira_email = os.getenv("JIRA_EMAIL")
    jira_token = os.getenv("JIRA_API_TOKEN")

    if not all([jira_domain, jira_email, jira_token]):
        return "Error: Missing Jira configuration in environment variables."

    # JQL: Search for tickets in the project that are not 'Done' (or equivalent closed statuses), ordered by recently updated
    assignee_clause = ""
    if assignee.strip().lower() in ("me", "currentuser()"):
        assignee_clause = " AND assignee = currentUser()"
    elif assignee.strip():
        escaped = assignee.strip().replace("\\", "\\\\").replace('"', '\\"')
        assignee_clause = f' AND assignee = "{escaped}"'
    jql = f'project = "{project_key}" AND statusCategory != Done{assignee_clause} ORDER BY updated DESC'
    url = f"https://{jira_domain}/rest/api/3/search/jql"
    
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
def search_jira_projects(query: str = "", max_results: int = 10) -> str:
    """
    Searches Jira for projects by name or key.
    Useful when the user doesn't know the exact project key.
    
    Args:
        query: The search term (e.g., 'Scheduler' or 'SCHE'). If empty, returns recent projects.
        max_results: Maximum number of projects to return (default 10).
    """
    jira_domain = os.getenv("JIRA_DOMAIN")
    jira_email = os.getenv("JIRA_EMAIL")
    jira_token = os.getenv("JIRA_API_TOKEN")

    if not all([jira_domain, jira_email, jira_token]):
        return "Error: Missing Jira configuration in environment variables."

    url = f"https://{jira_domain}/rest/api/3/project/search"
    params = {"maxResults": max_results}
    if query:
        params["query"] = query
        
    try:
        response = requests.get(
            url,
            auth=HTTPBasicAuth(jira_email, jira_token),
            headers={"Accept": "application/json"},
            params=params,
            timeout=10
        )

        if response.status_code == 200:
            projects = response.json().get("values", [])
            if not projects:
                return f"No projects found matching '{query}'."
            
            result = []
            for project in projects:
                key = project.get("key")
                name = project.get("name")
                style = project.get("style", "Unknown style")
                result.append(f"- [{key}] {name} (Style: {style})")
            
            return "\n".join(result)
        else:
            return f"Failed to search Jira projects: {response.status_code} - {response.text}"
    except Exception as e:
        return f"Error searching Jira projects: {str(e)}"

@mcp.tool()
def get_historical_git_activity(repo_paths: str, since: str, until: str = "now") -> str:
    """
    Scans specific git repositories and extracts commit history.
    
    Args:
        repo_paths: Comma-separated absolute paths to the git repositories to scan (e.g., '/projects/app1, /projects/app2').
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


GH_TIMEOUT_SECONDS = 30
GH_MAX_RANGE_DAYS = 365  # GitHub's contributionsCollection only spans one year.
GH_MAX_COMMENTED_PRS = 50

GH_REVIEW_LABELS = {
    "APPROVED": "Review approved",
    "CHANGES_REQUESTED": "Review changes requested",
    "COMMENTED": "Review commented",
    "DISMISSED": "Review dismissed",
    "PENDING": "Review pending",
}

GH_CONTRIBUTIONS_QUERY = """
query($from: DateTime!, $to: DateTime!) {
  viewer {
    login
    contributionsCollection(from: $from, to: $to) {
      pullRequestContributions(first: 100) {
        nodes { occurredAt pullRequest { number title url repository { nameWithOwner } } }
      }
      pullRequestReviewContributions(first: 100) {
        nodes {
          occurredAt
          pullRequestReview { state url }
          pullRequest { number title url repository { nameWithOwner } }
        }
      }
    }
  }
}
"""


def run_gh(args: list) -> str:
    """Runs the GitHub CLI and returns stdout, raising RuntimeError with an actionable message."""
    try:
        result = subprocess.run(
            ["gh", *args], capture_output=True, text=True, timeout=GH_TIMEOUT_SECONDS
        )
    except FileNotFoundError:
        raise RuntimeError(
            "GitHub CLI (gh) is not installed. Install it from https://cli.github.com/ "
            "and run 'gh auth login'."
        )
    if result.returncode != 0:
        raise RuntimeError(f"gh {' '.join(args[:2])} failed: {result.stderr.strip()}")
    return result.stdout


def parse_time_boundary(value: str, end: bool = False) -> datetime:
    """Parses 'now', 'N days|weeks|months ago', or an ISO date/datetime into an aware UTC datetime."""
    text = value.strip()
    now = datetime.now(timezone.utc)
    if text.lower() == "now":
        return now

    relative = re.fullmatch(r"(\d+)\s+(day|week|month)s?\s+ago", text.lower())
    if relative:
        days = {"day": 1, "week": 7, "month": 30}[relative.group(2)]
        return now - timedelta(days=int(relative.group(1)) * days)

    try:
        parsed = datetime.fromisoformat(text.replace("Z", "+00:00"))
    except ValueError:
        raise ValueError(
            f"Unsupported date '{value}'. Use YYYY-MM-DD, an ISO datetime, 'now' or 'N days|weeks|months ago'."
        )
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    if end and len(text) == 10:
        parsed += timedelta(days=1)  # A bare end date includes that whole day.
    return parsed.astimezone(timezone.utc)


def parse_gh_timestamp(value: str) -> datetime:
    return datetime.fromisoformat(value.replace("Z", "+00:00")).astimezone(timezone.utc)


def collect_github_events(start: datetime, end: datetime, warnings: list) -> tuple:
    """Returns (login, events). Each event is (datetime, kind, repo, number, title, url)."""
    iso = lambda moment: moment.strftime("%Y-%m-%dT%H:%M:%SZ")
    payload = json.loads(run_gh([
        "api", "graphql",
        "-f", f"query={GH_CONTRIBUTIONS_QUERY}",
        "-f", f"from={iso(start)}",
        "-f", f"to={iso(end)}",
    ]))
    viewer = payload["data"]["viewer"]
    login = viewer["login"]
    collection = viewer["contributionsCollection"]
    events = []

    for node in collection["pullRequestContributions"]["nodes"]:
        pr = node["pullRequest"]
        events.append((
            parse_gh_timestamp(node["occurredAt"]), "PR opened",
            pr["repository"]["nameWithOwner"], pr["number"], pr["title"], pr["url"],
        ))

    for node in collection["pullRequestReviewContributions"]["nodes"]:
        pr = node["pullRequest"]
        review = node["pullRequestReview"]
        events.append((
            parse_gh_timestamp(node["occurredAt"]),
            GH_REVIEW_LABELS.get(review["state"], f"Review {review['state'].lower()}"),
            pr["repository"]["nameWithOwner"], pr["number"], pr["title"], review["url"],
        ))

    search = run_gh([
        "api", "-X", "GET", "search/issues",
        "-f", f"q=commenter:{login} type:pr updated:>={start.strftime('%Y-%m-%d')}",
        "-f", f"per_page={GH_MAX_COMMENTED_PRS}",
        "--jq", r'.items[] | {number, title, repo: (.repository_url | sub("https://api.github.com/repos/"; ""))}',
    ])
    for line in search.splitlines():
        if not line.strip():
            continue
        pr = json.loads(line)
        for endpoint in ("issues", "pulls"):
            try:
                comments = run_gh([
                    "api", "--paginate", f"repos/{pr['repo']}/{endpoint}/{pr['number']}/comments",
                    "--jq", ".[] | {login: .user.login, at: .created_at, url: .html_url}",
                ])
            except RuntimeError as error:
                warnings.append(f"Could not read comments for {pr['repo']}#{pr['number']}: {error}")
                continue
            for comment_line in comments.splitlines():
                if not comment_line.strip():
                    continue
                comment = json.loads(comment_line)
                moment = parse_gh_timestamp(comment["at"])
                if comment["login"] == login and start <= moment <= end:
                    events.append((moment, "Comment", pr["repo"], pr["number"], pr["title"], comment["url"]))

    return login, events


def format_github_events(login: str, start: datetime, end: datetime, events: list, warnings: list) -> str:
    seen = set()
    unique = []
    for event in sorted(events, key=lambda item: item[0]):
        if event[5] in seen:
            continue
        seen.add(event[5])
        unique.append(event)

    header = f"GitHub activity for '{login}' (times in UTC) from {start:%Y-%m-%d %H:%M} to {end:%Y-%m-%d %H:%M}:"
    if not unique:
        body = "\n(No PRs, reviews or comments found in this date range)"
    else:
        lines = []
        current_day = None
        for moment, kind, repo, number, title, url in unique:
            day = moment.strftime("%Y-%m-%d")
            if day != current_day:
                lines.append(f"\n{day}")
                current_day = day
            lines.append(f"  {moment:%H:%M} | {kind} | {repo}#{number} | {title} | {url}")
        body = "\n".join(lines)

    footer = "".join(f"\nWarning: {warning}" for warning in warnings)
    return header + body + footer


@mcp.tool()
def get_github_activity(since: str, until: str = "now", repos: str = "") -> str:
    """
    Reads the user's GitHub activity (PRs opened, reviews with their state such as approvals,
    and PR comments) for a date range, using the authenticated GitHub CLI ('gh').
    Use it to reconstruct time spent on code review and PR work.

    Args:
        since: Start of the range: YYYY-MM-DD, an ISO datetime, or 'N days|weeks|months ago'.
        until: End of the range (defaults to 'now'). A bare YYYY-MM-DD includes that whole day.
        repos: Optional comma-separated 'owner/name' list to restrict the results (e.g., 'acme/app, acme/api').
    """
    try:
        start = parse_time_boundary(since)
        end = parse_time_boundary(until, end=True)
    except ValueError as error:
        return f"Error: {error}"

    if start >= end:
        return "Error: 'since' must be earlier than 'until'."
    if end - start > timedelta(days=GH_MAX_RANGE_DAYS):
        return f"Error: GitHub activity can only be read in ranges of up to {GH_MAX_RANGE_DAYS} days. Split the request."

    warnings = []
    try:
        login, events = collect_github_events(start, end, warnings)
    except (RuntimeError, subprocess.TimeoutExpired) as error:
        return f"Error reading GitHub activity: {error}"
    except (KeyError, TypeError, ValueError) as error:
        return f"Error reading GitHub activity: unexpected response from gh ({error})."

    wanted = {repo.strip().lower() for repo in repos.split(",") if repo.strip()}
    if wanted:
        events = [event for event in events if event[2].lower() in wanted]

    return format_github_events(login, start, end, events, warnings)


if __name__ == "__main__":
    mcp.run()
