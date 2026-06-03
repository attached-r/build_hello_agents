# MCPClient 使用指南

## 概述

`MCPClient` 是 FastMCP 2.0 的异步客户端封装，用于连接**任何实现了 MCP 协议**的服务器。

支持 4 种连接方式：

| 方式 | 输入类型 | 示例 |
|------|---------|------|
| stdio 命令列表 | `list` | `["npx", "-y", "package", "."]` |
| HTTP/SSE URL | `str` | `"http://localhost:8000/mcp"` |
| 本地脚本路径 | `str` | `"path/to/server.py"` |
| 内存模式 | `FastMCP` | `FastMCP("server")` |

## 快速开始

### 安装依赖

```bash
pip install fastmcp
```

### 内存模式 — 无需网络，同进程通信

```python
import asyncio
from fastmcp import FastMCP
from hello_agents.protocols.mcp import MCPClient

# 1. 创建内存 MCP 服务器，注册工具
server = FastMCP("DemoServer")

@server.tool()
def add(a: int, b: int) -> int:
    """将两个数相加"""
    return a + b

@server.tool()
def greet(name: str) -> str:
    """向指定姓名打招呼"""
    return f"你好, {name}!"

# 2. 连接并调用
async with MCPClient(server) as mcp:
    tools = await mcp.list_tools()
    result = await mcp.call_tool("add", {"a": 10, "b": 20})
```

### stdio 模式 — 连接 npx MCP 服务器

需要安装 [Node.js](https://nodejs.org/)，`npx` 会自动下载包：

```python
import asyncio
from hello_agents.protocols.mcp import MCPClient

async with MCPClient([
    "npx", "-y",
    "@modelcontextprotocol/server-filesystem",
    "."   # 文件系统根目录
]) as mcp:
    tools = await mcp.list_tools()
    result = await mcp.call_tool("read_file", {"path": "README.md"})
```

其他官方 MCP 服务器（[GitHub 仓库](https://github.com/modelcontextprotocol/servers)）：

| 包名 | 功能 |
|------|------|
| `@modelcontextprotocol/server-filesystem` | 文件系统操作 |
| `@modelcontextprotocol/server-github` | GitHub API |
| `@modelcontextprotocol/server-postgres` | PostgreSQL 数据库 |
| `@modelcontextprotocol/server-sqlite` | SQLite 数据库 |
| `@modelcontextprotocol/server-puppeteer` | 浏览器自动化 |

### HTTP 模式 — 连接远程 MCP 服务器

```python
async with MCPClient("http://localhost:8000/mcp") as mcp:
    prompts = await mcp.list_prompts()
    result = await mcp.get_prompt("greeting", {"name": "MCP"})
```

### 本地脚本模式

```python
async with MCPClient("path/to/mcp_server.py") as mcp:
    resources = await mcp.list_resources()
    content = await mcp.read_resource("file:///data/doc.txt")
```

## API 参考

### 连接生命周期

```python
# 方式 A: 上下文管理器（推荐）
async with MCPClient(server) as mcp:
    await mcp.list_tools()

# 方式 B: 手动管理
mcp = MCPClient(server)
await mcp.connect()
try:
    await mcp.call_tool(...)
finally:
    await mcp.disconnect()
```

### 核心方法

| 方法 | 说明 | 返回 |
|------|------|------|
| `list_tools()` | 列出所有可用工具 | `List[Tool]` |
| `call_tool(name, args)` | 调用指定工具 | `CallToolResult` |
| `list_resources()` | 列出所有可用资源 | `List[Resource]` |
| `read_resource(uri)` | 读取指定资源 | `ReadResourceResult` |
| `list_prompts()` | 列出所有提示模板 | `List[Prompt]` |
| `get_prompt(name, args)` | 获取指定提示模板 | `PromptResult` |

### 结果提取

MCP 返回的结果对象，通过 `content` 字段获取文本：

```python
result = await mcp.call_tool("add", {"a": 1, "b": 2})

# 提取文本内容
content = getattr(result, "content", [])
if content:
    text = getattr(content[0], "text", str(content[0]))
    print(text)  # "3"
```

### 错误处理

```python
try:
    async with MCPClient() as mcp:
        pass
except ValueError as e:
    print(f"未指定服务器: {e}")

# 未连接时调用工具会抛出 RuntimeError
mcp = MCPClient(server)
try:
    await mcp.list_tools()
except RuntimeError as e:
    print(f"请先连接: {e}")
```

## 与 MCPTool 集成

`MCPTool` 将异步的 `MCPClient` 包装为同步 Tool，供 Agent 调用：

```python
from hello_agents.tools import MCPTool

# 方式 1: 预置连接参数（惰性连接）
mcp_tool = MCPTool(connection=[
    "npx", "-y",
    "@modelcontextprotocol/server-filesystem",
    "."
])
result = mcp_tool.run({
    "action": "call_tool",
    "tool_name": "read_file",
    "arguments": {"path": "README.md"}
})

# 方式 2: 传入已连接的 MCPClient
from hello_agents.protocols import MCPClient
import asyncio

client = MCPClient(FastMCP("Demo"))
asyncio.run(client.connect())
tool = MCPTool(client=client)

# 方式 3: 在 run 中连接
mcp_tool = MCPTool()
mcp_tool.run({"action": "connect", "server": ["python", "server.py"]})
mcp_tool.run({"action": "list_tools"})
```

### MCPTool 支持的操作

| action | 说明 | 必要参数 |
|--------|------|---------|
| `connect` | 连接 MCP 服务器 | `server` |
| `disconnect` | 断开连接 | — |
| `list_tools` | 列出可用工具 | — |
| `call_tool` | 调用工具 | `tool_name`, `arguments` |
| `list_resources` | 列出资源 | — |
| `read_resource` | 读取资源 | `uri` |
| `list_prompts` | 列出提示模板 | — |
| `get_prompt` | 获取提示 | `name`, `arguments` |

## 完整测试示例

见 [test/testMCP/mcpClient.py](../7-HelloAgents构建/test/testMCP/mcpClient.py)，包含：

| 测试 | 说明 |
|------|------|
| `test_in_memory()` | 内存模式 — 建服务器→注册工具→调用 |
| `test_file_server()` | stdio 模式 — 连接 server-filesystem |
| `test_discover_tools()` | 查看工具参数 Schema |
| `test_connection_errors()` | 错误处理测试 |

运行方式：

```bash
cd 7-HelloAgents构建
python test/testMCP/mcpClient.py
```

## 架构示意

```
外部 MCP 服务器       MCPClient             MCPTool           Agent
(npx包/远程服务)  ←→  (异步客户端)  ←→  (同步包装器)  ←→  (使用工具)
                      fastmcp.Client   asyncio.run_coro_threadsafe
                      StdioTransport   专用事件循环线程
```

## 参考

- [MCP 协议官方文档](https://modelcontextprotocol.io/)
- [FastMCP GitHub](https://github.com/jlowin/fastmcp)
- [MCP 官方服务器集合](https://github.com/modelcontextprotocol/servers)
- [FastMCP PyPI](https://pypi.org/project/fastmcp/)
