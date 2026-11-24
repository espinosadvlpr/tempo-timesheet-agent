import json
import unittest
from datetime import datetime, timezone
from unittest.mock import patch, MagicMock
from server import SERVER_DIR, get_jira_issue_id


class TestServerEnvironment(unittest.TestCase):
    @patch('server.load_dotenv')
    def test_loads_env_from_server_directory(self, mock_load_dotenv):
        import server

        server.load_server_environment()

        mock_load_dotenv.assert_called_once_with(dotenv_path=SERVER_DIR / ".env")



class TestServer(unittest.TestCase):
    @patch('server.requests.get')
    def test_get_jira_issue_id_success(self, mock_get):
        # Mock successful Jira response
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"id": "12763", "key": "SCHE-1"}
        mock_get.return_value = mock_response

        # Need to mock env variables
        with patch.dict('os.environ', {'JIRA_DOMAIN': 'test.atlassian.net', 'JIRA_EMAIL': 'test@example.com', 'JIRA_API_TOKEN': 'token'}):
            issue_id = get_jira_issue_id("SCHE-1")
            
            self.assertEqual(issue_id, 12763)
            mock_get.assert_called_once()
            called_args, called_kwargs = mock_get.call_args
            self.assertEqual(called_args[0], "https://test.atlassian.net/rest/api/3/issue/SCHE-1")
            self.assertEqual(called_kwargs["auth"].username, "test@example.com")
            self.assertEqual(called_kwargs["auth"].password, "token")
            self.assertEqual(called_kwargs["headers"], {"Accept": "application/json"})
            self.assertEqual(called_kwargs["timeout"], 10)

    @patch('server.requests.get')
    def test_get_jira_issue_id_not_found(self, mock_get):
        # Mock failed Jira response
        mock_response = MagicMock()
        mock_response.status_code = 404
        mock_response.text = "Issue Does Not Exist"
        mock_get.return_value = mock_response

        with patch.dict('os.environ', {'JIRA_DOMAIN': 'test.atlassian.net', 'JIRA_EMAIL': 'test@example.com', 'JIRA_API_TOKEN': 'token'}):
            with self.assertRaises(Exception) as context:
                get_jira_issue_id("INVALID-1")
            
            self.assertIn("Failed to fetch Jira issue INVALID-1", str(context.exception))

    @patch('server.requests.post')
    @patch('server.get_jira_issue_id')
    def test_log_tempo_work_success(self, mock_get_jira, mock_post):
        mock_get_jira.return_value = 12763
        
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"tempoWorklogId": 999}
        mock_post.return_value = mock_response
        
        with patch.dict('os.environ', {'TEMPO_TOKEN': 'tempo_token', 'AUTHOR_ACCOUNT_ID': 'author_id'}):
            from server import log_tempo_work
            result = log_tempo_work("SCHE-1", 2.0, "2026-06-19", "Test description", "10:00:00")
            
            self.assertIn("Successfully logged 2.0 hours to SCHE-1", result)
            
            mock_post.assert_called_once()
            called_args, called_kwargs = mock_post.call_args
            self.assertEqual(called_args[0], "https://api.tempo.io/4/worklogs")
            self.assertEqual(called_kwargs["headers"]["Authorization"], "Bearer tempo_token")
            
            import json
            payload = json.loads(called_kwargs["data"])
            self.assertEqual(payload["issueId"], 12763)
            self.assertEqual(payload["timeSpentSeconds"], 7200) # 2.0 * 3600
            self.assertEqual(payload["startDate"], "2026-06-19")
            self.assertEqual(payload["startTime"], "10:00:00")
            self.assertEqual(payload["description"], "Test description")
            self.assertEqual(payload["authorAccountId"], "author_id")

    @patch('server.requests.get')
    def test_search_jira_issues_success(self, mock_get):
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "issues": [
                {
                    "key": "SCHE-99",
                    "fields": {
                        "summary": "Fix frontend bug",
                        "status": {"name": "In Progress"},
                        "assignee": {"displayName": "John Doe"}
                    }
                },
                {
                    "key": "SCHE-100",
                    "fields": {
                        "summary": "Update docs",
                        "status": {"name": "Open"},
                        "assignee": None
                    }
                }
            ]
        }
        mock_get.return_value = mock_response

        with patch.dict('os.environ', {'JIRA_DOMAIN': 'test.atlassian.net', 'JIRA_EMAIL': 'test@example.com', 'JIRA_API_TOKEN': 'token'}):
            from server import search_jira_issues
            result = search_jira_issues("SCHE")
            
            self.assertIn("- [SCHE-99] Fix frontend bug (Status: In Progress | Assignee: John Doe)", result)
            self.assertIn("- [SCHE-100] Update docs (Status: Open | Assignee: Unassigned)", result)
            
            called_args, called_kwargs = mock_get.call_args
            self.assertEqual(called_args[0], "https://test.atlassian.net/rest/api/3/search/jql")
            self.assertIn('project = "SCHE"', called_kwargs["params"]["jql"])

    @patch('server.requests.get')
    def test_search_jira_issues_filters_by_current_user(self, mock_get):
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"issues": []}
        mock_get.return_value = mock_response

        with patch.dict('os.environ', {'JIRA_DOMAIN': 'test.atlassian.net', 'JIRA_EMAIL': 'test@example.com', 'JIRA_API_TOKEN': 'token'}):
            from server import search_jira_issues
            search_jira_issues("SCHE", assignee="me")

            jql = mock_get.call_args[1]["params"]["jql"]
            self.assertIn('project = "SCHE"', jql)
            self.assertIn('assignee = currentUser()', jql)
            self.assertLess(jql.index('assignee'), jql.index('ORDER BY'))

    @patch('server.requests.get')
    def test_search_jira_issues_filters_by_assignee_value(self, mock_get):
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"issues": []}
        mock_get.return_value = mock_response

        with patch.dict('os.environ', {'JIRA_DOMAIN': 'test.atlassian.net', 'JIRA_EMAIL': 'test@example.com', 'JIRA_API_TOKEN': 'token'}):
            from server import search_jira_issues
            search_jira_issues("SCHE", assignee='abc"123')

            jql = mock_get.call_args[1]["params"]["jql"]
            self.assertIn('assignee = "abc\\"123"', jql)

    @patch('server.requests.get')
    def test_search_jira_issues_without_assignee_keeps_default_jql(self, mock_get):
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"issues": []}
        mock_get.return_value = mock_response

        with patch.dict('os.environ', {'JIRA_DOMAIN': 'test.atlassian.net', 'JIRA_EMAIL': 'test@example.com', 'JIRA_API_TOKEN': 'token'}):
            from server import search_jira_issues
            search_jira_issues("SCHE")

            self.assertNotIn('assignee', mock_get.call_args[1]["params"]["jql"])

    @patch('server.requests.get')
    def test_get_jira_issue_returns_description_and_comments(self, mock_get):
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "key": "SCHE-5",
            "fields": {
                "summary": "Add autosave",
                "status": {"name": "To Do"},
                "assignee": {"displayName": "John Doe"},
                "description": {
                    "type": "doc",
                    "content": [
                        {"type": "paragraph", "content": [{"type": "text", "text": "Save drafts automatically."}]},
                        {"type": "bulletList", "content": [
                            {"type": "listItem", "content": [
                                {"type": "paragraph", "content": [{"type": "text", "text": "Debounce 2s"}]}
                            ]},
                            {"type": "listItem", "content": [
                                {"type": "paragraph", "content": [
                                    {"type": "text", "text": "Ping "},
                                    {"type": "mention", "attrs": {"text": "@Jane"}}
                                ]}
                            ]},
                        ]},
                    ],
                },
                "comment": {"comments": [{
                    "author": {"displayName": "Jane Roe"},
                    "created": "2026-10-01T10:00:00.000-0500",
                    "body": {"type": "doc", "content": [
                        {"type": "paragraph", "content": [{"type": "text", "text": "See Figma."}]}
                    ]},
                }]},
            },
        }
        mock_get.return_value = mock_response

        with patch.dict('os.environ', {'JIRA_DOMAIN': 'test.atlassian.net', 'JIRA_EMAIL': 'test@example.com', 'JIRA_API_TOKEN': 'token'}):
            from server import get_jira_issue
            result = get_jira_issue("SCHE-5")

            self.assertIn("[SCHE-5] Add autosave", result)
            self.assertIn("Status: To Do | Assignee: John Doe", result)
            self.assertIn("Save drafts automatically.", result)
            self.assertIn("- Debounce 2s", result)
            self.assertIn("- Ping @Jane", result)
            self.assertIn("Jane Roe", result)
            self.assertIn("See Figma.", result)

            called_args, _ = mock_get.call_args
            self.assertEqual(called_args[0], "https://test.atlassian.net/rest/api/3/issue/SCHE-5")

    @patch('server.requests.get')
    def test_get_jira_issue_handles_empty_description(self, mock_get):
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "key": "SCHE-6",
            "fields": {"summary": "Bare", "status": {"name": "Open"}, "assignee": None,
                       "description": None, "comment": {"comments": []}},
        }
        mock_get.return_value = mock_response

        with patch.dict('os.environ', {'JIRA_DOMAIN': 'test.atlassian.net', 'JIRA_EMAIL': 'test@example.com', 'JIRA_API_TOKEN': 'token'}):
            from server import get_jira_issue
            result = get_jira_issue("SCHE-6")

            self.assertIn("Assignee: Unassigned", result)
            self.assertIn("(No description)", result)
            self.assertIn("(No comments)", result)

    @patch('server.requests.get')
    def test_get_jira_issue_not_found(self, mock_get):
        mock_response = MagicMock()
        mock_response.status_code = 404
        mock_response.text = "Issue Does Not Exist"
        mock_get.return_value = mock_response

        with patch.dict('os.environ', {'JIRA_DOMAIN': 'test.atlassian.net', 'JIRA_EMAIL': 'test@example.com', 'JIRA_API_TOKEN': 'token'}):
            from server import get_jira_issue
            result = get_jira_issue("NOPE-1")

            self.assertIn("Failed to fetch Jira issue", result)
            self.assertIn("404", result)

    @patch('server.requests.get')
    def test_search_jira_projects_success(self, mock_get):
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "values": [
                {
                    "key": "SCHE",
                    "name": "Scheduler App",
                    "style": "classic"
                },
                {
                    "key": "IA",
                    "name": "Internal Admin",
                    "style": "next-gen"
                }
            ]
        }
        mock_get.return_value = mock_response

        with patch.dict('os.environ', {'JIRA_DOMAIN': 'test.atlassian.net', 'JIRA_EMAIL': 'test@example.com', 'JIRA_API_TOKEN': 'token'}):
            from server import search_jira_projects
            result = search_jira_projects("admin")
            
            self.assertIn("- [SCHE] Scheduler App (Style: classic)", result)
            self.assertIn("- [IA] Internal Admin (Style: next-gen)", result)
            
            called_args, called_kwargs = mock_get.call_args
            self.assertEqual(called_args[0], "https://test.atlassian.net/rest/api/3/project/search")
            self.assertEqual(called_kwargs["params"]["query"], "admin")

    @patch('server.subprocess.check_output')
    @patch('server.Path.is_dir')
    @patch('server.Path.exists')
    def test_get_historical_git_activity(self, mock_exists, mock_is_dir, mock_subprocess):
        # Setup mocks so paths appear valid
        mock_exists.return_value = True
        mock_is_dir.return_value = True
        
        # Subprocess mock needs to handle two types of calls:
        # 1. git config user.email
        # 2. git log ...
        def mock_check_output(cmd, **kwargs):
            if "config" in cmd:
                return "test@example.com\n"
            if "log" in cmd:
                # Let's say one repo has commits and the other doesn't
                if "repo1" in kwargs.get("cwd", ""):
                    return "2026-06-01 | a1b2c3d | Initial commit"
                else:
                    return ""
            return ""

        mock_subprocess.side_effect = mock_check_output

        from server import get_historical_git_activity
        result = get_historical_git_activity("/projects/repo1, /projects/repo2", "3 weeks ago")
        
        self.assertIn("Found activity for 'test@example.com':", result)
        self.assertIn("Repository: repo1", result)
        self.assertIn("a1b2c3d | Initial commit", result)
        self.assertIn("Repository: repo2", result)
        self.assertIn("(No commits found in this date range)", result)


def gh_result(stdout="", returncode=0, stderr=""):
    return MagicMock(stdout=stdout, returncode=returncode, stderr=stderr)


GRAPHQL_PAYLOAD = json.dumps({"data": {"viewer": {
    "login": "dev",
    "contributionsCollection": {
        "pullRequestContributions": {"nodes": [{
            "occurredAt": "2026-06-02T09:15:00Z",
            "pullRequest": {"number": 12, "title": "Add retries", "url": "https://github.com/acme/app/pull/12",
                            "repository": {"nameWithOwner": "acme/app"}},
        }]},
        "pullRequestReviewContributions": {"nodes": [{
            "occurredAt": "2026-06-02T14:30:00Z",
            "pullRequestReview": {"state": "APPROVED", "url": "https://github.com/acme/api/pull/7#review-1"},
            "pullRequest": {"number": 7, "title": "Fix auth", "url": "https://github.com/acme/api/pull/7",
                            "repository": {"nameWithOwner": "acme/api"}},
        }]},
    },
}}})

SEARCH_LINE = json.dumps({"number": 7, "title": "Fix auth", "repo": "acme/api"})
ISSUE_COMMENTS = "\n".join([
    json.dumps({"login": "dev", "at": "2026-06-02T15:00:00Z", "url": "https://github.com/acme/api/pull/7#c1"}),
    json.dumps({"login": "someone-else", "at": "2026-06-02T15:05:00Z", "url": "https://github.com/acme/api/pull/7#c2"}),
])


def fake_gh(args_list):
    args = args_list[1:]
    if args[:2] == ["api", "graphql"]:
        return gh_result(GRAPHQL_PAYLOAD)
    if "search/issues" in args:
        return gh_result(SEARCH_LINE)
    if any(part.endswith("/issues/7/comments") for part in args):
        return gh_result(ISSUE_COMMENTS)
    if any(part.endswith("/pulls/7/comments") for part in args):
        return gh_result("")
    raise AssertionError(f"Unexpected gh call: {args}")


class TestGithubActivity(unittest.TestCase):
    def setUp(self):
        # Pin the gh backend so a real GITHUB_TOKEN in mcp-server/.env never triggers network calls.
        env = patch.dict('os.environ', {'GITHUB_ACTIVITY_BACKEND': 'gh', 'GITHUB_TOKEN': ''})
        env.start()
        self.addCleanup(env.stop)

    @patch('server.subprocess.run')
    def test_reports_prs_reviews_and_own_comments_by_day(self, mock_run):
        mock_run.side_effect = lambda cmd, **kwargs: fake_gh(cmd)

        from server import get_github_activity
        result = get_github_activity("2026-06-01", "2026-06-03")

        self.assertIn("GitHub activity for 'dev' (times in UTC)", result)
        self.assertIn("2026-06-02", result)
        self.assertIn("09:15 | PR opened | acme/app#12 | Add retries", result)
        self.assertIn("14:30 | Review approved | acme/api#7 | Fix auth", result)
        self.assertIn("15:00 | Comment | acme/api#7 | Fix auth", result)
        self.assertNotIn("#c2", result)  # Comments from other users are ignored.

    @patch('server.subprocess.run')
    def test_filters_by_repos(self, mock_run):
        mock_run.side_effect = lambda cmd, **kwargs: fake_gh(cmd)

        from server import get_github_activity
        result = get_github_activity("2026-06-01", "2026-06-03", repos="ACME/app")

        self.assertIn("acme/app#12", result)
        self.assertNotIn("acme/api#7", result)

    @patch('server.subprocess.run')
    def test_reports_when_gh_is_not_installed(self, mock_run):
        mock_run.side_effect = FileNotFoundError()

        from server import get_github_activity
        result = get_github_activity("2026-06-01", "2026-06-03")

        self.assertIn("GitHub CLI (gh) is not installed", result)

    @patch('server.subprocess.run')
    def test_reports_gh_failure(self, mock_run):
        mock_run.return_value = gh_result(returncode=1, stderr="gh: not logged in")

        from server import get_github_activity
        result = get_github_activity("2026-06-01", "2026-06-03")

        self.assertIn("Error reading GitHub activity", result)
        self.assertIn("not logged in", result)

    @patch('server.subprocess.run')
    def test_rejects_invalid_ranges_without_calling_gh(self, mock_run):
        from server import get_github_activity

        self.assertIn("Unsupported date", get_github_activity("last tuesday"))
        self.assertIn("earlier than", get_github_activity("2026-06-03", "2026-06-01"))
        self.assertIn("up to 365 days", get_github_activity("2024-01-01", "2026-06-01"))
        mock_run.assert_not_called()

    def test_backend_selection(self):
        from server import GhCliClient, GithubTokenClient, get_github_client

        with patch.dict('os.environ', {'GITHUB_ACTIVITY_BACKEND': 'auto', 'GITHUB_TOKEN': ''}):
            self.assertIsInstance(get_github_client(), GhCliClient)
        with patch.dict('os.environ', {'GITHUB_ACTIVITY_BACKEND': 'auto', 'GITHUB_TOKEN': 'ghp_x'}):
            self.assertIsInstance(get_github_client(), GithubTokenClient)
        with patch.dict('os.environ', {'GITHUB_ACTIVITY_BACKEND': 'gh', 'GITHUB_TOKEN': 'ghp_x'}):
            self.assertIsInstance(get_github_client(), GhCliClient)
        with patch.dict('os.environ', {'GITHUB_ACTIVITY_BACKEND': 'token', 'GITHUB_TOKEN': ''}):
            with self.assertRaisesRegex(RuntimeError, "requires GITHUB_TOKEN"):
                get_github_client()
        with patch.dict('os.environ', {'GITHUB_ACTIVITY_BACKEND': 'nope'}):
            with self.assertRaisesRegex(RuntimeError, "Unknown GITHUB_ACTIVITY_BACKEND"):
                get_github_client()

    @patch('server.subprocess.run')
    def test_off_backend_disables_the_tool_without_calling_gh(self, mock_run):
        from server import get_github_activity

        with patch.dict('os.environ', {'GITHUB_ACTIVITY_BACKEND': 'off'}):
            result = get_github_activity("2026-06-01", "2026-06-03")

        self.assertIn("disabled", result)
        mock_run.assert_not_called()

    @patch('server.subprocess.run')
    @patch('server.requests.request')
    def test_token_backend_reports_activity_without_gh(self, mock_request, mock_run):
        def respond(method, url, **kwargs):
            response = MagicMock(status_code=200, links={})
            if url.endswith("/graphql"):
                response.json.return_value = json.loads(GRAPHQL_PAYLOAD)
            elif url.endswith("/search/issues"):
                response.json.return_value = {"items": [{
                    "number": 7, "title": "Fix auth",
                    "repository_url": "https://api.github.com/repos/acme/api",
                }]}
            elif url.endswith("/issues/7/comments"):
                response.json.return_value = [
                    {"user": {"login": "dev"}, "created_at": "2026-06-02T15:00:00Z", "html_url": "https://github.com/acme/api/pull/7#c1"},
                    {"user": {"login": "someone-else"}, "created_at": "2026-06-02T15:05:00Z", "html_url": "https://github.com/acme/api/pull/7#c2"},
                    {"user": None, "created_at": "2026-06-02T15:06:00Z", "html_url": "https://github.com/acme/api/pull/7#c3"},
                ]
            else:
                response.json.return_value = []
            return response

        mock_request.side_effect = respond

        from server import get_github_activity
        with patch.dict('os.environ', {'GITHUB_ACTIVITY_BACKEND': 'auto', 'GITHUB_TOKEN': 'ghp_secret'}):
            result = get_github_activity("2026-06-01", "2026-06-03")

        self.assertIn("09:15 | PR opened | acme/app#12", result)
        self.assertIn("14:30 | Review approved | acme/api#7", result)
        self.assertIn("15:00 | Comment | acme/api#7", result)
        self.assertNotIn("#c2", result)
        self.assertNotIn("#c3", result)
        self.assertNotIn("ghp_secret", result)
        mock_run.assert_not_called()
        for call in mock_request.call_args_list:
            self.assertEqual(call.kwargs["headers"]["Authorization"], "Bearer ghp_secret")

    @patch('server.requests.request')
    def test_token_backend_follows_pagination_and_reports_api_errors(self, mock_request):
        from server import GithubTokenClient

        first = MagicMock(status_code=200, links={"next": {"url": "https://api.github.com/page2"}})
        first.json.return_value = [{"user": {"login": "dev"}, "created_at": "2026-06-02T15:00:00Z", "html_url": "u1"}]
        second = MagicMock(status_code=200, links={})
        second.json.return_value = [{"user": {"login": "dev"}, "created_at": "2026-06-02T16:00:00Z", "html_url": "u2"}]
        mock_request.side_effect = [first, second]

        comments = GithubTokenClient("t").comments("acme/api", "issues", 7)
        self.assertEqual([comment["url"] for comment in comments], ["u1", "u2"])
        self.assertIsNone(mock_request.call_args_list[1].kwargs.get("params"))

        mock_request.side_effect = None
        mock_request.return_value = MagicMock(status_code=401, text="Bad credentials")
        with self.assertRaisesRegex(RuntimeError, "401"):
            GithubTokenClient("t").graphql(datetime(2026, 6, 1, tzinfo=timezone.utc), datetime(2026, 6, 2, tzinfo=timezone.utc))

    def test_parses_relative_and_date_only_boundaries(self):
        from server import parse_time_boundary

        now = datetime.now(timezone.utc)
        self.assertAlmostEqual((now - parse_time_boundary("2 weeks ago")).days, 14, delta=1)
        self.assertEqual(parse_time_boundary("2026-06-03", end=True), datetime(2026, 6, 4, tzinfo=timezone.utc))
        self.assertEqual(parse_time_boundary("2026-06-03"), datetime(2026, 6, 3, tzinfo=timezone.utc))


if __name__ == '__main__':
    unittest.main()
