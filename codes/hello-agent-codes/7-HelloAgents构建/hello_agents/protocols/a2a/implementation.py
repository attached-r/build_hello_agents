"""
A2A (Agent-to-Agent) 协议封装 — 基于 a2a-sdk

提供:
  · A2AAgentExecutor — 包装 HelloAgents Agent 为 A2A 执行器
  · A2AServer        — 启动 A2A 服务器

A2ATool 已移至 hello_agents.tools.builtin.protocol_tools，作为内置工具使用。

依赖: pip install a2a-sdk httpx uvicorn

用法 (服务端):
    server = A2AServer(agent=my_agent, name="助手", port=9999)
    server.run()
"""

from __future__ import annotations

import asyncio
import logging
import os
import sys
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)

# ── 路径引导 ──────────────────────────────────────────────
_BASE = os.path.abspath(__file__)
while not os.path.isdir(os.path.join(os.path.dirname(_BASE), "hello_agents")):
    _BASE = os.path.dirname(_BASE)
    if os.path.dirname(_BASE) == _BASE:
        break
_PROJECT_ROOT = os.path.dirname(_BASE)
if _PROJECT_ROOT not in sys.path:
    sys.path.insert(0, _PROJECT_ROOT)


# ════════════════════════════════════════════════════════════
# A2AAgentExecutor — 将 Agent 包装为 A2A 执行器
# ════════════════════════════════════════════════════════════

class A2AAgentExecutor:
    """将 HelloAgents Agent 包装为 A2A AgentExecutor。

    通过动态子类方式实现 a2a.server.agent_execution.AgentExecutor 接口，
    桥接 A2A 协议层与业务 Agent。
    """

    def __init__(self, agent: Any, name: str = "a2a-agent"):
        self._agent = agent
        self._name = name
        self._executor = self._create_executor()

    @property
    def inner(self) -> Any:
        """底层的 AgentExecutor 实例，供 A2A 框架使用。"""
        return self._executor

    # ── 动态子类工厂 ──────────────────────────────────────

    def _create_executor(self) -> Any:
        """创建 AgentExecutor 子类实例，委托给当前对象。"""
        from a2a.server.agent_execution import AgentExecutor as _AE

        owner = self

        class _Inner(_AE):
            async def execute(self, context, event_queue):
                await owner._execute_impl(context, event_queue)
            async def cancel(self, context, event_queue):
                await owner._cancel_impl(context, event_queue)

        return _Inner()

    # ── 接口实现 ───────────────────────────────────────────

    async def _execute_impl(
        self, context: Any, event_queue: Any
    ) -> None:
        """处理 A2A 请求 → 调用 Agent → 返回结果。"""
        from a2a.types import Task, TaskState
        from a2a.utils import new_agent_text_message

        # 提取用户消息
        msg = context.message
        user_text = ""
        if msg and hasattr(msg, "content"):
            for part in (getattr(msg, "content", None) or []):
                t = getattr(part, "text", None) or (part.get("text") if isinstance(part, dict) else None)
                if t:
                    user_text = t
                    break
        if not user_text:
            user_text = str(msg) if msg else ""

        # 生命周期
        await event_queue.enqueue_event(Task(id=context.task_id, status=TaskState.SUBMITTED))

        try:
            if hasattr(self._agent, "arun"):
                response = await self._agent.arun(user_text)
            elif hasattr(self._agent, "run"):
                loop = asyncio.get_event_loop()
                response = await loop.run_in_executor(None, self._agent.run, user_text)
            else:
                response = f"[{self._name}] Agent 未实现 run()"
        except Exception as e:
            logger.exception("A2A 执行失败")
            response = f"执行失败: {e}"

        await event_queue.enqueue_event(Task(id=context.task_id, status=TaskState.WORKING))
        await event_queue.enqueue_event(new_agent_text_message(response))
        await event_queue.enqueue_event(Task(id=context.task_id, status=TaskState.COMPLETED))

    async def _cancel_impl(self, context: Any, event_queue: Any) -> None:
        from a2a.types import Task, TaskState
        await event_queue.enqueue_event(Task(id=context.task_id, status=TaskState.CANCELED))

    def __repr__(self) -> str:
        return f"A2AAgentExecutor(name={self._name})"


# ════════════════════════════════════════════════════════════
# A2AServer — 启动 A2A 服务器
# ════════════════════════════════════════════════════════════

class A2AServer:
    """快速将 HelloAgents Agent 包装为 A2A 服务器。"""

    def __init__(
        self,
        agent: Any,
        name: str = "A2A Agent",
        description: str = "",
        url: str = "http://localhost:9999",
        skills: Optional[List[Dict[str, str]]] = None,
    ):
        self._agent = agent
        self._name = name
        self._description = description
        self._url = url
        self._skills_data = skills or []

    def build_app(self) -> Any:
        """构建 ASGI 应用。"""
        from starlette.applications import Starlette
        from a2a.server.routes import create_agent_card_routes, create_jsonrpc_routes
        from a2a.server.request_handlers import DefaultRequestHandler
        from a2a.server.tasks import InMemoryTaskStore
        from a2a.types import AgentCard, AgentSkill

        executor = A2AAgentExecutor(self._agent, name=self._name)

        # 极简 AgentCard（只填最必要字段）
        skills = []
        for s in self._skills_data:
            try:
                skills.append(AgentSkill(
                    id=s.get("id", "default"),
                    name=s.get("name", "skill"),
                    description=s.get("description", ""),
                ))
            except Exception:
                pass

        card = AgentCard(
            name=self._name,
            description=self._description,
        )

        handler = DefaultRequestHandler(
            agent_executor=executor.inner,
            task_store=InMemoryTaskStore(),
            agent_card=card,
        )

        routes = []
        routes.extend(create_agent_card_routes(card))
        routes.extend(create_jsonrpc_routes(handler, rpc_url="/"))
        return Starlette(routes=routes)

    def run(self, host: str = "0.0.0.0", port: int = 9999, log_level: str = "info") -> None:
        """启动服务器（阻塞）。"""
        import uvicorn
        app = self.build_app()
        self._url = f"http://{host}:{port}"
        print(f"\n🤝 A2A 服务器: {self._name} → http://{host}:{port}")
        print(f"   Agent Card: http://{host}:{port}/.well-known/agent.json\n")
        uvicorn.run(app, host=host, port=port, log_level=log_level)


# ════════════════════════════════════════════════════════════
# 自测
# ════════════════════════════════════════════════════════════

if __name__ == "__main__":
    print("=" * 50)
    print("A2A 模块自测")
    print("=" * 50)

    # 检查 a2a-sdk
    try:
        import importlib
        importlib.import_module("a2a")
        print("✅ a2a-sdk 已安装")
    except ImportError:
        print("❌ 请安装: pip install a2a-sdk httpx uvicorn")
        sys.exit(1)

    # 测试 A2AAgentExecutor
    class _Echo:
        name = "echo"
        def run(self, t): return f"回声: {t}"

    exe = A2AAgentExecutor(_Echo(), "echo")
    print(f"✅ A2AAgentExecutor: {exe}")

    # 测试 A2AServer 构建
    srv = A2AServer(_Echo(), "EchoAgent", skills=[{"id": "echo", "name": "回声", "description": "返回输入"}])
    app = srv.build_app()
    print(f"✅ A2AServer: app={type(app).__name__}")

    print("\n" + "=" * 50)
    print("全部通过 ✅")
    print("=" * 50)

