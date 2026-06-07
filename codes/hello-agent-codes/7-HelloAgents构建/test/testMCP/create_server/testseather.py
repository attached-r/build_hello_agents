#!/usr/bin/env python3
"""测试天气查询 MCP 服务器

用法:
    python test/testMCP/create_server/testseather.py
"""

import asyncio
import json
import os
import sys

# ── 路径引导到 7-HelloAgents构建 ───────────────────
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", ".."))

from hello_agents.protocols.mcp import MCPClient


def extract_text(result) -> str:
    """从 MCP 调用结果中提取文本内容"""
    content = getattr(result, "content", [])
    if content:
        texts = [getattr(item, "text", str(item)) for item in content if getattr(item, "text", None)]
        return "\n".join(texts)
    return str(result)


async def test_weather_server():
    server_script = os.path.join(os.path.dirname(__file__), "weather.py")
    client = MCPClient(["python", server_script])

    try:
        async with client:
            # 测试1: 获取服务器信息
            result = await client.call_tool("get_server_info", {})
            info = json.loads(extract_text(result))
            print(f"服务器: {info['name']} v{info['version']}")

            # 测试2: 列出支持的城市
            result = await client.call_tool("list_supported_cities", {})
            cities = json.loads(extract_text(result))
            print(f"支持城市: {cities['count']} 个")

            # 测试3: 查询北京天气
            result = await client.call_tool("get_weather", {"city": "北京"})
            weather = json.loads(extract_text(result))
            if "error" not in weather:
                print(f"\n北京天气: {weather['temperature']}°C, {weather['condition']}")

            # 测试4: 查询深圳天气
            result = await client.call_tool("get_weather", {"city": "深圳"})
            weather = json.loads(extract_text(result))
            if "error" not in weather:
                print(f"深圳天气: {weather['temperature']}°C, {weather['condition']}")

            print("\n✅ 所有测试完成！")

    except Exception as e:
        print(f"❌ 测试失败: {e}")


if __name__ == "__main__":
    asyncio.run(test_weather_server())
