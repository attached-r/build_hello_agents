"""
MCP 客户端 — 连接 MCP 服务器并调用工具 / 资源 / 提示。

基于 FastMCP 2.0 实现，支持五种连接方式:
  1. 命令列表 (stdio):    ["npx", "-y", "@modelcontextprotocol/server-filesystem", "."]
  2. HTTP/SSE 服务器:     "http://localhost:8000/mcp"
  3. SSE 自定义配置:      SSEConfig 对象显式控制传输参数
  4. 本地脚本:            "path/to/mcp_server.py"
  5. 内存模式:            FastMCP 实例

用法:
    # 方式 1: stdio — 通过命令列表启动本地 MCP 服务器进程
    async with MCPClient(["npx", "-y", "@modelcontextprotocol/server-filesystem", "."]) as mcp:
        tools = await mcp.list_tools()
        result = await mcp.call_tool("read_file", {"path": "README.md"})

    # 方式 2: HTTP/SSE — 连接远程 MCP 服务器（自动使用 SSE 传输）
    async with MCPClient("http://localhost:8000/mcp") as mcp:
        prompts = await mcp.list_prompts()

    # 方式 3: SSE 自定义配置 — 自定义请求头、超时等
    from hello_agents.protocols.mcp.transports import SSEConfig
    async with MCPClient(SSEConfig(url="http://localhost:8000/mcp", headers={"Authorization": "Bearer xxx"})) as mcp:
        tools = await mcp.list_tools()

    # 方式 4: 本地脚本 — 自动启动 Python MCP 服务器
    async with MCPClient("my_server.py") as mcp:
        resources = await mcp.list_resources()

    # 方式 5: 内存 — 直接与 FastMCP 实例通信（测试用）
    from fastmcp import FastMCP
    server = FastMCP("TestServer")
    @server.tool()
    def add(a: int, b: int) -> int:
        return a + b
    async with MCPClient(server) as mcp:
        result = await mcp.call_tool("add", {"a": 1, "b": 2})
"""

from __future__ import annotations
from fastmcp import FastMCP                         #? 导入 FastMCP  实现客户端连接
import os
import sys
from typing import TYPE_CHECKING, Any, Dict, List, Optional, Union

if TYPE_CHECKING:
    from .transports import SSEConfig                # 仅类型检查时导入

# ── 路径引导: 自动向上搜索项目根目录 ────────────────────────────
_BASE = os.path.abspath(__file__)
while not os.path.isdir(os.path.join(os.path.dirname(_BASE), 'hello_agents')):
    _BASE = os.path.dirname(_BASE)
    if os.path.dirname(_BASE) == _BASE:
        break
_PROJECT_ROOT = os.path.dirname(_BASE)
if _PROJECT_ROOT not in sys.path:
    sys.path.insert(0, _PROJECT_ROOT)

# ── 类型前瞻导入（避免循环依赖） ─────────────────────────────
# 仅在类型检查或运行时惰性导入 SSETransport / SSEConfig


class MCPClient:
    """MCP 客户端封装 — 管理连接生命周期，提供统一的 Tool/Resource/Prompt 访问接口。

    Attributes:
        connected: 是否已连接到 MCP 服务器
    """

    def __init__(
        self,
        server: Optional[Union[str, List[str], "FastMCP", "SSEConfig"]] = None,
        sse_headers: Optional[Dict[str, str]] = None,
        sse_timeout: float = 60.0,
    ):
        """初始化 MCP 客户端。

        Args:
            server: 连接目标
                - List[str]: 命令列表（如 ["npx", "-y", "package", "."]）→ stdio 模式
                - str: 以 http:// 或 https:// 开头 → HTTP/SSE 模式
                - str: 其他 → 视为本地脚本路径
                - FastMCP 实例: 内存模式（无需网络，用于测试）
                - SSEConfig 实例: 显式 SSE 传输（可自定义请求头、超时）
            sse_headers: 快捷设置 SSE 请求头（仅在 server 为 HTTP URL 时生效）
            sse_timeout: 快捷设置 SSE 超时（秒，默认 60）
        """
        self._server_input = server
        self._sse_headers = sse_headers
        self._sse_timeout = sse_timeout

        # fastmcp.Client 实例（异步）
        self._client: Optional[Any] = None

    # ══════════════════════════════════════════════════════════════════
    # 连接生命周期
    # ══════════════════════════════════════════════════════════════════

    async def __aenter__(self) -> "MCPClient":
        await self.connect()
        return self

    async def __aexit__(self, *args: Any) -> None:
        await self.disconnect()

    async def connect(self) -> None:
        """建立与 MCP 服务器的连接。

        根据传入的 server 类型自动选择传输方式:
          - List[str]          → stdio（子进程管道）
          - SSEConfig 实例     → SSE（全参数自定义）
          - http:// / https:// → SSE（流式传输）
          - 脚本路径           → 本地子进程
          - FastMCP 实例       → 内存模式

        Raises:
            ValueError: 未指定 server 参数
            ImportError: fastmcp 库未安装
            RuntimeError: 连接失败
        """
        server = self._server_input
        if server is None:
            raise ValueError(
                "MCPClient: 未指定服务器。\n"
                "请传入命令列表 (list)、URL/脚本路径 (str) 或 FastMCP 实例。"
            )

        import fastmcp
        from .transports import SSEConfig as _SSEConfig, SSETransport as _SSETransport

        # ── 1) 命令列表 → StdioTransport ────────────────────────
        if isinstance(server, list):
            from fastmcp.client.transports.stdio import StdioTransport

            transport = StdioTransport(command=server[0], args=server[1:])
            self._client = fastmcp.Client(transport)

        # ── 2) SSEConfig 实例 → 显式 SSE 传输 ──────────────────
        elif isinstance(server, _SSEConfig):
            transport = _SSETransport(server)
            self._client = fastmcp.Client(transport)

        # ── 3) HTTP URL → 自动创建 SSE 传输 ─────────────────────
        elif isinstance(server, str) and (
            server.startswith("http://") or server.startswith("https://")
        ):
            config = _SSEConfig(
                url=server,
                headers=self._sse_headers or {},
                timeout=self._sse_timeout,
            )
            transport = _SSETransport(config)
            self._client = fastmcp.Client(transport)

        # ── 4) 其他（本地脚本 / FastMCP / dict）→ 自动推断 ────
        else:
            self._client = fastmcp.Client(server)

        await self._client.__aenter__()

    async def disconnect(self) -> None:
        """断开 MCP 连接，释放资源。"""
        if self._client is not None:
            try:
                await self._client.__aexit__(None, None, None)
            except Exception:
                pass
            self._client = None

    # ══════════════════════════════════════════════════════════════════
    # Tools — 工具发现与调用
    # ══════════════════════════════════════════════════════════════════

    async def list_tools(self) -> List[Any]:
        """列出 MCP 服务器提供的所有工具。

        Returns:
            工具对象列表，每个对象包含 name / description / inputSchema 等属性

        Raises:
            RuntimeError: 未连接服务器
        """
        self._require_connected()
        return await self._client.list_tools()

    async def call_tool(
        self,
        tool_name: str,
        arguments: Optional[Dict[str, Any]] = None,
    ) -> Any:
        """调用 MCP 服务器上的工具。

        Args:
            tool_name: 工具名称
            arguments: 工具参数字典

        Returns:
            工具执行结果（CallToolResult），包含 content 和 isError 等属性

        Raises:
            RuntimeError: 未连接服务器
        """
        self._require_connected()
        return await self._client.call_tool(tool_name, arguments or {})

    # ══════════════════════════════════════════════════════════════════
    # Resources — 资源发现与读取
    # ══════════════════════════════════════════════════════════════════

    async def list_resources(self) -> List[Any]:
        """列出 MCP 服务器提供的所有资源。

        Returns:
            资源对象列表，每个对象包含 uri / name / description 等属性
        """
        self._require_connected()
        return await self._client.list_resources()

    async def read_resource(self, uri: str) -> Any:
        """读取指定 URI 的资源内容。

        Args:
            uri: 资源 URI（如 "file:///path/to/file"）

        Returns:
            资源内容（ReadResourceResult）
        """
        self._require_connected()
        return await self._client.read_resource(uri)

    # ══════════════════════════════════════════════════════════════════
    # Prompts — 提示模板发现与获取
    # ══════════════════════════════════════════════════════════════════

    async def list_prompts(self) -> List[Any]:
        """列出 MCP 服务器提供的所有提示模板。

        Returns:
            提示模板对象列表，每个对象包含 name / description / arguments 等属性
        """
        self._require_connected()
        return await self._client.list_prompts()

    async def get_prompt(
        self,
        name: str,
        arguments: Optional[Dict[str, Any]] = None,
    ) -> Any:
        """获取指定名称的提示模板内容。

        Args:
            name: 提示模板名称
            arguments: 模板参数

        Returns:
            提示内容（PromptResult），包含 messages 列表
        """
        self._require_connected()
        return await self._client.get_prompt(name, arguments or {})

    # ══════════════════════════════════════════════════════════════════
    # 状态查询
    # ══════════════════════════════════════════════════════════════════

    @property
    def connected(self) -> bool:
        """是否已连接到 MCP 服务器。"""
        return self._client is not None

    def _require_connected(self) -> None:
        """检查连接状态，未连接时抛出 RuntimeError。"""
        if not self.connected:
            raise RuntimeError(
                "MCP 客户端未连接。请先调用 connect() 或使用 async with 上下文管理器。"
            )


# ══════════════════════════════════════════════════════════════════════
# 便捷工厂函数
# ══════════════════════════════════════════════════════════════════════

def create_mcp_client(
    server: Optional[Union[str, List[str], Any, "SSEConfig"]] = None,
    sse_headers: Optional[Dict[str, str]] = None,
    sse_timeout: float = 60.0,
) -> MCPClient:
    """创建 MCPClient 实例的便捷函数。

    Args:
        server: 同 MCPClient.__init__ 的 server 参数
        sse_headers: SSE 请求头（仅 HTTP 模式生效）
        sse_timeout: SSE 超时秒数（默认 60）

    Returns:
        MCPClient 实例（尚未连接，需使用 async with 或手动 connect）
    """
    return MCPClient(server=server, sse_headers=sse_headers, sse_timeout=sse_timeout)


# ══════════════════════════════════════════════════════════════════════
# 自测 / 演示
# ══════════════════════════════════════════════════════════════════════

if __name__ == "__main__":
    import asyncio

    async def demo():
        """演示 MCPClient 的各种工作模式。"""
        from fastmcp import FastMCP

        # ── 内存模式演示 ────────────────────────────────────────
        server = FastMCP("DemoServer")

        @server.tool()
        def add(a: int, b: int) -> int:
            """将两个数相加"""
            return a + b

        @server.tool()
        def greet(name: str) -> str:
            """向指定姓名打招呼"""
            return f"你好, {name}!"

        print("=" * 60)
        print("MCPClient 自测（内存模式）")
        print("=" * 60)

        async with MCPClient(server) as mcp:
            tools = await mcp.list_tools()
            print(f"\n🔧 可用工具 ({len(tools)}):")
            for t in tools:
                print(f"   · {t.name}: {t.description}")

            result = await mcp.call_tool("add", {"a": 10, "b": 20})
            content = getattr(result, "content", [])
            text = getattr(content[0], "text", str(content)) if content else str(result)
            print(f"\n📝 add(10, 20) = {text}")

            result = await mcp.call_tool("greet", {"name": "MCP"})
            content = getattr(result, "content", [])
            text = getattr(content[0], "text", str(content)) if content else str(result)
            print(f"📝 greet('MCP') = {text}")

        print("\n✅ 内存模式通过\n")

        # ── SSE 模式演示（需要远程 MCP 服务器） ─────────────────
        print("=" * 60)
        print("SSE 传输示例（需远程 MCP 服务器）")
        print("=" * 60)
        print()
        print("方式 A — 直接传 URL:")
        print('    async with MCPClient("http://localhost:8000/mcp") as mcp:')
        print("        tools = await mcp.list_tools()")
        print()
        print("方式 B — 自定义请求头:")
        print("    from hello_agents.protocols.mcp.transports import SSEConfig")
        print("    config = SSEConfig(")
        print('        url="http://localhost:8000/mcp",')
        print('        headers={"Authorization": "Bearer xxx"},')
        print("        timeout=120.0,")
        print("    )")
        print("    async with MCPClient(config) as mcp:")
        print("        tools = await mcp.list_tools()")
        print()
        print("方式 C — 快捷参数:")
        print("    async with MCPClient(")
        print('        "http://localhost:8000/mcp",')
        print('        sse_headers={"Authorization": "Bearer xxx"},')
        print("        sse_timeout=120.0,")
        print("    ) as mcp:")
        print("        tools = await mcp.list_tools()")
        print()
        print("=" * 60)

    asyncio.run(demo())
