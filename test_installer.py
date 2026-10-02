import io
import json
import os
import tempfile
import unittest
from contextlib import chdir, redirect_stdout
from pathlib import Path
from unittest.mock import patch, mock_open

import installer
import setup

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

    def test_inject_mcp_config_pi_is_unsupported(self):
        with self.assertRaisesRegex(ValueError, "repository-local"):
            installer.inject_mcp_config({}, "pi", "tempo", ["uv", "run"])

    @patch("setup.os.symlink")
    @patch("setup.installer.inject_mcp_config")
    @patch("setup.install_pi_resources", return_value=True)
    @patch("setup.installer.detect_claude_installations", return_value={"cli": None, "desktop": None})
    @patch("setup.installer.get_available_binary", return_value="uv")
    @patch("setup.installer.get_os_env", return_value="linux")
    @patch("builtins.input", side_effect=["4"])
    def test_configure_agents_pi_uses_repository_local_resources(
        self,
        mock_input,
        mock_os_env,
        mock_binary,
        mock_claude_installations,
        mock_install_dependencies,
        mock_inject_mcp_config,
        mock_symlink,
    ):
        output = io.StringIO()
        with redirect_stdout(output):
            setup.configure_agents()

        mock_inject_mcp_config.assert_not_called()
        mock_symlink.assert_not_called()
        mock_install_dependencies.assert_called_once_with(Path(setup.__file__).parent.resolve())
        self.assertIn(
            "Pi: Tempo extension and skills are registered globally; restart Pi sessions.",
            output.getvalue(),
        )

    def make_pi_install_tree(self, root):
        repo_root = root / "checkout"
        extension_dir = repo_root / ".pi" / "extensions" / "tempo-mcp"
        extension_dir.mkdir(parents=True)
        (extension_dir / "index.ts").write_text("export {};", encoding="utf-8")
        (repo_root / "skills").mkdir()
        return repo_root, extension_dir

    @patch("setup.subprocess.run")
    @patch("setup.shutil.which")
    def test_install_pi_resources_empty_agent_dir_uses_home_default(self, mock_which, mock_run):
        mock_which.side_effect = lambda tool: f"/usr/bin/{tool}"
        mock_run.return_value.returncode = 0
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            repo_root, _ = self.make_pi_install_tree(root)
            agent_home = root / "home"
            agent_home.mkdir()
            working_dir = root / "working"
            working_dir.mkdir()
            with patch.dict(os.environ, {"HOME": str(agent_home), "PI_CODING_AGENT_DIR": ""}), chdir(working_dir):
                self.assertTrue(setup.install_pi_resources(repo_root))
            self.assertTrue((agent_home / ".pi" / "agent" / "settings.json").is_file())
            self.assertFalse((working_dir / "settings.json").exists())

    @patch("setup.subprocess.run")
    @patch("setup.shutil.which")
    def test_install_pi_resources_reads_settings_after_npm_ci(self, mock_which, mock_run):
        mock_which.side_effect = lambda tool: f"/usr/bin/{tool}"
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            repo_root, _ = self.make_pi_install_tree(root)
            agent_dir = root / "agent"
            agent_dir.mkdir()
            settings_path = agent_dir / "settings.json"
            settings_path.write_text('{"extensions": ["old"]}', encoding="utf-8")

            def update_settings_during_npm(*args, **kwargs):
                settings_path.write_text('{"extensions": ["concurrent"], "keep": true}', encoding="utf-8")
                return type("Completed", (), {"returncode": 0})()

            mock_run.side_effect = update_settings_during_npm
            with patch.dict(os.environ, {"PI_CODING_AGENT_DIR": str(agent_dir)}):
                self.assertTrue(setup.install_pi_resources(repo_root))
            updated = json.loads(settings_path.read_text(encoding="utf-8"))
            self.assertEqual(updated["extensions"][0], "concurrent")
            self.assertTrue(updated["keep"])

    @patch("setup.subprocess.run")
    @patch("setup.shutil.which")
    def test_install_pi_resources_refuses_settings_changed_after_read(self, mock_which, mock_run):
        mock_which.side_effect = lambda tool: f"/usr/bin/{tool}"
        mock_run.return_value.returncode = 0
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            repo_root, _ = self.make_pi_install_tree(root)
            agent_dir = root / "agent"
            agent_dir.mkdir()
            settings_path = agent_dir / "settings.json"
            settings_path.write_text('{"keep": "original"}', encoding="utf-8")
            real_named_temporary_file = tempfile.NamedTemporaryFile

            def create_then_concurrent_update(*args, **kwargs):
                file_context = real_named_temporary_file(*args, **kwargs)

                class ConcurrentUpdate:
                    def __enter__(self):
                        return file_context.__enter__()

                    def __exit__(self, *exc):
                        result = file_context.__exit__(*exc)
                        settings_path.write_text('{"keep": "concurrent"}', encoding="utf-8")
                        return result

                return ConcurrentUpdate()

            with patch.dict(os.environ, {"PI_CODING_AGENT_DIR": str(agent_dir)}), \
                 patch("setup.tempfile.NamedTemporaryFile", side_effect=create_then_concurrent_update):
                self.assertFalse(setup.install_pi_resources(repo_root))
            self.assertEqual(settings_path.read_text(encoding="utf-8"), '{"keep": "concurrent"}')
            self.assertEqual(list(agent_dir.iterdir()), [settings_path])

    @patch("setup.os.replace", side_effect=OSError("replace denied"))
    @patch("setup.subprocess.run")
    @patch("setup.shutil.which")
    def test_install_pi_resources_cleans_temp_file_when_replace_fails(self, mock_which, mock_run, mock_replace):
        mock_which.side_effect = lambda tool: f"/usr/bin/{tool}"
        mock_run.return_value.returncode = 0
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            repo_root, _ = self.make_pi_install_tree(root)
            agent_dir = root / "agent"
            agent_dir.mkdir()
            settings_path = agent_dir / "settings.json"
            settings_path.write_text('{"keep": true}', encoding="utf-8")
            with patch.dict(os.environ, {"PI_CODING_AGENT_DIR": str(agent_dir)}):
                self.assertFalse(setup.install_pi_resources(repo_root))
            self.assertEqual(list(agent_dir.iterdir()), [settings_path])

    @patch("setup.subprocess.run")
    @patch("setup.shutil.which")
    def test_install_pi_resources_registers_global_paths_and_preserves_settings(self, mock_which, mock_run):
        mock_which.side_effect = lambda tool: f"/usr/bin/{tool}"
        mock_run.return_value.returncode = 0
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            repo_root, extension_dir = self.make_pi_install_tree(root)
            agent_dir = root / "pi-agent"
            agent_dir.mkdir()
            settings_path = agent_dir / "settings.json"
            settings_path.write_text(json.dumps({
                "extensions": ["-builtin:codemode", "/existing/extension.ts"],
                "skills": ["/existing/skills"],
                "other": {"kept": True},
            }), encoding="utf-8")
            output = io.StringIO()

            with patch.dict(os.environ, {"PI_CODING_AGENT_DIR": str(agent_dir)}), redirect_stdout(output):
                result = setup.install_pi_resources(repo_root)

            self.assertTrue(result)
            settings = json.loads(settings_path.read_text(encoding="utf-8"))
            self.assertEqual(settings["extensions"], [
                "-builtin:codemode", "/existing/extension.ts", str((extension_dir / "index.ts").resolve())
            ])
            self.assertEqual(settings["skills"], ["/existing/skills", str((repo_root / "skills").resolve())])
            self.assertEqual(settings["other"], {"kept": True})
            mock_run.assert_called_once_with(["npm", "ci"], cwd=extension_dir, check=False)

    @patch("setup.subprocess.run")
    @patch("setup.shutil.which")
    def test_install_pi_resources_is_idempotent(self, mock_which, mock_run):
        mock_which.side_effect = lambda tool: f"/usr/bin/{tool}"
        mock_run.return_value.returncode = 0
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            repo_root, _ = self.make_pi_install_tree(root)
            agent_dir = root / "agent"
            agent_dir.mkdir()
            with patch.dict(os.environ, {"PI_CODING_AGENT_DIR": str(agent_dir)}):
                self.assertTrue(setup.install_pi_resources(repo_root))
                settings_path = agent_dir / "settings.json"
                first = settings_path.read_bytes()
                self.assertTrue(setup.install_pi_resources(repo_root))
                self.assertEqual(settings_path.read_bytes(), first)

    @patch("setup.subprocess.run")
    @patch("setup.shutil.which", return_value=None)
    def test_install_pi_resources_requires_uv_without_writing(self, mock_which, mock_run):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            repo_root, _ = self.make_pi_install_tree(root)
            agent_dir = root / "agent"
            agent_dir.mkdir()
            settings_path = agent_dir / "settings.json"
            settings_path.write_text('{"keep": true}', encoding="utf-8")
            with patch.dict(os.environ, {"PI_CODING_AGENT_DIR": str(agent_dir)}):
                self.assertFalse(setup.install_pi_resources(repo_root))
            self.assertEqual(settings_path.read_text(encoding="utf-8"), '{"keep": true}')
            mock_run.assert_not_called()

    @patch("setup.subprocess.run")
    @patch("setup.shutil.which", side_effect=lambda tool: f"/usr/bin/{tool}")
    def test_install_pi_resources_rejects_missing_source_paths(self, mock_which, mock_run):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            repo_root = root / "checkout"
            repo_root.mkdir()
            agent_dir = root / "agent"
            agent_dir.mkdir()
            settings_path = agent_dir / "settings.json"
            settings_path.write_text('{"keep": true}', encoding="utf-8")
            with patch.dict(os.environ, {"PI_CODING_AGENT_DIR": str(agent_dir)}):
                self.assertFalse(setup.install_pi_resources(repo_root))
            self.assertEqual(settings_path.read_text(encoding="utf-8"), '{"keep": true}')
            mock_run.assert_not_called()

    @patch("setup.subprocess.run")
    @patch("setup.shutil.which", side_effect=lambda tool: f"/usr/bin/{tool}")
    def test_install_pi_resources_rejects_resource_list_conflict(self, mock_which, mock_run):
        mock_run.return_value.returncode = 0
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            repo_root, _ = self.make_pi_install_tree(root)
            agent_dir = root / "agent"
            agent_dir.mkdir()
            settings_path = agent_dir / "settings.json"
            settings_path.write_text('{"extensions": {"existing": true}}', encoding="utf-8")
            with patch.dict(os.environ, {"PI_CODING_AGENT_DIR": str(agent_dir)}):
                self.assertFalse(setup.install_pi_resources(repo_root))
            self.assertEqual(settings_path.read_text(encoding="utf-8"), '{"extensions": {"existing": true}}')
            mock_run.assert_called_once_with(["npm", "ci"], cwd=repo_root / ".pi" / "extensions" / "tempo-mcp", check=False)

    @patch("setup.subprocess.run")
    @patch("setup.shutil.which", side_effect=lambda tool: f"/usr/bin/{tool}")
    def test_install_pi_resources_rejects_malformed_settings_without_writing(self, mock_which, mock_run):
        mock_run.return_value.returncode = 0
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            repo_root, _ = self.make_pi_install_tree(root)
            agent_dir = root / "agent"
            agent_dir.mkdir()
            settings_path = agent_dir / "settings.json"
            settings_path.write_text("{bad json", encoding="utf-8")
            with patch.dict(os.environ, {"PI_CODING_AGENT_DIR": str(agent_dir)}):
                self.assertFalse(setup.install_pi_resources(repo_root))
            self.assertEqual(settings_path.read_text(encoding="utf-8"), "{bad json")
            mock_run.assert_called_once_with(["npm", "ci"], cwd=repo_root / ".pi" / "extensions" / "tempo-mcp", check=False)

    @patch("setup.subprocess.run")
    @patch("setup.shutil.which", side_effect=lambda tool: f"/usr/bin/{tool}")
    def test_install_pi_resources_does_not_write_after_npm_failure(self, mock_which, mock_run):
        mock_run.return_value.returncode = 1
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            repo_root, _ = self.make_pi_install_tree(root)
            agent_dir = root / "agent"
            agent_dir.mkdir()
            settings_path = agent_dir / "settings.json"
            settings_path.write_text('{"keep": true}', encoding="utf-8")
            with patch.dict(os.environ, {"PI_CODING_AGENT_DIR": str(agent_dir)}):
                self.assertFalse(setup.install_pi_resources(repo_root))
            self.assertEqual(settings_path.read_text(encoding="utf-8"), '{"keep": true}')


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
