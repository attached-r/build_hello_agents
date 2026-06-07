"""
MCP 协议工具 — 将 MCP 客户端封装为同步 Tool，供 Agent 调用。

MCPTool 实现了 Tool 抽象基类，使用 **专用线程 + 独立事件循环** 模式
桥接异步 MCPClient 与同步 Tool.run() 接口，兼容 Jupyter / FastAPI
等已有事件循环的运行环境。

用法:
    # 方式 1: 预置连接参数（自动连接）
    mcp_tool = MCPTool(connection=["python", "my_server.py"])
    mcp_tool.run({"action": "call_tool", "tool_name": "add", "arguments": {"a": 1, "b": 2}})

    # 方式 2: 传入已连接的 MCPClient
    from hello_agents.protocols import MCPClient
    import asyncio
    client = asyncio.run(MCPClient(server).connect())
    mcp_tool = MCPTool(client=client)

    # 方式 3: 在 run 中惰性连接
    mcp_tool = MCPTool()
    mcp_tool.run({"action": "connect", "server": ["python", "my_server.py"]})
    mcp_tool.run({"action": "list_tools"})

与智能体集成:
    from hello_agents import ReActAgent
    from hello_agents.tools import MCPTool

    agent = ReActAgent(name="助手", llm=llm)
    agent.add_tool(MCPTool(connection=["python", "db_server.py"]))
"""

from __future__ import annotations       

import asyncio
import threading
from typing import Any, Dict, List, Optional, Union

from ...tools.base import Tool, ToolParameter
from ...protocols.mcp.client import MCPClient


class MCPTool(Tool):
    """MCP 协议工具 — Agent 通过它与 MCP 服务器交互。

    将异步的 MCPClient 封装为同步 Tool，支持工具发现、工具调用、
    资源读取和提示模板获取等操作。

    Attributes:
        name: "mcp"
        description: 工具描述（含支持的操作列表）
    """

    def __init__(
        self,
        client: Optional[MCPClient] = None,
        connection: Optional[Union[str, List[str]]] = None,
    ):
        """初始化 MCPTool。

        Args:
            client: 已连接的 MCPClient 实例（复用现有连接）
            connection: MCP 服务器连接参数
                - List[str]: stdio 命令列表（如 ["npx", "-y", "package", "."]）
                - str: URL 或脚本路径（如 "http://localhost:8000/mcp"）
        """
        super().__init__(
            name="mcp",
            description=(
                "MCP (Model Context Protocol) 工具，用于连接 MCP 服务器 "
                "并调用远程工具 / 读取资源 / 获取提示模板。\n\n"
                "支持的操作:\n"
                "  · connect       — 连接到 MCP 服务器\n"
                "  · list_tools    — 列出所有可用工具\n"
                "  · call_tool     — 调用指定工具\n"
                "  · list_resources — 列出所有可用资源\n"
                "  · read_resource — 读取指定资源\n"
                "  · list_prompts  — 列出所有提示模板\n"
                "  · get_prompt    — 获取指定提示模板\n"
                "  · disconnect    — 断开连接"
            ),
        )
        self._client = client
        self._connection_params = connection

        # 异步事件循环（专用线程）
        self._loop: Optional[asyncio.AbstractEventLoop] = None
        self._loop_thread: Optional[threading.Thread] = None

    # ══════════════════════════════════════════════════════════════════
    # Async-Sync 桥接
    # ══════════════════════════════════════════════════════════════════

    def _ensure_event_loop(self) -> asyncio.AbstractEventLoop:
        """确保存在一个独立运行的专用事件循环。

        在 daemon 线程中运行事件循环，支持:
          - 在当前线程无事件循环时自动创建
          - 兼容已有事件循环的环境（Jupyter、FastAPI 等）
          - 多次调用复用同一循环

        Returns:
            运行中的事件循环
        """
        if self._loop is not None and self._loop.is_running():
            return self._loop

        # 创建新的事件循环并在线程中运行
        self._loop = asyncio.new_event_loop()

        def _run_loop(loop: asyncio.AbstractEventLoop) -> None:
            asyncio.set_event_loop(loop)
            loop.run_forever()

        self._loop_thread = threading.Thread(
            target=_run_loop,
            args=(self._loop,),
            daemon=True,
            name="mcp-tool-event-loop",
        )
        self._loop_thread.start()
        return self._loop

    def _run_async(self, coro: Any) -> Any:
        """在专用事件循环中执行异步协程，同步等待结果。

        Args:
            coro: 要执行的协程（awaitable）

        Returns:
            协程的执行结果

        Raises:
            协程执行过程中的任何异常
        """
        loop = self._ensure_event_loop()
        future = asyncio.run_coroutine_threadsafe(coro, loop)
        # 设置超时防止永久阻塞（大多数 MCP 操作应在 60s 内完成）
        return future.result(timeout=60)

    def _ensure_client(self) -> None:
        """确保已连接到 MCP 服务器。

        当 client 未连接时，尝试用 connection_params 自动连接。

        Raises:
            RuntimeError: 未指定 client 且未提供 connection_params
        """
        if self._client is not None and self._client.connected:
            return

        if self._connection_params is not None:
            self._client = MCPClient(self._connection_params)
            self._run_async(self._client.connect())
        else:
            raise RuntimeError(
                "MCPTool 未连接。请通过以下方式之一连接:\n"
                "  1. 构造时传入 connection= 参数\n"
                "  2. 构造时传入已连接的 client=\n"
                "  3. 调用 run({'action': 'connect', 'server': ...})"
            )

    # ══════════════════════════════════════════════════════════════════
    # Tool 接口实现
    # ══════════════════════════════════════════════════════════════════

    def run(self, parameters: Dict[str, Any]) -> str:
        """统一入口 — 根据 action 分发到具体操作。

        Args:
            parameters: 参数字典，必须含 "action" 键
                - action: 操作类型（connect/list_tools/call_tool/...）
                - 其他参数因操作而异

        Returns:
            操作结果的格式化字符串

        Raises:
            ValueError: action 参数缺失或未知
        """
        action = parameters.get("action", "")
        if not action:
            return "❌ 参数 'action' 不能为空。支持的操作: connect/list_tools/call_tool/list_resources/read_resource/list_prompts/get_prompt/disconnect"

        handler = getattr(self, f"_{action}", None)
        if handler is None:
            return (
                f"❌ 未知操作: '{action}'。\n"
                f"支持的操作: connect/list_tools/call_tool/"
                f"list_resources/read_resource/list_prompts/get_prompt/disconnect"
            )

        try:
            result = handler(**parameters)
            return result
        except Exception as e:
            return f"❌ 操作 '{action}' 执行失败: {e}"

    def get_parameters(self) -> List[ToolParameter]:
        """获取 MCPTool 的参数 Schema 定义。"""
        return [
            ToolParameter(
                name="action", type="string",
                description=(
                    "操作类型: connect / list_tools / call_tool / "
                    "list_resources / read_resource / list_prompts / "
                    "get_prompt / disconnect"
                ),
            ),
            ToolParameter(
                name="server", type="string",
                description=(
                    "MCP 服务器连接参数（connect 操作需要）。"
                    "命令列表格式如 [\"npx\", \"-y\", \"package\"]，"
                    "或 URL 如 \"http://localhost:8000/mcp\""
                ),
                required=False,
            ),
            ToolParameter(
                name="tool_name", type="string",
                description="要调用的 MCP 工具名称（call_tool 操作需要）",
                required=False,
            ),
            ToolParameter(
                name="arguments", type="object",
                description="工具调用参数（call_tool / get_prompt 操作需要），JSON 对象格式",
                required=False,
            ),
            ToolParameter(
                name="uri", type="string",
                description="资源 URI（read_resource 操作需要）",
                required=False,
            ),
            ToolParameter(
                name="name", type="string",
                description="提示模板名称（get_prompt 操作需要）",
                required=False,
            ),
        ]

    # ══════════════════════════════════════════════════════════════════
    # 连接管理
    # ══════════════════════════════════════════════════════════════════

    def _connect(self, **params: Any) -> str:
        """连接到 MCP 服务器。

        参数 (取自 params):
            server: 连接参数，同 MCPClient.__init__ 的 server 参数
        """
        server = params.get("server", self._connection_params)
        if server is None:
            return "❌ 未指定 server 参数。请传入命令列表、URL 或 FastMCP 实例。"

        self._connection_params = server
        self._client = MCPClient(server)
        self._run_async(self._client.connect())
        return "✅ MCP 客户端已成功连接到服务器"

    def _disconnect(self, **params: Any) -> str:
        """断开 MCP 连接。"""
        if self._client is None:
            return "⚠️ MCP 客户端尚未连接，无需断开"

        self._run_async(self._client.disconnect())
        self._client = None
        return "✅ MCP 客户端已断开连接"

    # ══════════════════════════════════════════════════════════════════
    # 工具操作
    # ══════════════════════════════════════════════════════════════════

    def _list_tools(self, **params: Any) -> str:
        """列出 MCP 服务器提供的所有工具。"""
        self._ensure_client()
        tools = self._run_async(self._client.list_tools())

        if not tools:
            return "💡 MCP 服务器未提供任何工具"

        lines: List[str] = []
        lines.append(f"🔧 MCP 工具列表（共 {len(tools)} 个）:\n")
        for i, t in enumerate(tools, 1):
            name = getattr(t, "name", "?")
            desc = getattr(t, "description", "") or "无描述"
            lines.append(f"  [{i}] {name}: {desc[:120]}")

            # 显示参数概要
            schema = getattr(t, "inputSchema", None) or getattr(t, "parameters", None)
            if schema and isinstance(schema, dict):
                props = schema.get("properties", {})
                if props:
                    param_names = ", ".join(props.keys())
                    lines.append(f"      参数: {param_names}")
        return "\n".join(lines)

    def _call_tool(self, **params: Any) -> str:
        """调用 MCP 服务器上的工具。

        参数 (取自 params):
            tool_name: 工具名称（必需）
            arguments: 工具参数字典（可选，默认 {})
        """
        self._ensure_client()

        tool_name = params.get("tool_name", "")
        if not tool_name:
            return "❌ 参数 'tool_name' 不能为空"

        arguments = params.get("arguments", {})
        result = self._run_async(self._client.call_tool(tool_name, arguments))
        return self._format_tool_result(tool_name, result)

    # ══════════════════════════════════════════════════════════════════
    # 资源操作
    # ══════════════════════════════════════════════════════════════════

    def _list_resources(self, **params: Any) -> str:
        """列出 MCP 服务器提供的所有资源。"""
        self._ensure_client()
        resources = self._run_async(self._client.list_resources())

        if not resources:
            return "💡 MCP 服务器未提供任何资源"

        lines: List[str] = []
        lines.append(f"📦 MCP 资源列表（共 {len(resources)} 个）:\n")
        for i, r in enumerate(resources, 1):
            name = getattr(r, "name", "?")
            uri = getattr(r, "uri", "?")
            desc = getattr(r, "description", "") or "无描述"
            lines.append(f"  [{i}] {name}: {desc[:120]}")
            lines.append(f"      URI: {uri}")
        return "\n".join(lines)

    def _read_resource(self, **params: Any) -> str:
        """读取 MCP 资源。

        参数 (取自 params):
            uri: 资源 URI（必需）
        """
        self._ensure_client()

        uri = params.get("uri", "")
        if not uri:
            return "❌ 参数 'uri' 不能为空"

        result = self._run_async(self._client.read_resource(uri))
        return self._format_resource_result(uri, result)

    # ══════════════════════════════════════════════════════════════════
    # 提示模板操作
    # ══════════════════════════════════════════════════════════════════

    def _list_prompts(self, **params: Any) -> str:
        """列出 MCP 服务器提供的所有提示模板。"""
        self._ensure_client()
        prompts = self._run_async(self._client.list_prompts())

        if not prompts:
            return "💡 MCP 服务器未提供任何提示模板"

        lines: List[str] = []
        lines.append(f"📝 MCP 提示模板列表（共 {len(prompts)} 个）:\n")
        for i, p in enumerate(prompts, 1):
            name = getattr(p, "name", "?")
            desc = getattr(p, "description", "") or "无描述"
            lines.append(f"  [{i}] {name}: {desc[:120]}")
        return "\n".join(lines)

    def _get_prompt(self, **params: Any) -> str:
        """获取指定提示模板的内容。

        参数 (取自 params):
            name: 提示模板名称（必需）
            arguments: 模板参数（可选）
        """
        self._ensure_client()

        name = params.get("name", "")
        if not name:
            return "❌ 参数 'name' 不能为空"

        arguments = params.get("arguments", {})
        result = self._run_async(self._client.get_prompt(name, arguments))

        lines: List[str] = []
        lines.append(f"📝 提示模板 '{name}':\n")

        messages = getattr(result, "messages", [])
        if messages:
            for msg in messages:
                role = getattr(msg, "role", "unknown")
                content = getattr(msg, "content", "")
                text = str(content)[:500] if content else ""
                lines.append(f"  [{role}]: {text}")
        else:
            lines.append(f"  {str(result)[:500]}")

        return "\n".join(lines)

    # ══════════════════════════════════════════════════════════════════
    # 格式化工具
    # ══════════════════════════════════════════════════════════════════

    @staticmethod
    def _format_tool_result(tool_name: str, result: Any) -> str:
        """将工具调用结果格式化为可读字符串。

        Args:
            tool_name: 工具名称
            result: MCP 工具调用结果（CallToolResult）

        Returns:
            格式化后的结果字符串
        """
        lines: List[str] = []
        lines.append(f"🔧 MCP 工具 '{tool_name}' 执行结果:\n")

        content = getattr(result, "content", [])
        if content:
            for item in content:
                text = getattr(item, "text", str(item))
                if text:
                    lines.append(text)
        else:
            lines.append(str(result))

        # 检查是否包含错误
        is_error = getattr(result, "isError", False)
        if is_error:
            lines.append("\n⚠️ 工具调用返回错误状态")

        return "\n".join(lines)

    @staticmethod
    def _format_resource_result(uri: str, result: Any) -> str:
        """将资源读取结果格式化为可读字符串。

        Args:
            uri: 资源 URI
            result: 资源读取结果（ReadResourceResult）

        Returns:
            格式化后的结果字符串
        """
        lines: List[str] = []
        lines.append(f"📦 MCP 资源 '{uri}' 内容:\n")

        content = getattr(result, "content", [])
        if content:
            for item in content:
                text = getattr(item, "text", str(item))
                if text:
                    lines.append(text)
        else:
            lines.append(str(result))

        return "\n".join(lines)


# ══════════════════════════════════════════════════════════════════════
# A2ATool — 调用远程 A2A Agent 的工具
# ══════════════════════════════════════════════════════════════════════

class A2ATool(Tool):
    """A2A 通信工具 — Agent 通过它与远程 A2A Agent 交互。

    将异步的 A2A 客户端封装为同步 Tool，支持发送消息、
    查询 Agent Card 和列出技能等操作。

    用法:
        tool = A2ATool(default_url="http://localhost:9998")
        tool.run({"action": "send_message", "message": "你好"})
        tool.run({"action": "get_agent_card"})

    与智能体集成:
        from hello_agents import ReActAgent
        from hello_agents.tools import A2ATool

        agent = ReActAgent(name="助手", llm=llm)
        agent.add_tool(A2ATool(default_url="http://localhost:9999"))
    """

    def __init__(self, default_url: Optional[str] = None, name: str = "a2a"):
        """初始化 A2ATool。

        Args:
            default_url: 远程 A2A Agent 的默认 URL（可选，调用时可覆盖）
            name: 工具名称（默认 "a2a"）
        """
        super().__init__(
            name=name,
            description=(
                "A2A (Agent-to-Agent) 通信工具，与远程 AI Agent 交互。\n\n"
                "支持的操作:\n"
                "  · send_message   — 向远程 Agent 发送消息并获取回复\n"
                "  · get_agent_card — 获取远程 Agent 的元信息卡片\n"
                "  · list_skills    — 列出远程 Agent 支持的能力"
            ),
        )
        self._default_url = default_url

        # 异步事件循环（专用线程）
        self._loop: Optional[asyncio.AbstractEventLoop] = None
        self._loop_thread: Optional[threading.Thread] = None

    # ── Async-Sync 桥接 ──────────────────────────────────────────

    def _ensure_loop(self) -> asyncio.AbstractEventLoop:
        """确保存在一个独立运行的专用事件循环。

        使用 daemon 线程 + 独立事件循环，兼容 Jupyter / FastAPI
        等已有事件循环的运行环境。
        """
        if self._loop and self._loop.is_running():
            return self._loop

        self._loop = asyncio.new_event_loop()
        self._loop_thread = threading.Thread(
            target=lambda: (asyncio.set_event_loop(self._loop), self._loop.run_forever()),
            daemon=True,
            name="a2a-tool-event-loop",
        )
        self._loop_thread.start()
        return self._loop

    def _run_async(self, coro: Any, timeout: float = 60) -> Any:
        """在专用事件循环中执行异步协程，同步等待结果。

        Args:
            coro: 要执行的协程
            timeout: 超时秒数（默认 60）

        Returns:
            协程的执行结果
        """
        loop = self._ensure_loop()
        return asyncio.run_coroutine_threadsafe(coro, loop).result(timeout=timeout)

    # ── 工具接口 ────────────────────────────────────────────────

    def run(self, parameters: Dict[str, Any]) -> str:
        """统一入口 — 根据 action 分发到具体操作。

        Args:
            parameters: 参数字典
                - action: 操作类型（send_message / get_agent_card / list_skills）
                - url: 目标 Agent URL（可选，覆盖默认 URL）
                - message: 消息内容（send_message 需要）

        Returns:
            操作结果的格式化字符串
        """
        action = parameters.get("action", "")
        if not action:
            return "❌ 参数 'action' 不能为空。支持的操作: send_message / get_agent_card / list_skills"

        handler = getattr(self, f"_{action}", None)
        if handler is None:
            return f"❌ 未知操作 '{action}'，支持: send_message / get_agent_card / list_skills"

        try:
            return handler(**parameters)
        except ImportError as e:
            return f"❌ 缺少依赖: {e}，请安装: pip install a2a-sdk httpx"
        except Exception as e:
            return f"❌ {action} 失败: {e}"

    def get_parameters(self) -> List[ToolParameter]:
        return [
            ToolParameter(name="action", type="string", description="操作: send_message / get_agent_card / list_skills"),
            ToolParameter(name="url", type="string", description="目标 Agent URL（可选，使用默认 URL）", required=False),
            ToolParameter(name="message", type="string", description="消息内容（send_message 需要）", required=False),
        ]

    # ── 辅助方法 ────────────────────────────────────────────────

    def _get_url(self, params: Dict[str, Any]) -> str:
        url = params.get("url", self._default_url)
        if not url:
            raise ValueError("需要 url 参数，请在构造时传入 default_url 或调用时传入 url")
        return url

    # ── 操作实现 ────────────────────────────────────────────────

    def _send_message(self, **kw: Any) -> str:
        """发送消息给远程 A2A Agent 并获取回复。"""
        import httpx
        from a2a.client import A2AClient
        from a2a.types import MessageData, Part, TaskInput, TaskSendParams

        url = self._get_url(kw)
        text = kw.get("message", "")
        if not text:
            return "❌ message 不能为空"

        async def _exec():
            async with httpx.AsyncClient() as c:
                client = await A2AClient.get_client_from_agent_card_url(c, url)
                req = TaskSendParams(
                    input=TaskInput(
                        message=MessageData(role="user", parts=[Part(type="text", text=text)])
                    )
                )
                resp = await client.send_message(req)
                parts = []
                if hasattr(resp, "result") and resp.result:
                    msg = getattr(resp.result, "message", None)
                    if msg and hasattr(msg, "content"):
                        for p in msg.content:
                            if hasattr(p, "text") and p.text:
                                parts.append(p.text)
                return "\n".join(parts) if parts else str(resp)

        return self._run_async(_exec())

    def _get_agent_card(self, **kw: Any) -> str:
        """获取远程 Agent 的元信息卡片。"""
        import httpx
        url = self._get_url(kw)

        async def _exec():
            async with httpx.AsyncClient() as c:
                r = await c.get(f"{url.rstrip('/')}/.well-known/agent.json")
                card = r.json()
                lines = ["📇 Agent Card:\n"]
                for k in ("name", "description", "version", "url"):
                    if k in card:
                        lines.append(f"  {k}: {card[k]}")
                skills = card.get("skills", [])
                if skills:
                    lines.append(f"\n  技能 ({len(skills)}):")
                    for s in skills:
                        lines.append(f"    · {s.get('name', '?')}: {s.get('description', '')[:60]}")
                return "\n".join(lines)

        return self._run_async(_exec())

    def _list_skills(self, **kw: Any) -> str:
        """列出远程 Agent 的技能（通过 Agent Card）。"""
        card_out = self._get_agent_card(**kw)
        if "技能" not in card_out:
            return card_out
        return card_out[card_out.index("技能"):]


# ══════════════════════════════════════════════════════════════════════
# 便捷工厂函数
# ══════════════════════════════════════════════════════════════════════

def create_mcp_tool(
    connection: Optional[Union[str, List[str]]] = None,
) -> MCPTool:
    """创建 MCPTool 实例的便捷函数。

    Args:
        connection: MCP 服务器连接参数
            - List[str]: stdio 命令列表
            - str: URL 或脚本路径

    Returns:
        MCPTool 实例
    """
    return MCPTool(connection=connection)


def create_a2a_tool(
    default_url: Optional[str] = None,
) -> A2ATool:
    """创建 A2ATool 实例的便捷函数。

    Args:
        default_url: 远程 A2A Agent 的默认 URL

    Returns:
        A2ATool 实例
    """
    return A2ATool(default_url=default_url)


# ══════════════════════════════════════════════════════════════════════
# 自测 / 演示
# ══════════════════════════════════════════════════════════════════════

if __name__ == "__main__":
    print("=" * 60)
    print("MCPTool 自测（内存模式）")
    print("=" * 60)

    from hello_agents.protocols.mcp.client import MCPClient as _MCPClient
    from fastmcp import FastMCP

    # 1. 创建内存 MCP 服务器
    _server = FastMCP("DemoServer")

    @_server.tool()
    def add(a: int, b: int) -> int:
        """将两个数相加"""
        return a + b

    @_server.tool()
    def greet(name: str) -> str:
        """向指定姓名打招呼"""
        return f"你好, {name}!"

    # 2. 用 MCPTool 包装
    import asyncio

    _client = _MCPClient(_server)
    asyncio.run(_client.connect())
    tool = MCPTool(client=_client)

    # 3. 测试 list_tools
    print("\n--- list_tools ---")
    result = tool.run({"action": "list_tools"})
    print(result)

    # 4. 测试 call_tool
    print("\n--- call_tool: add ---")
    result = tool.run({
        "action": "call_tool",
        "tool_name": "add",
        "arguments": {"a": 10, "b": 20},
    })
    print(result)

    print("\n--- call_tool: greet ---")
    result = tool.run({
        "action": "call_tool",
        "tool_name": "greet",
        "arguments": {"name": "MCP"},
    })
    print(result)

    # 5. 断开连接
    print("\n--- disconnect ---")
    result = tool.run({"action": "disconnect"})
    print(result)

    print("\n" + "=" * 60)
    print("自测完成 ✅")
    print("=" * 60)
