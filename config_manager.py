"""
配置管理器 - 负责读取和写入配置文件
"""

import json
import os
from pathlib import Path

BASE_DIR = Path(__file__).parent
CONFIG_FILE = BASE_DIR / "config.json"
MCP_FILE = BASE_DIR / "mcp.json"


def load_config() -> dict:
    """加载config.json"""
    if not CONFIG_FILE.exists():
        return {
            "baseUrl": "https://api.minimaxi.com/anthropic",
            "model": "MiniMax-M2.5",
            "apiKey": ""
        }
    with open(CONFIG_FILE, "r", encoding="utf-8") as f:
        return json.load(f)


def save_config(config: dict) -> None:
    """保存config.json"""
    with open(CONFIG_FILE, "w", encoding="utf-8") as f:
        json.dump(config, f, ensure_ascii=False, indent=2)


def load_mcp_config() -> dict:
    """加载mcp.json"""
    if not MCP_FILE.exists():
        return {"mcpServers": {}}
    with open(MCP_FILE, "r", encoding="utf-8") as f:
        return json.load(f)


def save_mcp_config(mcp_config: dict) -> None:
    """保存mcp.json"""
    with open(MCP_FILE, "w", encoding="utf-8") as f:
        json.dump(mcp_config, f, ensure_ascii=False, indent=2)


def get_api_key() -> str:
    """获取API密钥"""
    config = load_config()
    return config.get("apiKey", "")


def get_model() -> str:
    """获取模型名称"""
    config = load_config()
    return config.get("model", "MiniMax-M2.5")


def get_base_url() -> str:
    """获取API基础URL"""
    config = load_config()
    return config.get("baseUrl", "https://api.minimaxi.com/anthropic")


def get_mcp_servers() -> dict:
    """获取MCP服务器配置"""
    mcp_config = load_mcp_config()
    return mcp_config.get("mcpServers", {})
