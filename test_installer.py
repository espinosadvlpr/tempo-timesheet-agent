import unittest
import os
from unittest.mock import patch, mock_open
import installer

class TestInstaller(unittest.TestCase):
    @patch('installer.shutil.which')
    def test_get_available_binary_uv(self, mock_which):
        # When uv is found, return "uv"
        mock_which.side_effect = lambda x: "/usr/bin/uv" if x == "uv" else None
        self.assertEqual(installer.get_available_binary(), "uv")

    @patch('installer.shutil.which')
    def test_get_available_binary_python(self, mock_which):
        # When uv is not found, return "python"
        mock_which.side_effect = lambda x: "/usr/bin/python" if x == "python" else None
        self.assertEqual(installer.get_available_binary(), "python")

    @patch('installer.platform.system')
    def test_get_os_env_windows(self, mock_system):
        mock_system.return_value = "Windows"
        self.assertEqual(installer.get_os_env(), "windows")

    @patch('installer.platform.system')
    def test_get_os_env_darwin(self, mock_system):
        mock_system.return_value = "Darwin"
        self.assertEqual(installer.get_os_env(), "darwin")

    @patch('installer.platform.system')
    @patch('builtins.open', new_callable=mock_open, read_data="Linux version 5.15.0-71-generic\n")
    def test_get_os_env_linux_plain(self, mock_file, mock_system):
        mock_system.return_value = "Linux"
        self.assertEqual(installer.get_os_env(), "linux")
        mock_file.assert_called_once_with('/proc/version', 'r')

    @patch('installer.platform.system')
    @patch('builtins.open', new_callable=mock_open, read_data="Linux version 4.4.0-19041-Microsoft\n")
    def test_get_os_env_wsl_microsoft(self, mock_file, mock_system):
        mock_system.return_value = "Linux"
        self.assertEqual(installer.get_os_env(), "wsl")
        mock_file.assert_called_once_with('/proc/version', 'r')

    @patch('installer.platform.system')
    @patch('builtins.open', new_callable=mock_open, read_data="Linux version 5.15.90.1-microsoft-standard-WSL2\n")
    def test_get_os_env_wsl_wsl(self, mock_file, mock_system):
        mock_system.return_value = "Linux"
        self.assertEqual(installer.get_os_env(), "wsl")
        mock_file.assert_called_once_with('/proc/version', 'r')

    @patch('installer.platform.system')
    @patch('builtins.open')
    def test_get_os_env_linux_no_proc_version(self, mock_file, mock_system):
        mock_system.return_value = "Linux"
        mock_file.side_effect = FileNotFoundError
        self.assertEqual(installer.get_os_env(), "linux")

    def test_get_config_path_claude(self):
        with patch('installer.os.environ.get', return_value='C:\\Users\\Test\\AppData\\Roaming'):
            # Windows
            self.assertEqual(
                installer.get_config_path("claude", "windows"),
                "C:\\Users\\Test\\AppData\\Roaming/Claude/claude_desktop_config.json".replace("/", os.sep)
            )
            # WSL
            self.assertEqual(
                installer.get_config_path("claude", "wsl"),
                "C:\\Users\\Test\\AppData\\Roaming/Claude/claude_desktop_config.json".replace("/", os.sep)
            )
        
        with patch('installer.os.path.expanduser', return_value='/Users/Test/Library/Application Support/Claude/claude_desktop_config.json'):
            # Darwin
            self.assertEqual(
                installer.get_config_path("claude", "darwin"),
                "/Users/Test/Library/Application Support/Claude/claude_desktop_config.json"
            )
            
        with patch('installer.os.path.expanduser', return_value='/home/test/.config/Claude/claude_desktop_config.json'):
            # Linux
            self.assertEqual(
                installer.get_config_path("claude", "linux"),
                "/home/test/.config/Claude/claude_desktop_config.json"
            )

    def test_get_config_path_opencode(self):
        with patch('installer.os.environ.get', return_value='C:\\Users\\Test\\AppData\\Roaming'):
            self.assertEqual(
                installer.get_config_path("opencode", "windows"),
                "C:\\Users\\Test\\AppData\\Roaming/opencode/opencode.json".replace("/", os.sep)
            )
        
        with patch('installer.os.path.expanduser', return_value='/home/test/.config/opencode/opencode.json'):
            self.assertEqual(
                installer.get_config_path("opencode", "linux"),
                "/home/test/.config/opencode/opencode.json"
            )
            self.assertEqual(
                installer.get_config_path("opencode", "wsl"),
                "/home/test/.config/opencode/opencode.json"
            )

    def test_inject_mcp_config_claude_fresh(self):
        config = {}
        result = installer.inject_mcp_config(config, "claude", "tempo", ["uv", "run", "mcp-server"])
        self.assertIn("mcpServers", result)
        self.assertIn("tempo", result["mcpServers"])
        self.assertEqual(result["mcpServers"]["tempo"]["command"], "uv")
        self.assertEqual(result["mcpServers"]["tempo"]["args"], ["run", "mcp-server"])

    def test_inject_mcp_config_opencode_existing(self):
        config = {"mcp": {"existing": {"command": ["python"]}}}
        result = installer.inject_mcp_config(config, "opencode", "tempo", ["uv", "run"])
        self.assertIn("existing", result["mcp"])
        self.assertIn("tempo", result["mcp"])
        self.assertEqual(result["mcp"]["tempo"]["type"], "local")
        self.assertEqual(result["mcp"]["tempo"]["command"], ["uv", "run"])
        self.assertTrue(result["mcp"]["tempo"]["enabled"])

    def test_generate_wsl_proxy_bat(self):
        result = installer.generate_wsl_proxy_bat("/home/user/project", "uv", "installer.py")
        expected = '@echo off\nwsl.exe -d Ubuntu -e bash -c "cd /home/user/project && uv installer.py"'
        self.assertEqual(result, expected)

if __name__ == "__main__":
    unittest.main()
