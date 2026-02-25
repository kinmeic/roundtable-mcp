#!/usr/bin/env python3
"""
圆桌会议系统 MCP 服务器
"""

import json
import sys
from pathlib import Path

# 添加当前目录到路径
sys.path.insert(0, str(Path(__file__).parent))

import config_manager
import llm_client
import meeting_manager
import role_manager


class MCPServer:
    """MCP服务器"""

    def __init__(self):
        self.tools = {
            "list_roles": {
                "description": "列出所有角色",
                "input_schema": {
                    "type": "object",
                    "properties": {},
                    "required": []
                }
            },
            "get_role_identity": {
                "description": "获取角色IDENTITY信息",
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "role_id": {"type": "string", "description": "角色ID"}
                    },
                    "required": ["role_id"]
                }
            },
            "create_role": {
                "description": "创建新角色",
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "name": {"type": "string", "description": "角色名称"},
                        "description": {"type": "string", "description": "角色描述"},
                        "notes": {"type": "string", "description": "注意事项"}
                    },
                    "required": ["name", "description"]
                }
            },
            "delete_role": {
                "description": "删除角色",
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "role_id": {"type": "string", "description": "角色ID"}
                    },
                    "required": ["role_id"]
                }
            },
            "list_meetings": {
                "description": "列出所有会议",
                "input_schema": {
                    "type": "object",
                    "properties": {},
                    "required": []
                }
            },
            "create_meeting": {
                "description": "创建新会议",
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "topic": {"type": "string", "description": "会议主题"},
                        "role_ids": {"type": "array", "items": {"type": "string"}, "description": "角色ID列表"},
                        "rounds": {"type": "integer", "description": "发言轮次，默认3"}
                    },
                    "required": ["topic", "role_ids"]
                }
            },
            "get_meeting": {
                "description": "获取会议信息",
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "meeting_id": {"type": "string", "description": "会议ID"}
                    },
                    "required": ["meeting_id"]
                }
            },
            "get_meeting_minutes": {
                "description": "获取会议纪要",
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "meeting_id": {"type": "string", "description": "会议ID"}
                    },
                    "required": ["meeting_id"]
                }
            },
            "delete_meeting": {
                "description": "删除会议",
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "meeting_id": {"type": "string", "description": "会议ID"}
                    },
                    "required": ["meeting_id"]
                }
            },
            "update_meeting_topic": {
                "description": "更新会议主题",
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "meeting_id": {"type": "string", "description": "会议ID"},
                        "topic": {"type": "string", "description": "新主题"}
                    },
                    "required": ["meeting_id", "topic"]
                }
            },
            "add_meeting_participant": {
                "description": "添加会议参与者",
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "meeting_id": {"type": "string", "description": "会议ID"},
                        "role_id": {"type": "string", "description": "角色ID"}
                    },
                    "required": ["meeting_id", "role_id"]
                }
            },
            "remove_meeting_participant": {
                "description": "删除会议参与者",
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "meeting_id": {"type": "string", "description": "会议ID"},
                        "role_id": {"type": "string", "description": "角色ID"}
                    },
                    "required": ["meeting_id", "role_id"]
                }
            },
            "get_meeting_status": {
                "description": "获取会议状态",
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "meeting_id": {"type": "string", "description": "会议ID"}
                    },
                    "required": ["meeting_id"]
                }
            },
            "update_meeting_rounds": {
                "description": "更新会议轮次",
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "meeting_id": {"type": "string", "description": "会议ID"},
                        "rounds": {"type": "integer", "description": "发言轮次数"}
                    },
                    "required": ["meeting_id", "rounds"]
                }
            },
            "start_meeting": {
                "description": "启动会议（开始圆桌讨论）",
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "meeting_id": {"type": "string", "description": "会议ID"}
                    },
                    "required": ["meeting_id"]
                }
            }
        }

    def handle_request(self, method: str, params: dict = None):
        """处理请求"""
        if params is None:
            params = {}

        if method == "initialize":
            return {
                "protocolVersion": "2024-11-05",
                "capabilities": {"tools": {}},
                "serverInfo": {
                    "name": "roundtable",
                    "version": "1.0"
                }
            }

        elif method == "tools/list":
            tools = []
            for name, spec in self.tools.items():
                tools.append({
                    "name": name,
                    "description": spec["description"],
                    "inputSchema": spec["input_schema"]
                })
            return {"tools": tools}

        elif method == "tools/call":
            tool_name = params.get("name")
            arguments = params.get("arguments", {})

            if tool_name == "list_roles":
                roles = role_manager.list_roles()
                return {"content": [{"type": "text", "text": json.dumps(roles, ensure_ascii=False)}]}

            elif tool_name == "get_role_identity":
                role_id = arguments.get("role_id")
                identity = role_manager.get_role_identity(role_id)
                return {"content": [{"type": "text", "text": identity or "角色不存在"}]}

            elif tool_name == "create_role":
                name = arguments.get("name")
                description = arguments.get("description", "")
                notes = arguments.get("notes", "")
                result = role_manager.create_role(name, description, notes)
                return {"content": [{"type": "text", "text": "创建成功" if result else "创建失败"}]}

            elif tool_name == "delete_role":
                role_id = arguments.get("role_id")
                result = role_manager.delete_role(role_id)
                return {"content": [{"type": "text", "text": "删除成功" if result else "删除失败"}]}

            elif tool_name == "list_meetings":
                meetings = meeting_manager.list_meetings()
                result = [{"meeting_id": m.meeting_id, "topic": m.topic, "status": m.status} for m in meetings]
                return {"content": [{"type": "text", "text": json.dumps(result, ensure_ascii=False)}]}

            elif tool_name == "create_meeting":
                topic = arguments.get("topic")
                role_ids = arguments.get("role_ids", [])
                rounds = arguments.get("rounds", 3)
                meeting = meeting_manager.create_meeting(topic, role_ids, rounds)
                if meeting:
                    return {"content": [{"type": "text", "text": f"会议创建成功，ID: {meeting.meeting_id}"}]}
                return {"content": [{"type": "text", "text": "会议创建失败"}]}

            elif tool_name == "get_meeting":
                meeting_id = arguments.get("meeting_id")
                meeting = meeting_manager.get_meeting(meeting_id)
                if meeting:
                    result = {
                        "meeting_id": meeting.meeting_id,
                        "topic": meeting.topic,
                        "roles": meeting.role_names,
                        "rounds": meeting.rounds,
                        "status": meeting.status
                    }
                    return {"content": [{"type": "text", "text": json.dumps(result, ensure_ascii=False)}]}
                return {"content": [{"type": "text", "text": "会议不存在"}]}

            elif tool_name == "get_meeting_minutes":
                meeting_id = arguments.get("meeting_id")
                minutes = meeting_manager.view_meeting_minutes(meeting_id)
                return {"content": [{"type": "text", "text": minutes or "会议纪要不存在"}]}

            elif tool_name == "delete_meeting":
                meeting_id = arguments.get("meeting_id")
                result = meeting_manager.delete_meeting(meeting_id)
                return {"content": [{"type": "text", "text": "删除成功" if result else "删除失败"}]}

            elif tool_name == "update_meeting_topic":
                meeting_id = arguments.get("meeting_id")
                topic = arguments.get("topic")
                result = meeting_manager.update_meeting_topic(meeting_id, topic)
                return {"content": [{"type": "text", "text": "更新成功" if result else "更新失败"}]}

            elif tool_name == "add_meeting_participant":
                meeting_id = arguments.get("meeting_id")
                role_id = arguments.get("role_id")
                result = meeting_manager.add_meeting_participant(meeting_id, role_id)
                return {"content": [{"type": "text", "text": "添加成功" if result else "添加失败"}]}

            elif tool_name == "remove_meeting_participant":
                meeting_id = arguments.get("meeting_id")
                role_id = arguments.get("role_id")
                result = meeting_manager.remove_meeting_participant(meeting_id, role_id)
                return {"content": [{"type": "text", "text": "删除成功" if result else "删除失败"}]}

            elif tool_name == "get_meeting_status":
                meeting_id = arguments.get("meeting_id")
                status = meeting_manager.get_meeting_status(meeting_id)
                return {"content": [{"type": "text", "text": json.dumps(status, ensure_ascii=False)}]}

            elif tool_name == "update_meeting_rounds":
                meeting_id = arguments.get("meeting_id")
                rounds = arguments.get("rounds")
                result = meeting_manager.update_meeting_rounds(meeting_id, rounds)
                return {"content": [{"type": "text", "text": "更新成功" if result else "更新失败"}]}

            elif tool_name == "start_meeting":
                meeting_id = arguments.get("meeting_id")
                # 检查会议状态
                meeting = meeting_manager.get_meeting(meeting_id)
                if not meeting:
                    return {"content": [{"type": "text", "text": "会议不存在"}]}
                if meeting.status == "completed":
                    return {"content": [{"type": "text", "text": "会议已结束，如需继续讨论请使用continue_discussion"}]}
                if meeting.status == "running":
                    return {"content": [{"type": "text", "text": "会议正在进行中"}]}
                # 启动会议（静默模式，不输出日志）
                result = meeting_manager.run_meeting(meeting_id, silent=True)
                return {"content": [{"type": "text", "text": "会议完成" if result else "会议启动失败"}]}

            else:
                return {"error": {"code": -32601, "message": f"Unknown tool: {tool_name}"}}

        return {"error": {"code": -32600, "message": "Invalid request"}}


def main():
    """主函数"""
    server = MCPServer()

    while True:
        try:
            line = sys.stdin.readline()
            if not line:
                break

            request = json.loads(line)
            method = request.get("method")
            params = request.get("params")
            id_val = request.get("id")

            result = server.handle_request(method, params)

            response = {
                "jsonrpc": "2.0",
                "id": id_val
            }

            if "error" in result:
                response["error"] = result["error"]
            else:
                response["result"] = result

            print(json.dumps(response), flush=True)

        except Exception as e:
            error_response = {
                "jsonrpc": "2.0",
                "id": None,
                "error": {"code": -32603, "message": str(e)}
            }
            print(json.dumps(error_response), flush=True)


if __name__ == "__main__":
    main()
