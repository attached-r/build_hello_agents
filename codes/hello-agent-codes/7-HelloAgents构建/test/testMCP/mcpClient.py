"""
MCP 客户端测试 — 演示 MCPClient 的 4 种连接方式。

运行方式:
    python test/testMCP/mcpClient.py

依赖:
    pip install fastmcp
    方式2需要 Node.js + npx（会自动下载 @modelcontextprotocol/server-filesystem）
"""

import asyncio
import sys
import os

# ── 路径引导: 把项目根目录加入 Python 搜索路径 ──────────────
_project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "../.."))
if _project_root not in sys.path:
    sys.path.insert(0, _project_root)

from hello_agents.protocols.mcp.client import MCPClient


class MCPClientTest:
    """MCP 客户端测试套件"""

    @staticmethod
    async def test_in_memory():
        """① 内存模式 — 无需网络，同进程通信"""
        from fastmcp import FastMCP

        print("=" * 60)
        print("① 测试: 内存模式 (FastMCP 实例)")
        print("=" * 60)

        # 创建内存服务器，注册两个工具
        server = FastMCP("DemoServer")

        @server.tool()
        def add(a: int, b: int) -> int:
            """将两个数相加"""
            return a + b

        @server.tool()
        def greet(name: str) -> str:
            """向指定姓名打招呼"""
            return f"你好, {name}!"

        # 通过 MCPClient 连接并调用
        async with MCPClient(server) as mcp:
            # 列出工具
            tools = await mcp.list_tools()
            print(f"\n🔧 可用工具 ({len(tools)} 个):")
            for t in tools:
                print(f"   · {t.name}: {t.description or '无描述'}")

            # 调用 add
            result = await mcp.call_tool("add", {"a": 10, "b": 20})
            text = _get_text(result)
            print(f"\n📝 add(10, 20) = {text}")

            # 调用 greet
            result = await mcp.call_tool("greet", {"name": "MCP"})
            text = _get_text(result)
            print(f"📝 greet('MCP') = {text}")

        print("\n✅ 内存模式测试通过\n")

    @staticmethod
    async def test_file_server():
        """② stdio 模式 — 连接文件系统 MCP 服务器 (需要 npx)"""
        print("=" * 60)
        print("② 测试: stdio 模式 (server-filesystem)")
        print("=" * 60)
        print("  正在启动 npx @modelcontextprotocol/server-filesystem...")

        try:
            async with MCPClient([
                "npx", "-y",
                "@modelcontextprotocol/server-filesystem",
                "."
            ]) as mcp:
                # 列出工具
                tools = await mcp.list_tools()
                print(f"\n🔧 可用工具 ({len(tools)} 个):")
                for t in tools:
                    name = getattr(t, "name", "?")
                    desc = getattr(t, "description", "") or "无描述"
                    print(f"   · {name}: {desc}")

                # 调用 read_file 读取当前目录的某个文件
                result = await mcp.call_tool("read_file", {"path": __file__})
                text = _get_text(result)
                print(f"\n📝 read_file (前200字):")
                print(f"   {text[:200]}...")

        except FileNotFoundError:
            print("\n⚠️  未找到 npx，请安装 Node.js 后重试")
        except Exception as e:
            print(f"\n⚠️  连接失败: {e}")
            print("   (这是预期的 — 需要安装 Node.js 和 npx)")

        print("\n✅ stdio 模式测试完成\n")

    @staticmethod
    async def test_discover_tools():
        """③ 工具发现 — 详细查看工具的参数定义"""
        from fastmcp import FastMCP

        print("=" * 60)
        print("③ 测试: 工具发现与参数 Schema")
        print("=" * 60)

        server = FastMCP("SchemaDemo")

        @server.tool()
        def search(query: str, limit: int = 10, verbose: bool = False) -> str:
            """搜索数据库中的记录"""
            return f"搜索 '{query}' (limit={limit}, verbose={verbose})"

        async with MCPClient(server) as mcp:
            tools = await mcp.list_tools()
            for t in tools:
                name = getattr(t, "name", "?")
                desc = getattr(t, "description", "") or "无描述"
                print(f"\n🔧 {name}: {desc}")

                # 读取 inputSchema
                schema = getattr(t, "inputSchema", None) or getattr(t, "parameters", None)
                if schema and isinstance(schema, dict):
                    props = schema.get("properties", {})
                    required = schema.get("required", [])
                    for pname, pinfo in props.items():
                        ptype = pinfo.get("type", "any")
                        pdesc = pinfo.get("description", "")
                        req = " ✅ 必填" if pname in required else ""
                        print(f"   · {pname} ({ptype}): {pdesc}{req}")

            # 实际调用
            result = await mcp.call_tool("search", {"query": "MCP", "limit": 5})
            text = _get_text(result)
            print(f"\n📝 search('MCP', limit=5) = {text}")

        print("\n✅ 工具发现测试通过\n")

    @staticmethod
    async def test_connection_errors():
        """④ 错误处理 — 未连接时调用工具"""
        print("=" * 60)
        print("④ 测试: 错误处理")
        print("=" * 60)

        # 未传入 server → 应抛出 ValueError
        try:
            client = MCPClient()  # server=None
            async with client:
                pass
            print("❌ 应抛出异常但未抛出")
        except ValueError as e:
            print(f"✅ 未指定服务器时正确抛出: {e}")

        # 未连接时调用工具 → 应抛出 RuntimeError
        client = MCPClient()
        try:
            await client.list_tools()
            print("❌ 应抛出异常但未抛出")
        except RuntimeError as e:
            print(f"✅ 未连接时正确抛出: {e}")

        print("\n✅ 错误处理测试通过\n")


def _get_text(result) -> str:
    """从 MCP 调用结果中提取文本内容"""
    content = getattr(result, "content", [])
    if content:
        texts = []
        for item in content:
            t = getattr(item, "text", str(item))
            if t:
                texts.append(t)
        return "\n".join(texts)
    return str(result)


async def main():
    """运行所有测试"""
    print("\n" + "=" * 60)
    print("  MCP 客户端测试套件")
    print("=" * 60 + "\n")

    await MCPClientTest.test_in_memory()
    await MCPClientTest.test_file_server()
    await MCPClientTest.test_discover_tools()
    await MCPClientTest.test_connection_errors()

    print("=" * 60)
    print("  全部测试完成 🎉")
    print("=" * 60)


if __name__ == "__main__":
    asyncio.run(main())
