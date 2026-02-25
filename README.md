# 圆桌会议系统 (Roundtable)

多角色 AI 讨论系统，通过定义不同角色让多个 AI 代表不同观点进行讨论，最终形成共识决策。

## 功能特性

- **角色管理** - 创建、删除角色，每个角色有独立的 IDENTITY.md 定义
- **圆桌讨论** - 多角色轮流发言，自动检测共识达成
- **会议纪要** - 自动生成 Markdown 格式会议纪要
- **时间感知** - 支持时间相关话题的实时搜索
- **MCP 集成** - 支持通过 MCP 协议调用所有功能

## 快速开始

### 1. 克隆项目

```bash
git clone https://github.com/your-repo/roundtable-mcp.git
cd roundtable
```

### 2. 安装依赖

```bash
pip install -r requirements.txt
```

### 3. 配置

```bash
# 复制配置模板
cp config.json.example config.json

# 编辑配置，填入你的 API Key
vim config.json
```

### 4. 启动

```bash
python3 main.py
```

## MCP 部署

### 与 Claude Code 集成

在 Claude Code 配置文件中添加：

```json
{
  "mcpServers": {
    "Roundtable": {
      "command": "/path/to/roundtable/venv/bin/python",
      "args": ["/path/to/roundtable/mcp_server.py"]
    }
  }
}
```

### MCP 工具列表

| 工具 | 说明 |
|------|------|
| list_roles | 列出所有角色 |
| get_role_identity | 获取角色 IDENTITY |
| create_role | 创建角色 |
| delete_role | 删除角色 |
| list_meetings | 列出所有会议 |
| create_meeting | 创建会议 |
| get_meeting | 获取会议信息 |
| get_meeting_minutes | 获取会议纪要 |
| delete_meeting | 删除会议 |
| update_meeting_topic | 更新主题 |
| add_meeting_participant | 添加参与者 |
| remove_meeting_participant | 删除参与者 |
| get_meeting_status | 获取状态 |
| update_meeting_rounds | 更新轮次 |
| start_meeting | 启动会议 |

## 目录结构

```
roundtable/
├── main.py              # 入口文件
├── cli.py               # 命令行界面
├── config_manager.py    # 配置管理
├── role_manager.py      # 角色管理
├── meeting_manager.py   # 会议管理
├── llm_client.py        # LLM 调用
├── mcp_server.py        # MCP 服务器
├── config.json.example  # 配置模板
├── mcp.json.example     # MCP 配置模板
└── requirements.txt    # 依赖
```

## 文档

- [MCP 说明书](docs/MCP_Specification.md)
- [部署说明书](docs/Deployment_Guide.md)

## 依赖

- Python >= 3.8
- anthropic >= 0.83.0

## 许可证

GPL-3.0 license
