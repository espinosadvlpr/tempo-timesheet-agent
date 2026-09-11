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

    @patch('installer.shutil.which')
    def test_detect_claude_cli_found(self, mock_which):
        mock_which.side_effect = lambda x: "/usr/local/bin/claude" if x == "claude" else None
        self.assertEqual(installer.detect_claude_cli(), os.path.expanduser("~/.claude.json"))

    @patch('installer.shutil.which')
    def test_detect_claude_cli_not_found(self, mock_which):
        mock_which.return_value = None
        self.assertIsNone(installer.detect_claude_cli())

    @patch('installer.subprocess.check_output')
    def test_resolve_windows_appdata_from_wsl_success(self, mock_check_output):
        mock_check_output.side_effect = [
            b"C:\\Users\\Test\\AppData\\Roaming\r\n",
            b"/mnt/c/Users/Test/AppData/Roaming\n",
        ]
        self.assertEqual(
            installer.resolve_windows_appdata_from_wsl(),
            "/mnt/c/Users/Test/AppData/Roaming"
        )

    @patch('installer.subprocess.check_output')
    def test_resolve_windows_appdata_from_wsl_interop_broken(self, mock_check_output):
        # Windows-side env var not resolved by cmd.exe interop -> literal %APPDATA%
        mock_check_output.return_value = b"%APPDATA%\r\n"
        self.assertIsNone(installer.resolve_windows_appdata_from_wsl())

    @patch('installer.subprocess.check_output')
    def test_resolve_windows_appdata_from_wsl_subprocess_failure(self, mock_check_output):
        mock_check_output.side_effect = FileNotFoundError
        self.assertIsNone(installer.resolve_windows_appdata_from_wsl())

    @patch('installer.os.path.isdir')
    @patch('installer.resolve_windows_appdata_from_wsl')
    def test_detect_claude_desktop_wsl_found(self, mock_resolve, mock_isdir):
        mock_resolve.return_value = "/mnt/c/Users/Test/AppData/Roaming"
        mock_isdir.return_value = True
        self.assertEqual(
            installer.detect_claude_desktop("wsl"),
            os.path.join("/mnt/c/Users/Test/AppData/Roaming", "Claude", "claude_desktop_config.json")
        )

    @patch('installer.resolve_windows_appdata_from_wsl')
    def test_detect_claude_desktop_wsl_not_found(self, mock_resolve):
        # Real-world WSL case: interop unavailable, no guessed fallback path
        mock_resolve.return_value = None
        self.assertIsNone(installer.detect_claude_desktop("wsl"))

    @patch('installer.os.path.isdir')
    @patch('installer.os.environ.get')
    def test_detect_claude_desktop_windows_found(self, mock_env_get, mock_isdir):
        mock_env_get.return_value = "C:\\Users\\Test\\AppData\\Roaming"
        mock_isdir.return_value = True
        self.assertEqual(
            installer.detect_claude_desktop("windows"),
            os.path.join("C:\\Users\\Test\\AppData\\Roaming", "Claude", "claude_desktop_config.json")
        )

    @patch('installer.os.environ.get')
    def test_detect_claude_desktop_windows_no_appdata(self, mock_env_get):
        mock_env_get.return_value = None
        self.assertIsNone(installer.detect_claude_desktop("windows"))

    @patch('installer.os.path.isdir')
    def test_detect_claude_desktop_darwin_found(self, mock_isdir):
        mock_isdir.return_value = True
        self.assertEqual(
            installer.detect_claude_desktop("darwin"),
            os.path.join(
                os.path.expanduser("~/Library/Application Support/Claude"),
                "claude_desktop_config.json"
            )
        )

    @patch('installer.os.path.isdir')
    def test_detect_claude_desktop_darwin_not_found(self, mock_isdir):
        mock_isdir.return_value = False
        self.assertIsNone(installer.detect_claude_desktop("darwin"))

    @patch('installer.os.path.isdir')
    def test_detect_claude_desktop_linux_found(self, mock_isdir):
        mock_isdir.return_value = True
        self.assertEqual(
            installer.detect_claude_desktop("linux"),
            os.path.join(os.path.expanduser("~/.config/Claude"), "claude_desktop_config.json")
        )

    @patch('installer.os.path.isdir')
    def test_detect_claude_desktop_linux_not_found(self, mock_isdir):
        mock_isdir.return_value = False
        self.assertIsNone(installer.detect_claude_desktop("linux"))

    @patch('installer.detect_claude_desktop')
    @patch('installer.detect_claude_cli')
    def test_detect_claude_installations_composes(self, mock_cli, mock_desktop):
        mock_cli.return_value = "/home/test/.claude.json"
        mock_desktop.return_value = None
        result = installer.detect_claude_installations("wsl")
        self.assertEqual(result, {"cli": "/home/test/.claude.json", "desktop": None})
        mock_cli.assert_called_once_with()
        mock_desktop.assert_called_once_with("wsl")

if __name__ == "__main__":
    unittest.main()
