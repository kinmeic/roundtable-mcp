"""
LLM客户端 - 负责调用MiniMax API并支持MCP工具调用
"""

import json
import subprocess
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional

import config_manager

BASE_DIR = Path(__file__).parent


class MCPClient:
    """MCP客户端 - 通过stdio与MCP服务器通信"""

    def __init__(self, server_config: dict):
        """
        初始化MCP客户端

        Args:
            server_config: MCP服务器配置
        """
        self.command = server_config.get("command", "")
        self.args = server_config.get("args", [])
        self.env = server_config.get("env", {})
        self.process = None
        self._initialized = False

    def start(self):
        """启动MCP服务器进程并初始化"""
        import os
        full_env = os.environ.copy()
        full_env.update(self.env)

        self.process = subprocess.Popen(
            [self.command] + self.args,
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            env=full_env,
            text=True,
            bufsize=1
        )

        # 初始化连接
        self._initialize()

    def _send_request(self, method: str, params: Optional[Dict] = None) -> Dict:
        """发送JSON-RPC请求"""
        request = {
            "jsonrpc": "2.0",
            "id": 1,
            "method": method,
        }
        if params:
            request["params"] = params

        self.process.stdin.write(json.dumps(request) + "\n")
        self.process.stdin.flush()

        # 读取响应
        response_line = self.process.stdout.readline()
        return json.loads(response_line)

    def _initialize(self):
        """初始化MCP连接"""
        try:
            # 发送initialize请求
            init_params = {
                "protocolVersion": "2024-11-05",
                "capabilities": {},
                "clientInfo": {
                    "name": "roundtable",
                    "version": "1.0"
                }
            }
            response = self._send_request("initialize", init_params)

            if "result" in response:
                self._initialized = True
                # 发送initialized通知
                self.process.stdin.write(json.dumps({"jsonrpc": "2.0", "method": "initialized"}) + "\n")
                self.process.stdin.flush()

        except Exception as e:
            print(f"MCP初始化错误: {e}")

    def list_tools(self) -> List[Dict]:
        """列出可用工具"""
        if not self.process or self.process.poll() is not None:
            self.start()

        try:
            response = self._send_request("tools/list")
            if "result" in response:
                return response["result"].get("tools", [])
        except Exception as e:
            print(f"列出工具错误: {e}")

        return []

    def call_tool(self, tool_name: str, arguments: Dict) -> str:
        """
        调用MCP工具

        Args:
            tool_name: 工具名称
            arguments: 工具参数

        Returns:
            工具执行结果
        """
        if not self.process or self.process.poll() is not None:
            self.start()

        if not self._initialized:
            self._initialize()

        try:
            # 构建JSON-RPC请求
            request = {
                "jsonrpc": "2.0",
                "id": 2,
                "method": "tools/call",
                "params": {
                    "name": tool_name,
                    "arguments": arguments
                }
            }

            # 发送请求
            self.process.stdin.write(json.dumps(request) + "\n")
            self.process.stdin.flush()

            # 读取响应
            response_line = self.process.stdout.readline()
            response = json.loads(response_line)

            if "result" in response:
                # 处理结果
                result = response["result"]
                if isinstance(result, dict):
                    if "content" in result:
                        # 返回content数组中的文本
                        contents = result["content"]
                        text_parts = []
                        for item in contents:
                            if item.get("type") == "text":
                                text_parts.append(item.get("text", ""))
                        return "\n".join(text_parts)
                return json.dumps(result, ensure_ascii=False)
            elif "error" in response:
                return json.dumps(response["error"], ensure_ascii=False)

        except Exception as e:
            return f"Tool execution error: {str(e)}"

        return "No response from MCP server"

    def stop(self):
        """停止MCP服务器进程"""
        if self.process:
            self.process.terminate()
            self.process.wait()


class LLMClient:
    """LLM客户端"""

    def __init__(self, model: Optional[str] = None, base_url: Optional[str] = None, api_key: Optional[str] = None):
        """
        初始化LLM客户端

        Args:
            model: 模型名称，默认从配置读取
            base_url: API基础URL，默认从配置读取
            api_key: API密钥，默认从配置读取
        """
        self.model = model or config_manager.get_model()
        self.base_url = base_url or config_manager.get_base_url()
        self.api_key = api_key or config_manager.get_api_key()
        self.mcp_servers = config_manager.get_mcp_servers()
        self.mcp_client = None

        # 初始化MCP客户端
        if self.mcp_servers:
            # 使用第一个MCP服务器
            for server_name, server_config in self.mcp_servers.items():
                self.mcp_client = MCPClient(server_config)
                break

    def call(
        self,
        system_message: str,
        user_message: str,
        tools: Optional[List[Dict]] = None,
        max_tokens: int = 4096,
        temperature: float = 0.7
    ) -> Dict[str, Any]:
        """
        调用LLM API

        Args:
            system_message: 系统消息
            user_message: 用户消息
            tools: 工具定义列表
            max_tokens: 最大token数
            temperature: 温度参数

        Returns:
            包含响应文本和工具调用的字典
        """
        import anthropic

        client = anthropic.Anthropic(
            base_url=self.base_url,
            api_key=self.api_key
        )

        messages = [{"role": "user", "content": user_message}]

        # 准备工具
        tool_definitions = None
        if tools:
            tool_definitions = tools

        # 第一次调用
        response = client.messages.create(
            model=self.model,
            max_tokens=max_tokens,
            system=system_message,
            messages=messages,
            tools=tool_definitions,
            temperature=temperature
        )

        # 处理工具调用
        while response.stop_reason == "tool_use":
            tool_results = []

            for block in response.content:
                if block.type == "tool_use":
                    tool_name = block.name
                    tool_input = block.input
                    tool_id = block.id

                    # 执行工具
                    result = self._execute_tool(tool_name, tool_input)

                    tool_results.append({
                        "type": "tool_result",
                        "tool_use_id": tool_id,
                        "content": result
                    })

            # 将工具结果添加到消息中
            messages.append({"role": "assistant", "content": response.content})
            messages.append({"role": "user", "content": tool_results})

            # 继续调用
            response = client.messages.create(
                model=self.model,
                max_tokens=max_tokens,
                system=system_message,
                messages=messages,
                tools=tool_definitions,
                temperature=temperature
            )

        # 提取文本内容
        text_content = ""
        for block in response.content:
            if block.type == "text":
                text_content += block.text

        return {
            "text": text_content,
            "stop_reason": response.stop_reason,
            "usage": {
                "input_tokens": response.usage.input_tokens,
                "output_tokens": response.usage.output_tokens
            }
        }

    def call_stream(
        self,
        system_message: str,
        user_message: str,
        tools: Optional[List[Dict]] = None,
        max_tokens: int = 4096,
        temperature: float = 0.7,
        callback: Optional[Callable] = None
    ) -> Dict[str, Any]:
        """
        流式调用LLM API

        Args:
            system_message: 系统消息
            user_message: 用户消息
            tools: 工具定义列表
            max_tokens: 最大token数
            temperature: 温度参数
            callback: 流式输出回调函数，接收文本片段

        Returns:
            包含响应文本和工具调用的字典
        """
        import anthropic

        # 如果没有回调函数，直接使用非流式调用
        if not callback:
            return self.call(system_message, user_message, tools, max_tokens, temperature)

        # 有工具时不支持流式，降级为非流式
        if tools:
            response = self.call(system_message, user_message, tools, max_tokens, temperature)
            # 模拟流式输出
            text = response.get("text", "")
            for char in text:
                callback(char)
            return response

        client = anthropic.Anthropic(
            base_url=self.base_url,
            api_key=self.api_key
        )

        messages = [{"role": "user", "content": user_message}]

        try:
            # 使用text()方法获取完整的文本
            response = client.messages.create(
                model=self.model,
                max_tokens=max_tokens,
                system=system_message,
                messages=messages,
                temperature=temperature
            )

            # 提取文本内容
            text_content = ""
            for block in response.content:
                if block.type == "text":
                    # 模拟流式输出
                    for char in block.text:
                        callback(char)
                        text_content += char

            return {
                "text": text_content,
                "stop_reason": response.stop_reason,
                "usage": {
                    "input_tokens": response.usage.input_tokens,
                    "output_tokens": response.usage.output_tokens
                }
            }
        except Exception as e:
            # 如果出错，返回空结果
            return {
                "text": "",
                "stop_reason": "error",
                "usage": {}
            }

    def _execute_tool(self, tool_name: str, tool_input: Dict) -> str:
        """
        执行工具调用

        Args:
            tool_name: 工具名称
            tool_input: 工具输入参数

        Returns:
            工具执行结果
        """
        # 使用MCP客户端执行工具
        if self.mcp_client:
            try:
                return self.mcp_client.call_tool(tool_name, tool_input)
            except Exception as e:
                return f"Tool execution error: {str(e)}"

        # 如果没有MCP客户端，返回错误
        return f"Tool '{tool_name}' not available - no MCP server configured"


def create_client() -> LLMClient:
    """创建默认LLM客户端"""
    return LLMClient()


def get_default_tools() -> List[Dict]:
    """
    获取默认工具列表

    Returns:
        工具定义列表
    """
    return [
        {
            "name": "web_search",
            "description": "Search the web for current information, news, and facts. Use this when you need up-to-date information.",
            "input_schema": {
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "The search query"
                    }
                },
                "required": ["query"]
            }
        }
    ]
