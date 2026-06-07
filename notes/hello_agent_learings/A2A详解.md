

# A2A 实现架构总览

HelloAgents 的 A2A 实现基于 Google 官方的 [a2a-sdk](https://github.com/google/a2a-sdk)，提供了三个核心组件：

| 组件 | 角色 | 类比 |
|------|------|------|
| **A2AAgentExecutor** | 将 HelloAgents Agent 包装为 A2A 标准执行器 | 翻译器 — 让 Agent "说" A2A 语言 |
| **A2AServer** | 启动 A2A 协议服务器，暴露 Agent 为 HTTP 服务 | 基站 — 让 Agent 可被发现和连接 |
| **A2ATool** | 作为 Tool 调用远程 A2A Agent | 电话 — 让 Agent 呼叫其他 Agent |

```
┌────────────────────────────────────────────────────────────┐
│                    A2A 协议实现架构                          │
│                                                            │
│  ┌──────────────┐    ┌──────────────┐    ┌──────────────┐  │
│  │ A2AAgentExec │───▶│  A2AServer   │───▶│  远程 Agent  │  │
│  │   (包装器)    │    │  (HTTP服务)   │    │  (A2A协议)   │  │
│  └──────────────┘    └──────────────┘    └──────────────┘  │
│         │                                                   │
│         │                   ┌──────────────┐                │
│         └──────────────────▶│   A2ATool    │                │
│                             │  (客户端工具)  │                │
│                             └──────────────┘                │
│                                    │                        │
│                                    ▼                        │
│                             ┌──────────────┐                │
│                             │ 远程 A2A 服务  │               │
│                             └──────────────┘                │
└────────────────────────────────────────────────────────────┘
```

## 依赖安装

```bash
pip install a2a-sdk httpx uvicorn
```

- `a2a-sdk` — Google 官方的 A2A Python SDK，提供协议核心类型和客户端
- `httpx` — 异步 HTTP 客户端，用于远程通信
- `uvicorn` — ASGI 服务器，用于启动 A2A HTTP 服务

---

# A2AAgentExecutor — 包装 Agent

> 代码位置: `hello_agents/protocols/a2a/implementation.py :46-124`

`A2AAgentExecutor` 的核心作用是将 HelloAgents 框架中的 Agent 包装为符合 A2A 协议的 `AgentExecutor`，使得普通 Agent 能够接入 A2A 通信网络。

## 设计原理

它通过 **动态子类工厂模式** 实现：

```python
class A2AAgentExecutor:
    def __init__(self, agent: Any, name: str = "a2a-agent"):
        self._agent = agent
        self._name = name
        self._executor = self._create_executor()  # 创建动态子类实例

    def _create_executor(self) -> Any:
        from a2a.server.agent_execution import AgentExecutor as _AE

        owner = self  # 闭包引用

        class _Inner(_AE):
            async def execute(self, context, event_queue):
                await owner._execute_impl(context, event_queue)

            async def cancel(self, context, event_queue):
                await owner._cancel_impl(context, event_queue)

        return _Inner()
```

关键点：
- 在运行时动态创建 `_Inner` 子类，继承自 `a2a-sdk` 的 `AgentExecutor`
- 通过闭包 `owner = self` 将方法委托给 `A2AAgentExecutor` 实例
- 实现 `execute()` 和 `cancel()` 两个核心接口

## 执行流程

当远程请求到达时，`_execute_impl` 方法处理完整流程：

```python
async def _execute_impl(self, context, event_queue):
    # 1. 提取用户消息
    msg = context.message
    user_text = self._extract_text(msg)

    # 2. 提交状态
    await event_queue.enqueue_event(Task(id=..., status=SUBMITTED))

    try:
        # 3. 调用 Agent（优先异步 arun，回退同步 run）
        if hasattr(self._agent, "arun"):
            response = await self._agent.arun(user_text)
        elif hasattr(self._agent, "run"):
            loop = asyncio.get_event_loop()
            response = await loop.run_in_executor(None, self._agent.run, user_text)
    except Exception as e:
        response = f"执行失败: {e}"

    # 4. 发送结果
    await event_queue.enqueue_event(Task(id=..., status=WORKING))
    await event_queue.enqueue_event(new_agent_text_message(response))
    await event_queue.enqueue_event(Task(id=..., status=COMPLETED))
```

**状态流转**: `SUBMITTED → WORKING → COMPLETED`

## 支持的 Agent 类型

只要 Agent 实现了 `run(text: str) -> str` 或 `arun(text: str) -> str` 方法，就可以被 A2AAgentExecutor 包装：

```python
# 同步 Agent
class MyAgent:
    def run(self, text: str) -> str:
        return f"处理: {text}"

# 异步 Agent
class MyAsyncAgent:
    async def arun(self, text: str) -> str:
        await asyncio.sleep(1)
        return f"异步处理: {text}"
```

---

# A2AServer — 启动服务器

> 代码位置: `hello_agents/protocols/a2a/implementation.py :131-193`

`A2AServer` 将包装后的 Agent 暴露为 HTTP 服务，使其他智能体可以通过 A2A 协议远程调用。

## 快速启动

```python
from hello_agents.protocols.a2a import A2AServer

# 创建服务器
server = A2AServer(
    agent=my_agent,
    name="文档助手",
    description="一个帮助处理文档的智能体",
    url="http://localhost:9999",
)

# 启动（阻塞）
server.run(host="0.0.0.0", port=9999)
# 输出:
# 🤝 A2A 服务器: 文档助手 → http://0.0.0.0:9999
#    Agent Card: http://0.0.0.0:9999/.well-known/agent.json
```

## 构建过程详解

`build_app()` 方法构建 ASGI 应用：

```python
def build_app(self) -> Any:
    from starlette.applications import Starlette
    from a2a.server.routes import create_agent_card_routes, create_jsonrpc_routes
    from a2a.server.request_handlers import DefaultRequestHandler
    from a2a.server.tasks import InMemoryTaskStore
    from a2a.types import AgentCard

    # 1. 创建 AgentExecutor 包装
    executor = A2AAgentExecutor(self._agent, name=self._name)

    # 2. 创建 AgentCard（描述信息）
    card = AgentCard(
        name=self._name,
        description=self._description,
    )

    # 3. 创建请求处理器（含内存任务存储）
    handler = DefaultRequestHandler(
        agent_executor=executor.inner,
        task_store=InMemoryTaskStore(),
        agent_card=card,
    )

    # 4. 注册路由
    routes = []
    routes.extend(create_agent_card_routes(card))     # GET /.well-known/agent.json
    routes.extend(create_jsonrpc_routes(handler))     # POST / (JSON-RPC)

    return Starlette(routes=routes)
```

### 暴露的端点

| 端点 | 方法 | 说明 |
|------|------|------|
| `/.well-known/agent.json` | GET | Agent Card — 发现 Agent 信息 |
| `/` | POST | JSON-RPC — 发送任务请求 |

### Agent Card 示例

```json
{
    "name": "文档助手",
    "description": "一个帮助处理文档的智能体",
    "capabilities": {},
    "skills": []
}
```

## 完整参数

```python
A2AServer(
    agent=my_agent,                    # 要暴露的 Agent
    name="A2A Agent",                  # Agent 名称（默认）
    description="",                    # Agent 描述
    url="http://localhost:9999",       # 服务地址
    skills=None,                       # 技能列表（可选）
)
```

## 技能声明

可以在启动时声明 Agent 支持的"技能"，方便其他智能体发现能力：

```python
server = A2AServer(
    agent=calculator_agent,
    name="计算器",
    skills=[
        {"id": "arithmetic", "name": "算术运算", "description": "执行加减乘除运算"},
        {"id": "statistics", "name": "统计分析", "description": "计算均值、方差等统计量"},
    ],
)
```

---

# A2ATool — 调用远程 Agent

> 代码位置: `hello_agents/tools/builtin/protocol_tools.py`

`A2ATool` 是连接到远程 A2A Agent 的客户端工具，可以在其他 Agent 的 ToolRegistry 中注册，让智能体能够调用其他智能体。

## 创建和使用

```python
from hello_agents.tools import A2ATool

tool = A2ATool()

# 发送消息给远程 Agent
result = tool.run({
    "action": "send_message",
    "url": "http://localhost:9999",
    "message": "你好，请帮我计算 1+1",
})
print(result)

# 获取远程 Agent 的卡片信息
card = tool.run({
    "action": "get_agent_card",
    "url": "http://localhost:9999",
})
print(card)

# 列出远程 Agent 的技能
skills = tool.run({
    "action": "list_skills",
    "url": "http://localhost:9999",
})
```

## 三种操作

### 1. send_message — 发送消息

核心操作，发送消息给远程 Agent 并获取回复：

```python
result = tool.run({
    "action": "send_message",
    "url": "http://localhost:9999",
    "message": "请帮我分析这段文本的情感倾向",
})
```

**内部流程**：
```
A2ATool._send_message()
  │
  ├─ 1. 建立 A2AClient 连接（通过 Agent Card URL 发现）
  │     httpx.AsyncClient → A2AClient.get_client_from_agent_card_url()
  │
  ├─ 2. 构建 TaskSendParams 请求
  │     TaskSendParams(
  │       input=TaskInput(
  │         message=MessageData(role="user", parts=[Part(type="text", text=...)])
  │       )
  │     )
  │
  ├─ 3. 发送消息
  │     client.send_message(req)
  │
  └─ 4. 解析回复
        resp.result.message.content[].text
```

### 2. get_agent_card — 获取 Agent 信息

获取远程 Agent 的元数据卡片：

```python
card = tool.run({"action": "get_agent_card", "url": "http://localhost:9999"})
# 返回:
# 📇 Agent Card:
#   name: 文档助手
#   description: 一个帮助处理文档的智能体
#   技能 (2):
#     · 摘要生成: 对输入文本生成摘要
#     · 关键词提取: 提取文本中的关键信息
```

### 3. list_skills — 列出技能

快捷操作，只返回技能列表：

```python
skills = tool.run({"action": "list_skills", "url": "http://localhost:9999"})
```

## Async-Sync 桥接

A2ATool 运行在同步环境中（Agent 是同步调用），但 A2A 客户端是异步的。为此，它使用 **daemon 线程 + 独立事件循环** 模式：

```python
def _ensure_loop(self):
    self._loop = asyncio.new_event_loop()
    self._loop_thread = threading.Thread(
        target=lambda: (asyncio.set_event_loop(self._loop), self._loop.run_forever()),
        daemon=True,
    )
    self._loop_thread.start()
    return self._loop

def _run_async(self, coro, timeout=60):
    loop = self._ensure_loop()
    return asyncio.run_coroutine_threadsafe(coro, loop).result(timeout=timeout)
```

这种设计兼容 Jupyter、FastAPI 等已有事件循环的环境，每个 `A2ATool` 实例拥有独立的事件循环。

---

# 完整示例：从服务端到客户端

## 场景：构建一个多智能体协作系统

假设我们有两个智能体：
1. **翻译助手** — 负责中英文翻译
2. **主控 Agent** — 用户直接交互的 Agent，需要时调用翻译助手

### 第一步：启动翻译助手 A2A 服务器

```python
# translator_server.py
"""翻译助手 — 以 A2A 服务器方式暴露"""
from hello_agents.protocols.a2a import A2AServer

class TranslatorAgent:
    """简单的翻译智能体"""
    name = "translator"

    def run(self, text: str) -> str:
        # 这里简化处理，实际可以调用翻译 API 或 LLM
        if "翻译" in text or "translate" in text:
            return f"[翻译结果]: {text} (已翻译)"
        return f"[翻译助手] 收到: {text}"

# 启动 A2A 服务器
server = A2AServer(
    agent=TranslatorAgent(),
    name="翻译助手",
    description="专业的中英文翻译智能体",
    skills=[{"id": "translate", "name": "翻译", "description": "中英文互译"}],
)
print("🚀 翻译助手已启动...")
server.run(host="0.0.0.0", port=9998)
```

### 第二步：创建主控 Agent，集成 A2ATool

```python
# main_agent.py
"""主控 Agent — 集成 A2ATool 调用远程翻译助手"""
from hello_agents import HelloAgentsLLM
from hello_agents.agents import ReActAgent
from hello_agents.tools import A2ATool

# 1. 创建 A2ATool，连接翻译助手
a2a_tool = A2ATool(default_url="http://localhost:9998")

# 2. 测试连接
card = a2a_tool.run({"action": "get_agent_card"})
print(f"✅ 已发现翻译助手: {card}")

# 3. 创建 ReActAgent 并注册 A2ATool
llm = HelloAgentsLLM()
agent = ReActAgent(name="主控助手", llm=llm)
agent.add_tool(a2a_tool)

# 4. 运行 — 当用户需要翻译时，LLM 会自动选择 A2ATool
response = agent.run("请帮我翻译 'Hello, world' 成中文")
print(response)
# ReAct 循环: Thought → Action(A2ATool) → Observation → Finish
```

### 第三步：完整的多智能体对话

```python
# 用户可以直接请求调用远程 Agent
agent.run("帮我连接到翻译助手，发送：今天天气真好")

# 或者让主控 Agent 自主判断是否需要调用翻译助手
agent.run("我有一段英文需要翻译，你能帮我处理吗？")
# Agent 内部: 思考后决定调用 A2ATool → send_message → 获取翻译结果
```

## 参数配置

A2ATool 支持默认 URL 减少重复参数：

```python
# 方式 A：在构造函数中指定默认 URL
tool = A2ATool(default_url="http://localhost:9998")
result = tool.run({"action": "send_message", "message": "你好"})  # 自动使用默认 URL

# 方式 B：每次调用指定 URL（覆盖默认）
tool.run({"action": "send_message", "url": "http://other-server:9997", "message": "你好"})

# 方式 C：不传 URL 会报错
tool.run({"action": "send_message", "message": "你好"})
# ❌ 需要 url 参数
```

## 获取参数定义（供 LLM 使用）

```python
params = tool.get_parameters()
# 返回 ToolParameter 列表:
#   name="action", type="string", description="操作: send_message / get_agent_card / list_skills"
#   name="url",    type="string", description="目标 Agent URL" (可选)
#   name="message",type="string", description="消息内容(send_message需要)" (可选)
```

---

# 在智能体中使用 A2ATool

## 注册到 ToolRegistry

A2ATool 可以像其他任何工具一样注册到智能体的 ToolRegistry 中：

```python
from hello_agents.tools import ToolRegistry
from hello_agents.tools import A2ATool

registry = ToolRegistry()
registry.register_tool(A2ATool(default_url="http://localhost:9998"))

agent = ReActAgent(name="多智能体协调器", llm=llm, tool_registry=registry)
```

## Agent 如何选择 A2ATool

Agent 不区分 A2ATool 和其他工具，所有工具在 ToolRegistry 中平等注册。LLM 根据工具描述和用户问题自主选择：

| 用户问题 | LLM 选择 | 原因 |
|---------|---------|------|
| "计算 1+2" | `calculator` | 描述匹配数学计算 |
| "帮我问问翻译助手" | `a2a` | 描述匹配 A2A 远程调用 |
| "把这段话发给另一个 Agent" | `a2a` | 需要跨 Agent 通信 |

## 与多个 A2A 服务器协作

可以注册多个 A2ATool 实例连接不同的远程 Agent：

```python
# 连接两个不同的 A2A 服务器
translator_tool = A2ATool(default_url="http://localhost:9998", name="translator_a2a")
analyst_tool = A2ATool(default_url="http://localhost:9997", name="analyst_a2a")

agent.add_tool(translator_tool)
agent.add_tool(analyst_tool)

# Agent 会自动根据问题选择合适的远程 Agent
agent.run("帮我翻译这段文字")       # → 选择 translator_a2a
agent.run("分析这份数据报告")       # → 选择 analyst_a2a
```

---

# 架构示意

## 服务端架构

```
外部 A2A 客户端         A2AServer / Starlette          A2AAgentExecutor         Agent
     │                        │                              │                    │
     │  POST / (JSON-RPC)     │                              │                    │
     ├───────────────────────▶│                              │                    │
     │                        │  create_agent_card_routes()   │                    │
     │  GET /.well-known/     │                              │                    │
     │  agent.json            │                              │                    │
     ├───────────────────────▶│                              │                    │
     │                        │                              │                    │
     │                        │  DefaultRequestHandler        │                    │
     │                        │    ├─ executor.execute()     │                    │
     │                        │    └─ task_store.xxx()       │                    │
     │                        │         │                    │                    │
     │                        │         └───────────────────▶│                    │
     │                        │                              │  _execute_impl()    │
     │                        │                              │    ├─ extract msg   │
     │                        │                              │    ├─ agent.run()  │
     │                        │                              │    └─ return result  │
     │                        │                              │         │           │
     │                        │                              │         ▼           │
     │                        │                              │    agent.run(text)  │
     │                        │                              │         │           │
     │                        │                              │         ▼           │
     │                        │                              │   响应文本          │
     │                        │◀─────────────────────────────│                    │
     │◀───────────────────────│                              │                    │
```

## 客户端架构

```
Agent (同步)              A2ATool (同步桥)              A2AClient (异步)        远程 A2A 服务
     │                        │                              │                    │
     │ tool.run(params)       │                              │                    │
     ├───────────────────────▶│                              │                    │
     │                        │  _send_message()              │                    │
     │                        │  _run_async(coro)             │                    │
     │                        │    ├─ 专用 daemon 线程        │                    │
     │                        │    └─ 独立事件循环            │                    │
     │                        │         │                    │                    │
     │                        │         └───────────────────▶│                    │
     │                        │                              │  HTTP POST         │
     │                        │                              ├───────────────────▶│
     │                        │                              │◀───────────────────┤
     │                        │◀─────────────────────────────│                    │
     │◀───────────────────────│                              │                    │
     │  result text           │                              │                    │
```

---

# 与 MCP 的对比

| 维度 | A2A | MCP |
|------|-----|-----|
| **通信方向** | 智能体 ↔ 智能体（对等） | 智能体 → 工具（主从） |
| **拓扑** | P2P 网状 | Host-Client-Server |
| **协议基础** | JSON-RPC + HTTP | JSON-RPC + stdio/SSE |
| **核心关注** | 任务协商、协作 | 工具调用、上下文共享 |
| **发现机制** | Agent Card (`/.well-known/agent.json`) | `list_tools()` 接口 |
| **SDK** | `a2a-sdk` (Google) | `fastmcp` (Anthropic) |
| **状态管理** | 任务生命周期（SUBMITTED→WORKING→COMPLETED） | 无状态调用 |

## 何时使用 A2A

- 需要 **多个智能体协作** 完成复杂任务时
- 希望智能体之间 **点对点直接通信**，不经过中央协调器
- 构建 **去中心化的多智能体系统**
- 需要 **任务委托** — 一个 Agent 把子任务交给另一个 Agent

---

# 最佳实践

## 1. 服务端稳定性

```python
# 使用 try-except 包装 Agent 执行逻辑，避免未处理异常导致连接中断
class RobustAgent:
    def run(self, text):
        try:
            # 核心逻辑
            return self._process(text)
        except Exception as e:
            return f"处理失败: {e}"  # 返回错误信息而非抛出

server = A2AServer(RobustAgent(), name="稳定助手")
```

## 2. 超时处理

A2ATool 默认 60 秒超时，对于耗时任务可适当调整：

```python
# 在代码层可修改超时
import asyncio
tool._run_async(coro, timeout=120)  # 设置 120 秒超时
```

## 3. 服务发现集成

可以将 A2A 与 ANP 配合使用 — 通过 ANP 注册 A2A 服务，让其他智能体动态发现：

```python
# 启动 A2A 服务器后，在 ANP 中注册
from hello_agents.protocols.anp import ANPTool

anp = ANPTool()
anp.run({
    "action": "register_service",
    "service_id": "translator",
    "service_type": "a2a",
    "endpoint": "http://localhost:9998",
})

# 其他 Agent 通过 ANP 发现服务后，用 A2ATool 连接
services = anp.run({"action": "discover_services", "service_type": "a2a"})
```

## 4. 异步优先

如果 Agent 实现了 `arun()` 异步方法，A2AAgentExecutor 会优先使用异步调用，获得更好的性能：

```python
class AsyncAgent:
    async def arun(self, text: str) -> str:
        # 异步处理，不阻塞事件循环
        result = await some_async_api(text)
        return result
```

---

# 相关文件索引

| 文件 | 作用 |
|------|------|
| `protocols/a2a/__init__.py` | A2A 模块导出 |
| `protocols/a2a/implementation.py` | A2A 核心实现（Executor / Server / Tool） |
| `tools/builtin/protocol_tools.py` | 协议工具包装器统一入口 |
| `tools/registry.py` | ToolRegistry 工具注册中心 |

## 参考

- [Google A2A 协议官方文档](https://google.github.io/a2a/)
- [a2a-sdk PyPI](https://pypi.org/project/a2a-sdk/)
