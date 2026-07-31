import unittest
from unittest.mock import patch, MagicMock
from server import get_jira_issue_id

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

if __name__ == '__main__':
    unittest.main()
