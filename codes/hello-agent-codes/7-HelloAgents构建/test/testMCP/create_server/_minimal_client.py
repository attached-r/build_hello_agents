#!/usr/bin/env python3
"""最简 MCP 客户端 — 测试 stdio 连接最简服务器"""

import asyncio
import json
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", ".."))

from hello_agents.protocols.mcp import MCPClient


def extract_text(result) -> str:
    content = getattr(result, "content", [])
    if content:
        texts = [getattr(item, "text", str(item)) for item in content if getattr(item, "text", None)]
        return "\n".join(texts)
    return str(result)


async def main():
    # 测试1: 直接用 fastmcp Client（不经过 MCPClient 包装）
    print("测试1: fastmcp.Client 直连 stdio...")
    try:
        from fastmcp import Client
        from fastmcp.client.transports.stdio import StdioTransport

        script = os.path.join(os.path.dirname(__file__), "_minimal_server.py")
        transport = StdioTransport(command="python", args=[script])
        client = Client(transport)
        async with client:
            tools = await client.list_tools()
            print(f"  ✅ 工具: {[t.name for t in tools]}")
            result = await client.call_tool("ping", {"msg": "hello"})
            print(f"  ✅ ping: {extract_text(result)}")
    except Exception as e:
        print(f"  ❌ 失败: {e}")

    print()

    # 测试2: 用 MCPClient 包装
    print("测试2: MCPClient 连接 stdio...")
    try:
        script = os.path.join(os.path.dirname(__file__), "_minimal_server.py")
        async with MCPClient(["python", script]) as mcp:
            tools = await mcp.list_tools()
            print(f"  ✅ 工具: {[t.name for t in tools]}")
            result = await mcp.call_tool("ping", {"msg": "hello"})
            print(f"  ✅ ping: {extract_text(result)}")
    except Exception as e:
        print(f"  ❌ 失败: {e}")

    print()
    print("=" * 40)
    print("测试完成")


if __name__ == "__main__":
    asyncio.run(main())
