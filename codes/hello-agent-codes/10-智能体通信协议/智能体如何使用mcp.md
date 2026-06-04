# 智能体如何使用 MCP

## 架构总览

```
┌─────────────────────────────────────────────────────────┐
│                     智能体 (Agent)                       │
│  MySimpleAgent / MyFunctionAgent / ReActAgent           │
│         │                                               │
│         ▼                                               │
│  ToolRegistry.execute_tool("mcp", params)               │
│         │                                               │
│         ▼                                               │
│  MCPTool.run(parameters)        ← 同步包装器            │
│    └─ daemon 线程 + 独立事件循环                         │
│         │                                               │
│         ▼                                               │
│  MCPClient (异步)                                       │
│    ├─ connect() / disconnect()                          │
│    ├─ list_tools() / call_tool()                        │
│    ├─ list_resources() / read_resource()                │
│    └─ list_prompts() / get_prompt()                     │
│         │                                               │
│         ▼                                               │
│  传输层 (Transport)                                     │
│    ├─ StdioTransport  ← 本地子进程                      │
│    ├─ SSETransport    ← 远程 HTTP/SSE                   │
│    └─ 内存模式         ← 同进程 FastMCP 实例            │
│         │                                               │
│         ▼                                               │
│  MCP 服务器 (filesystem / database / custom ...)        │
└─────────────────────────────────────────────────────────┘
```

**核心链路**：Agent → ToolRegistry → MCPTool(同步桥) → MCPClient(异步) → Transport → MCP Server

---

## 核心澄清：Agent 不会"自动调用 MCPTool"

这是一个很自然但需要澄清的疑惑。**Agent 不区分 MCPTool 和其他工具**——所有工具在 ToolRegistry 里是**平等注册、按名匹配**的。

### 工具调用的真实流程

```
多个工具注册 → 全部描述写入 system prompt → LLM 选一个 → Agent 按名称执行
```

举例：

```python
# 三个工具注册到同一个 registry
registry.register_tool(calculator_tool)        # 名称: "calculator"
registry.register_tool(search_tool)             # 名称: "search"
registry.register_tool(MCPTool(...))            # 名称: "mcp"
```

Agent 在 system prompt 中看到的工具描述是：

```text
## 可用工具
- calculator: 执行数学计算，传入表达式如 '1+2*3'
- search: 搜索知识库，返回相关文档
- mcp: MCP 服务器工具，支持调用远程工具/资源/提示
```

**LLM 根据用户的问题选择工具**：

| 用户问题 | LLM 选择的工具 | 原因 |
|---------|---------------|------|
| "计算 1+2×3" | `calculator` | 描述匹配数学计算 |
| "搜索昨天的会议记录" | `search` | 描述匹配搜索 |
| "读取 /etc/config 文件" | `mcp` | 只有 MCP 能操作远程服务器 |
| "用服务器上的 add 工具计算" | `mcp` | 同上，且带参数 action=call_tool |

### MCPTool 的特殊之处

MCPTool 不特殊在"被优先调用"，而是特殊在它是一个**门面（Facade）工具**：

| 普通工具 | MCPTool |
|---------|---------|
| 一个工具只做一件事（如 `calculator` 只算数） | 一个工具通过 `action` 参数分发到多个子操作 |
| 参数直接是业务参数（如 `expression`） | 参数先声明 `action`，再传业务参数 |
| 注册多个就要写多个 Tool 类 | 注册一个 MCPTool = 接入整个 MCP 服务器的所有工具 |

所以如果你的 ToolRegistry 里**只注册了 MCPTool 这一个工具**，那 LLM 自然只能选它——不是因为 Agent 偏爱它，而是**没别的可选**。

---

## 第一步：启动 MCP 服务器

MCP 服务器提供工具/资源/提示。常见方式：

### 方式 A：使用现成的 npm 包
```bash
npx -y @modelcontextprotocol/server-filesystem .
npx -y @modelcontextprotocol/server-github ...
```

### 方式 B：自建 Python 服务器
```python
from fastmcp import FastMCP

server = FastMCP("MyServer")

@server.tool()
def add(a: int, b: int) -> int:
    """将两个数相加"""
    return a + b

@server.tool()
def search_db(query: str) -> str:
    """搜索数据库"""
    return f"查询结果: {query}"

server.run()  # 启动 stdio 模式
```

### 方式 C：远程 HTTP/SSE 服务器
```python
from fastmcp import FastMCP

server = FastMCP("RemoteServer")

@server.tool()
def greet(name: str) -> str:
    return f"你好, {name}!"

# 以 SSE 模式启动（需要 uvicorn 等 ASGI 服务器）
# uvicorn run:app --host 0.0.0.0 --port 8000
```

---

## 第二步：连接 MCP 服务器（MCPClient）

`MCPClient` 是异步客户端，支持 **5 种连接方式**：

```python
from hello_agents.protocols.mcp import MCPClient
```

### 1. stdio 模式 — 本地子进程
```python
async with MCPClient(["npx", "-y", "@modelcontextprotocol/server-filesystem", "."]) as mcp:
    tools = await mcp.list_tools()
    result = await mcp.call_tool("read_file", {"path": "README.md"})
```

### 2. HTTP/SSE 模式 — 远程服务器
```python
async with MCPClient("http://localhost:8000/mcp") as mcp:
    tools = await mcp.list_tools()
```

### 3. SSE 自定义配置 — 带鉴权/超时
```python
from hello_agents.protocols.mcp.transports import SSEConfig

config = SSEConfig(
    url="http://localhost:8000/mcp",
    headers={"Authorization": "Bearer sk-xxx"},
    timeout=120.0,
)
async with MCPClient(config) as mcp:
    tools = await mcp.list_tools()
```

### 4. 快捷参数
```python
async with MCPClient(
    "http://localhost:8000/mcp",
    sse_headers={"Authorization": "Bearer sk-xxx"},
    sse_timeout=120.0,
) as mcp:
    tools = await mcp.list_tools()
```

### 5. 内存模式 — 同进程通信（测试/开发用）
```python
from fastmcp import FastMCP

server = FastMCP("Demo")
@server.tool()
def add(a: int, b: int) -> int:
    return a + b

async with MCPClient(server) as mcp:
    result = await mcp.call_tool("add", {"a": 1, "b": 2})
```

### MCPClient 核心方法

| 方法 | 说明 |
|------|------|
| `connect()` / `disconnect()` | 手动连接管理 |
| `list_tools()` | 列出所有可用工具 |
| `call_tool(name, args)` | 调用工具 |
| `list_resources()` | 列出资源 |
| `read_resource(uri)` | 读取资源 |
| `list_prompts()` | 列出提示模板 |
| `get_prompt(name, args)` | 获取提示内容 |

---

## 第三步：桥接同步层（MCPTool）

智能体运行在同步环境中，`MCPTool` 是连接异步 `MCPClient` 与同步 `Agent` 的桥梁。

它使用 **daemon 线程 + 独立事件循环** 模式，将异步调用转为同步等待（最长 60s 超时）。

```python
from hello_agents.tools import MCPTool, create_mcp_tool
```

### 创建 MCPTool

```python
# 方式 A：传入连接参数（惰性连接，首次 run() 时自动连接）
tool = MCPTool(connection=["python", "my_server.py"])

# 方式 B：传入已连接的 MCPClient
import asyncio
client = MCPClient(FastMCP("Demo"))
asyncio.run(client.connect())
tool = MCPTool(client=client)

# 方式 C：使用工厂函数
tool = create_mcp_tool(connection=["npx", "-y", "server-filesystem", "."])
```

### MCPTool 的 action 分发

所有操作通过 `run({"action": "...", ...})` 入口：

```python
# 手动连接
tool.run({"action": "connect", "server": ["python", "server.py"]})

# 列出工具
tool.run({"action": "list_tools"})

# 调用工具
tool.run({"action": "call_tool", "tool_name": "add", "arguments": {"a": 1, "b": 2}})

# 读取资源
tool.run({"action": "read_resource", "uri": "file:///data/doc.txt"})

# 断开连接
tool.run({"action": "disconnect"})
```

### 常见参数速查

| action | 必填参数 | 可选参数 |
|--------|---------|---------|
| `connect` | — | `server`（连接目标） |
| `disconnect` | — | — |
| `list_tools` | — | — |
| `call_tool` | `tool_name`, `arguments` | — |
| `list_resources` | — | — |
| `read_resource` | `uri` | — |
| `list_prompts` | — | — |
| `get_prompt` | `name` | `arguments` |

---

## 第四步：注册到智能体（Agent）

### 在所有支持工具的智能体中使用

目前 **3 种智能体** 支持 MCP 工具集成：

### MySimpleAgent
```python
from hello_agents.agents import MySimpleAgent
from hello_agents.tools import MCPTool

agent = MySimpleAgent(name="助手", llm=llm)

# 注册 MCP 工具（内部自动创建 ToolRegistry）
mcp_tool = MCPTool(connection=["python", "math_server.py"])
agent.add_tool(mcp_tool)

# 智能体会在对话中自动调用 MCP 工具
# LLM 输出 [TOOL_CALL:tool_name:params] → 解析执行 → 返回结果
agent.run("请计算 12345 + 67890")
```

### MyFunctionAgent
```python
from hello_agents.agents import MyFunctionAgent
from hello_agents.tools import MCPTool, ToolRegistry

# 创建 ToolRegistry 并注册 MCPTool
registry = ToolRegistry()
registry.register_tool(MCPTool(connection=["python", "math_server.py"]))

# 传入智能体
agent = MyFunctionAgent(name="助手", llm=llm, tool_registry=registry)

# 或动态添加
agent.add_tool(MCPTool(connection=["python", "math_server.py"]))

# 智能体会在对话中调用工具
# LLM 输出 tool_name({"key": "value"}) → 解析执行 → 返回结果
agent.run("计算 1 + 2 = ?")
```

### ReActAgent
```python
from hello_agents.agents import ReActAgent
from hello_agents.tools import MCPTool

agent = ReActAgent(name="助手", llm=llm)

# 直接操作 tool_registry
agent.tool_registry.register_tool(MCPTool(connection=["python", "math_server.py"]))

# ReAct 循环: Thought → Action → Observation → Finish
agent.run("查询文件系统根目录有哪些文件")
```

---

## 完整示例：从零到智能体调用 MCP 工具

```python
"""演示：智能体通过 MCP 连接远程工具"""
import asyncio
from fastmcp import FastMCP
from hello_agents.llm import HelloAgentsLLM
from hello_agents.agents import MySimpleAgent
from hello_agents.tools import MCPTool

# 1. 创建 MCP 服务器（内存模式）
server = FastMCP("MathServer")

@server.tool()
def add(a: int, b: int) -> int:
    """将两个数相加"""
    return a + b

@server.tool()
def multiply(a: int, b: int) -> int:
    """将两个数相乘"""
    return a * b

# 2. 连接并创建 MCPTool
async def setup():
    client = MCPClient(server)
    await client.connect()
    return MCPTool(client=client)

mcp_tool = asyncio.run(setup())

# 3. 创建智能体并注册工具
llm = HelloAgentsLLM(api_key="...", model="gpt-4")
agent = MySimpleAgent(name="计算助手", llm=llm)
agent.add_tool(mcp_tool)

# 4. 运行智能体
response = agent.run("请计算 (5 + 3) * 2 的结果")
print(response)
```

---

## 常见场景

### 场景 1：文件系统操作
```python
# 连接文件系统 MCP 服务器
tool = MCPTool(connection=[
    "npx", "-y", "@modelcontextprotocol/server-filesystem", "/workspace"
])
agent.add_tool(tool)
# 智能体可以：读取文件、写入文件、列出目录...
```

### 场景 2：数据库查询
```python
# 连接数据库 MCP 服务器
tool = MCPTool(connection=["python", "db_server.py"])
agent.add_tool(tool)
# 智能体可以：执行 SQL、查询表结构、获取数据...
```

### 场景 3：远程 API 网关
```python
# 连接远程 HTTP MCP 服务器
from hello_agents.protocols.mcp.transports import SSEConfig

config = SSEConfig(
    url="https://api.example.com/mcp",
    headers={"Authorization": f"Bearer {API_KEY}"},
    timeout=30,
)
tool = MCPTool(connection=config)
agent.add_tool(tool)
# 智能体可以：调用远程 API、获取数据...
```

---

## 注意事项

### 连接生命周期
- `MCPTool` 默认**惰性连接**：首次 `run()` 时才建立连接
- 如果 MCP 服务器未启动，首次调用会超时（最长 60s）
- 建议在智能体启动前确保服务器可用

### 线程安全
- `MCPTool` 使用专用 daemon 线程运行事件循环
- 支持在 Jupyter、FastAPI 等已有事件循环的环境中使用
- 每个 `MCPTool` 实例拥有独立的事件循环

### 错误处理
```python
try:
    result = tool.run({"action": "call_tool", "tool_name": "add", "arguments": {"a": 1, "b": 2}})
except TimeoutError:
    print("MCP 服务器无响应")
except ConnectionError:
    print("无法连接到 MCP 服务器")
except RuntimeError as e:
    print(f"调用失败: {e}")
```

### 性能建议
- 一个 `MCPTool` 实例对应一个 MCP 服务器连接
- 多个智能体可以共享同一个 `MCPTool` 实例
- 不需要时调用 `tool.run({"action": "disconnect"})` 释放资源

---

## 相关文件索引

| 文件 | 作用 |
|------|------|
| `protocols/mcp/client.py` | MCPClient 异步客户端 |
| `protocols/mcp/transports/sse.py` | SSE 传输实现 |
| `protocols/mcp/transports/__init__.py` | 传输层导出 |
| `tools/builtin/protocol_tools.py` | MCPTool 同步包装器 |
| `tools/registry.py` | ToolRegistry 工具注册中心 |
| `core/agent.py` | Agent 基类 |
| `agents/my_simple_agent.py` | 支持工具的智能体（标记解析） |
| `agents/my_function_agent.py` | 支持工具的智能体（函数调用） |
| `agents/react_agent.py` | 支持工具的智能体（ReAct 循环） |
