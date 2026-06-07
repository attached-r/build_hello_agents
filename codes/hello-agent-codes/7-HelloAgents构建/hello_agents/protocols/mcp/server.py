"""
MCP 服务器 — 基于 FastMCP 快速创建 MCP 服务端。

提供 MCPServer 包装类，简化 MCP 服务器的创建流程。
支持 stdio（用于本地 MCP 客户端）和 SSE/HTTP（用于远程连接）两种传输模式。

用法:
    # 创建服务器
    server = MCPServer(name="weather-server", description="天气查询服务")

    # 注册工具（函数签名自动生成 JSON Schema）
    def get_weather(city: str) -> str:
        \"\"\"获取指定城市的当前天气\"\"\"
        return f"{city} 25°C"

    server.add_tool(get_weather)

    # 启动（stdio 模式 — 默认，供 MCPClient 连接）
    server.run()

    # 或启动 SSE 模式（HTTP 服务）
    server.run(transport="sse", port=8000)
"""

from __future__ import annotations

import inspect
import logging
import sys
from typing import Any, Callable, Dict, List, Optional

logger = logging.getLogger(__name__)


class MCPServer:
    """MCP 服务器封装 — 基于 FastMCP 提供便捷的工具注册与启动接口。

    Attributes:
        name: 服务器名称
        description: 服务器描述
        tools: 已注册的工具函数列表
    """

    def __init__(
        self,
        name: str = "MCP Server",
        description: str = "",
    ):
        """初始化 MCP 服务器。

        Args:
            name: 服务器名称（也用作 FastMCP 实例名称）
            description: 服务器描述
        """
        self.name = name
        self.description = description
        self._tools: List[Callable] = []
        self._fastmcp_instance: Any = None

    # ── 工具注册 ──────────────────────────────────────────

    def add_tool(self, func: Callable) -> Callable:
        """注册一个工具函数到 MCP 服务器。

        工具函数的:
          - 函数名 → 工具名
          - 文档字符串 → 工具描述
          - 类型注解 → 参数 JSON Schema
          - 返回值类型 → 输出格式

        Args:
            func: 要注册的函数。应包含完整的文档字符串和类型注解。

        Returns:
            原函数（支持用作装饰器）

        Raises:
            TypeError: func 不是可调用对象
        """
        if not callable(func):
            raise TypeError(f"工具必须是可调用对象，收到: {type(func)}")

        self._tools.append(func)

        # 如果 FastMCP 实例已创建，立即注册到实例
        if self._fastmcp_instance is not None:
            self._fastmcp_instance.tool()(func)

        return func

    def tool(self, func: Optional[Callable] = None) -> Callable:
        """装饰器方式注册工具（与 FastMCP 风格一致）。

        用法:
            @server.tool()
            def my_tool(x: int) -> int:
                ...

        或直接:
            @server.tool
            def my_tool(x: int) -> int:
                ...
        """
        if func is not None:
            return self.add_tool(func)
        return self.add_tool

    # ── 服务器启动 ──────────────────────────────────────────

    def run(
        self,
        transport: str = "stdio",
        host: str = "0.0.0.0",
        port: int = 8000,
        log_level: str = "info",
    ) -> None:
        """启动 MCP 服务器。

        Args:
            transport: 传输模式
                - "stdio"（默认）: 标准输入输出模式，供本地 MCPClient 连接
                - "sse": SSE/HTTP 模式，供远程客户端连接
            host: 监听地址（仅 SSE 模式有效）
            port: 监听端口（仅 SSE 模式有效）
            log_level: 日志级别（仅 SSE 模式有效）

        Raises:
            ImportError: fastmcp 未安装
            ValueError: transport 参数不合法
        """
        server = self._build()

        if transport == "stdio":
            # 提示信息输出到 stderr，避免污染 stdout（MCP 协议通信通道）
            print(f"🔌 MCP 服务器 [{self.name}] 启动中... （stdio 模式）", file=sys.stderr)
            print("   等待 MCP 客户端连接...\n", file=sys.stderr)
            server.run(transport="stdio")

        elif transport == "sse":
            print(f"\n🌐 MCP 服务器 [{self.name}] 启动中... （SSE 模式）", file=sys.stderr)
            print(f"   地址: http://{host}:{port}/mcp\n", file=sys.stderr)
            server.run(transport="sse", host=host, port=port, log_level=log_level)

        else:
            raise ValueError(
                f"不支持的传输模式: {transport!r}，请使用 'stdio' 或 'sse'"
            )

    # ── 内部方法 ──────────────────────────────────────────

    def _build(self) -> Any:
        """构建底层 FastMCP 实例并注册所有工具。"""
        from fastmcp import FastMCP

        # FastMCP 较新版本已移除 description 参数，放在 name 里做标识
        name_str = self.name
        if self.description:
            name_str = f"{self.name} ({self.description})"

        self._fastmcp_instance = FastMCP(name_str)

        # 注册所有已添加的工具
        for func in self._tools:
            self._fastmcp_instance.tool()(func)

        return self._fastmcp_instance

    def list_tools_info(self) -> List[Dict[str, Any]]:
        """获取已注册工具的元信息（无需启动服务器）。"""
        info = []
        for func in self._tools:
            sig = inspect.signature(func)
            params = [
                {
                    "name": p.name,
                    "annotation": str(p.annotation) if p.annotation is not inspect.Parameter.empty else "str",
                    "default": repr(p.default) if p.default is not inspect.Parameter.empty else None,
                }
                for p in sig.parameters.values()
                if p.name != "self"
            ]
            info.append({
                "name": func.__name__,
                "description": inspect.cleandoc(func.__doc__ or ""),
                "parameters": params,
            })
        return info

    # ── 上下文管理器支持（用于测试） ───────────────────────

    async def __aenter__(self) -> "MCPServer":
        return self

    async def __aexit__(self, *args: Any) -> None:
        pass

    def __repr__(self) -> str:
        return f"MCPServer(name={self.name!r}, tools={len(self._tools)})"


# ════════════════════════════════════════════════════════════
# 便捷工厂函数
# ════════════════════════════════════════════════════════════

def create_mcp_server(
    name: str = "MCP Server",
    description: str = "",
) -> MCPServer:
    """创建 MCPServer 实例的便捷函数。

    Args:
        name: 服务器名称
        description: 服务器描述

    Returns:
        MCPServer 实例
    """
    return MCPServer(name=name, description=description)


# ════════════════════════════════════════════════════════════
# 自测 / 演示
# ════════════════════════════════════════════════════════════

if __name__ == "__main__":
    print("=" * 50)
    print("MCPServer 自测")
    print("=" * 50)

    # 测试服务器创建与工具注册
    def add(a: int, b: int) -> int:
        """将两个数相加"""
        return a + b

    def greet(name: str) -> str:
        """向指定姓名打招呼"""
        return f"你好, {name}!"

    server = MCPServer(name="demo", description="演示服务器")
    server.add_tool(add)
    server.add_tool(greet)

    print(f"\n✅ {server}")
    print(f"\n📋 已注册工具:")
    for t in server.list_tools_info():
        print(f"   · {t['name']}: {t['description']}")
        for p in t["parameters"]:
            print(f"     - {p['name']}: {p['annotation']}")

    print(f"\n✅ 验证通过")
    print(f"\n💡 启动方式:")
    print(f"   运行服务器: python {__file__}  # stdio 模式")
    print(f"   或使用: server.run(transport='sse', port=8000)")
