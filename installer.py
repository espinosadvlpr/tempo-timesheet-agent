import shutil
import platform
import os
import subprocess

def get_available_binary() -> str:
    """Detect if uv is available, fallback to python."""
    if shutil.which("uv"):
        return "uv"
    return "python"

def get_os_env() -> str:
    """Detect OS environment, distinguishing plain Linux from WSL."""
    system = platform.system().lower()
    
    if system == "linux":
        try:
            with open("/proc/version", "r") as f:
                version_info = f.read().lower()
                if "microsoft" in version_info or "wsl" in version_info:
                    return "wsl"
        except FileNotFoundError:
            pass
        return "linux"
        
    return system

def get_config_path(agent_name: str, os_env: str) -> str:
    """Return default absolute config path for an agent based on OS environment."""
    if agent_name == "claude":
        if os_env in ["windows", "wsl"]:
            base = os.environ.get("APPDATA", "%APPDATA%")
            return os.path.join(base, "Claude", "claude_desktop_config.json").replace("/", os.sep)
        elif os_env == "darwin":
            return os.path.expanduser("~/Library/Application Support/Claude/claude_desktop_config.json")
        else:
            return os.path.expanduser("~/.config/Claude/claude_desktop_config.json")
    else:
        # opencode, antigravity, pi
        if os_env == "windows":
            base = os.environ.get("APPDATA", "%APPDATA%")
            return os.path.join(base, agent_name, f"{agent_name}.json").replace("/", os.sep)
        else:
            return os.path.expanduser(f"~/.config/{agent_name}/{agent_name}.json")

def inject_mcp_config(current_config: dict, agent_name: str, mcp_name: str, command: list) -> dict:
    """Inject MCP configuration into an agent config dictionary."""
    if agent_name == "pi":
        raise ValueError(
            "Pi uses repository-local settings and extensions; legacy MCP injection is unsupported."
        )

    if agent_name == "claude":
        root_key = "mcpServers"
        mcp_config = {
            "command": command[0],
            "args": command[1:]
        }
    else: # opencode, antigravity
        root_key = "mcp"
        mcp_config = {
            "type": "local",
            "command": command,
            "enabled": True
        }
        
    if root_key not in current_config:
        current_config[root_key] = {}
        
    current_config[root_key][mcp_name] = mcp_config
    return current_config

def generate_wsl_proxy_bat(linux_dir: str, binary: str, script: str) -> str:
    """Generate a batch script proxy for WSL."""
    return f'@echo off\nwsl.exe -d Ubuntu -e bash -c "cd {linux_dir} && {binary} {script}"'

def resolve_windows_appdata_from_wsl() -> str | None:
    """Resolve the Windows host's APPDATA folder from inside WSL, as a WSL-mounted path.

    WSL does not inherit Windows env vars, so APPDATA has to be fetched through
    interop (cmd.exe) and translated from a C:\\... path to /mnt/c/... via wslpath.
    """
    try:
        win_appdata = subprocess.check_output(
            ["cmd.exe", "/c", "echo %APPDATA%"],
            stderr=subprocess.DEVNULL,
        ).decode("utf-8").strip()

        if not win_appdata or "%APPDATA%" in win_appdata:
            return None

        return subprocess.check_output(
            ["wslpath", "-u", win_appdata]
        ).decode("utf-8").strip()
    except Exception:
        return None

def detect_claude_cli() -> str | None:
    """Return the Claude Code CLI's config path if the CLI is installed, else None.

    The CLI always resolves ~/.claude.json on the filesystem it runs on -- no
    Windows bridging needed even under WSL.
    """
    if shutil.which("claude"):
        return os.path.expanduser("~/.claude.json")
    return None

def detect_claude_desktop(os_env: str) -> str | None:
    """Return the Claude Desktop app's config path if its config dir exists, else None."""
    if os_env == "wsl":
        appdata = resolve_windows_appdata_from_wsl()
        if appdata and os.path.isdir(os.path.join(appdata, "Claude")):
            return os.path.join(appdata, "Claude", "claude_desktop_config.json")
        return None
    elif os_env == "windows":
        appdata = os.environ.get("APPDATA")
        if appdata and os.path.isdir(os.path.join(appdata, "Claude")):
            return os.path.join(appdata, "Claude", "claude_desktop_config.json")
        return None
    elif os_env == "darwin":
        base = os.path.expanduser("~/Library/Application Support/Claude")
        return os.path.join(base, "claude_desktop_config.json") if os.path.isdir(base) else None
    else:
        base = os.path.expanduser("~/.config/Claude")
        return os.path.join(base, "claude_desktop_config.json") if os.path.isdir(base) else None

def detect_claude_installations(os_env: str) -> dict:
    """Detect which Claude product(s) are actually installed and their config paths."""
    return {
        "cli": detect_claude_cli(),
        "desktop": detect_claude_desktop(os_env),
    }
