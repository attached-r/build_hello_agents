"""
MCP 协议模块 — 客户端实现

提供基于 Model Context Protocol (MCP) 的外部工具调用能力。
当前实现了 MCPClient，支持 stdio / HTTP / 内存三种连接模式。

用法:
    async with MCPClient(["npx", "-y", "@modelcontextprotocol/server-filesystem", "."]) as mcp:
        tools = await mcp.list_tools()
        result = await mcp.call_tool("read_file", {"path": "README.md"})
"""

from .client import MCPClient

__all__ = ["MCPClient"]
