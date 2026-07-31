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

if __name__ == '__main__':
    unittest.main()
