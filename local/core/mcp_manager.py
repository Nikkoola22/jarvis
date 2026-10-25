"""
Module Gestionnaire MCP (Model Context Protocol) pour JARVIS
Permet de connecter JARVIS aux serveurs MCP externes (Spotify, Gmail, Outlook).
"""

import json
import os
import subprocess

CONFIG_PATH = os.path.expanduser("~/jarvis/config_mcp.json")

def load_mcp_config() -> dict:
    if os.path.exists(CONFIG_PATH):
        try:
            with open(CONFIG_PATH, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            pass
    return {"mcpServers": {}}

def list_mcp_servers() -> list:
    """Retourne la liste des serveurs MCP configurés."""
    cfg = load_mcp_config()
    servers = []
    for name, details in cfg.get("mcpServers", {}).items():
        servers.append({
            "name": name,
            "description": details.get("description", ""),
            "command": details.get("command", "")
        })
    return servers

def is_server_configured(server_name: str) -> bool:
    """Vérifie si les clés d'un serveur MCP sont renseignées."""
    cfg = load_mcp_config()
    server = cfg.get("mcpServers", {}).get(server_name)
    if not server:
        return False
    env = server.get("env", {})
    # Vérifier que les variables ne contiennent pas 'YOUR_'
    for k, v in env.items():
        if "YOUR_" in str(v):
            return False
    return True
