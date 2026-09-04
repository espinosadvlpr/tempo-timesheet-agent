import shutil
import platform
import os

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
    """Inject MCP configuration into the agent's config dictionary."""
    if agent_name in ["claude", "pi"]:
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
