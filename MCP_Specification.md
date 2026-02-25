# 圆桌会议系统 MCP 接口说明书

## 1. 概述

MCP (Model Context Protocol) 服务器为圆桌会议系统提供外部 API 接口，支持通过 JSON-RPC 2.0 协议调用所有核心功能。

## 2. 连接方式

### 2.1 stdio 模式

```json
{
  "mcpServers": {
    "Roundtable": {
      "command": "python3",
      "args": ["mcp_server.py"]
    }
  }
}
```

### 2.2 请求格式

```json
{
  "jsonrpc": "2.0",
  "id": 1,
  "method": "tools/call",
  "params": {
    "name": "工具名称",
    "arguments": {
      "参数1": "值1",
      "参数2": "值2"
    }
  }
}
```

### 2.3 响应格式

```json
{
  "jsonrpc": "2.0",
  "id": 1,
  "result": {
    "content": [
      {
        "type": "text",
        "text": "返回内容"
      }
    ]
  }
}
```

---

## 3. 工具列表

### 3.1 角色管理工具

#### 3.1.1 list_roles

列出所有角色

**参数：** 无

**返回：**
```json
[
  {"id": "7571db781106", "name": "DevilsAdvocate", "description": "专门唱反调"},
  {"id": "f7a80bafc842", "name": "GrowthStrategist", "description": "习惯寻找机会"}
]
```

---

#### 3.1.2 get_role_identity

获取角色 IDENTITY 信息

**参数：**
| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| role_id | string | 是 | 角色 ID |

**返回：** IDENTITY.md 内容

---

#### 3.1.3 create_role

创建新角色

**参数：**
| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| name | string | 是 | 角色名称 |
| description | string | 是 | 角色描述 |
| notes | string | 否 | 注意事项 |

**返回：** `"创建成功"` 或 `"创建失败"`

---

#### 3.1.4 delete_role

删除角色

**参数：**
| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| role_id | string | 是 | 角色 ID |

**返回：** `"删除成功"` 或 `"删除失败"`

---

### 3.2 会议管理工具

#### 3.2.1 list_meetings

列出所有会议

**参数：** 无

**返回：**
```json
[
  {"meeting_id": "50eab6f9d55d", "topic": "主题", "status": "completed"},
  {"meeting_id": "67baffe9b4da", "topic": "主题", "status": "pending"}
]
```

---

#### 3.2.2 create_meeting

创建新会议

**参数：**
| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| topic | string | 是 | 会议主题 |
| role_ids | array | 是 | 角色 ID 列表 |
| rounds | integer | 否 | 发言轮次，默认 3 |

**返回：** `"会议创建成功，ID: {meeting_id}"` 或 `"会议创建失败"`

---

#### 3.2.3 get_meeting

获取会议信息

**参数：**
| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| meeting_id | string | 是 | 会议 ID |

**返回：**
```json
{
  "meeting_id": "50eab6f9d55d",
  "topic": "主题",
  "roles": ["DevilsAdvocate", "GrowthStrategist"],
  "rounds": 3,
  "status": "completed"
}
```

---

#### 3.2.4 get_meeting_minutes

获取会议纪要

**参数：**
| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| meeting_id | string | 是 | 会议 ID |

**返回：** 会议纪要 markdown 内容

---

#### 3.2.5 delete_meeting

删除会议

**参数：**
| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| meeting_id | string | 是 | 会议 ID |

**返回：** `"删除成功"` 或 `"删除失败"`

---

#### 3.2.6 update_meeting_topic

更新会议主题

**参数：**
| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| meeting_id | string | 是 | 会议 ID |
| topic | string | 是 | 新主题 |

**返回：** `"更新成功"` 或 `"更新失败"`

---

#### 3.2.7 add_meeting_participant

添加会议参与者

**参数：**
| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| meeting_id | string | 是 | 会议 ID |
| role_id | string | 是 | 角色 ID |

**返回：** `"添加成功"` 或 `"添加失败"`

---

#### 3.2.8 remove_meeting_participant

删除会议参与者

**参数：**
| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| meeting_id | string | 是 | 会议 ID |
| role_id | string | 是 | 角色 ID |

**返回：** `"删除成功"` 或 `"删除失败"`

---

#### 3.2.9 get_meeting_status

获取会议状态

**参数：**
| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| meeting_id | string | 是 | 会议 ID |

**返回：**
```json
{
  "meeting_id": "50eab6f9d55d",
  "topic": "主题",
  "status": "completed",
  "consensus": "...",
  "conclusion": "..."
}
```

---

#### 3.2.10 update_meeting_rounds

更新会议轮次

**参数：**
| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| meeting_id | string | 是 | 会议 ID |
| rounds | integer | 是 | 发言轮次数 |

**返回：** `"更新成功"` 或 `"更新失败"`

---

#### 3.2.11 start_meeting

启动会议（开始圆桌讨论）

**参数：**
| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| meeting_id | string | 是 | 会议 ID |

**返回：**
- `"会议完成"` - 会议成功完成
- `"会议不存在"` - 会议 ID 无效
- `"会议已结束，如需继续讨论请使用continue_discussion"` - 会议已完成
- `"会议正在进行中"` - 会议已在运行

**注意：** 此工具会实际运行 LLM 调用，生成会议纪要。

---

## 4. 错误响应

### 4.1 错误格式

```json
{
  "jsonrpc": "2.0",
  "id": 1,
  "error": {
    "code": -32601,
    "message": "Unknown tool: xxx"
  }
}
```

### 4.2 错误码

| 错误码 | 说明 |
|--------|------|
| -32600 | 无效请求 |
| -32601 | 未知工具 |
| -32603 | 内部错误 |

---

## 5. 使用示例

### 5.1 创建会议并启动

```bash
# 1. 列出角色
echo '{"jsonrpc":"2.0","id":1,"method":"tools/call","params":{"name":"list_roles","arguments":{}}}' | python3 mcp_server.py

# 2. 创建会议
echo '{"jsonrpc":"2.0","id":2,"method":"tools/call","params":{"name":"create_meeting","arguments":{"topic":"测试主题","role_ids":["7571db781106"],"rounds":2}}}' | python3 mcp_server.py

# 3. 启动会议
echo '{"jsonrpc":"2.0","id":3,"method":"tools/call","params":{"name":"start_meeting","arguments":{"meeting_id":"50eab6f9d55d"}}}' | python3 mcp_server.py

# 4. 查看会议纪要
echo '{"jsonrpc":"2.0","id":4,"method":"tools/call","params":{"name":"get_meeting_minutes","arguments":{"meeting_id":"50eab6f9d55d"}}}' | python3 mcp_server.py
```

---

## 6. 会议状态说明

| 状态 | 说明 | 可用操作 |
|------|------|----------|
| `pending` | 待开始 | start_meeting |
| `running` | 进行中 | - |
| `completed` | 已完成 | get_meeting_minutes |
