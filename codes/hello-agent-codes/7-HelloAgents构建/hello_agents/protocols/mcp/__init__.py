"""
MCP 协议模块 — 客户端与服务器实现

基于 Model Context Protocol (MCP) 提供:
  - MCPClient — 连接 MCP 服务器，调用工具/资源/提示
  - MCPServer — 快速创建 MCP 服务端，注册工具并启动

用法 (客户端):
    async with MCPClient(["npx", "-y", "@modelcontextprotocol/server-filesystem", "."]) as mcp:
        tools = await mcp.list_tools()
        result = await mcp.call_tool("read_file", {"path": "README.md"})

用法 (服务端):
    server = MCPServer(name="weather", description="天气查询")
    server.add_tool(get_weather)
    server.run()  # stdio 模式
"""

from .client import MCPClient
from .server import MCPServer, create_mcp_server

__all__ = ["MCPClient", "MCPServer", "create_mcp_server"]
