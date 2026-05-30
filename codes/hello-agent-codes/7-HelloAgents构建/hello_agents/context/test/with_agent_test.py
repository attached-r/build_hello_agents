"""
Agent + ContextBuilder 集成测试（使用底层 API）

把 Tool 层替换为直接调用 MemoryManager / RAGPipeline，
展示 ContextBuilder 如何与 Agent 搭配工作。

改动要点:
  MemoryTool → MemoryManager (save/search 直接调用)
  RAGTool    → RAGPipeline (query 直接调用，需 Qdrant 服务)
  llm.invoke → llm.think   (HelloAgentsLLM 的正确方法名)
"""

import os
import sys
from datetime import datetime

# ── 路径引导 ──────────────────────────────────────────
_BASE = os.path.abspath(__file__)
while not os.path.isdir(os.path.join(os.path.dirname(_BASE), 'hello_agents')):
    _BASE = os.path.dirname(_BASE)
    if os.path.dirname(_BASE) == _BASE:
        break
_PROJECT_ROOT = os.path.dirname(_BASE)
if _PROJECT_ROOT not in sys.path:
    sys.path.insert(0, _PROJECT_ROOT)

from hello_agents import SimpleAgent, HelloAgentsLLM
from hello_agents.context import ContextBuilder, ContextConfig
from hello_agents.memory.manager import MemoryManager
from hello_agents.memory.base import MemoryConfig
from hello_agents.core.message import Message


class ContextAwareAgent(SimpleAgent):
    """具有上下文感知能力的 Agent（底层 API 版）"""

    def __init__(self, name: str, llm: HelloAgentsLLM, **kwargs):
        super().__init__(name=name, llm=llm, system_prompt=kwargs.get("system_prompt", ""))

        # ── 使用 MemoryManager 而非 MemoryTool ──────────────
        mem_config = MemoryConfig(
            episodic_db_type="mysql",  
            episodic_db_path=":memory:",  # 内存模式，用完即弃
            semantic_enabled=False,
            perceptual_enabled=False,
        )
        self.memory = MemoryManager(
            config=mem_config,
            user_id=kwargs.get("user_id", "default"),
        )

        # ── 尝试初始化 RAGPipeline（需要 Qdrant 服务） ──────
        self.rag = None
        try:
            from hello_agents.memory.rag.pipeline import RAGPipeline
            self.rag = RAGPipeline(
                llm=llm,
                collection_name="data_science_kb",
            )
        except Exception as e:
            print(f"⏭️ RAGPipeline 不可用（跳过）: {e}")

        # ── ContextBuilder 接收底层实例 ─────────────────────
        self.context_builder = ContextBuilder(
            memory=self.memory,
            rag=self.rag,
            config=ContextConfig(max_tokens=4000),
        )

        self.conversation_history: list[Message] = []

    def run(self, user_input: str) -> str:
        """运行 Agent，自动构建优化的上下文"""

        # 1. 使用 ContextBuilder 构建优化的上下文
        optimized_context = self.context_builder.build(
            user_query=user_input,
            conversation_history=self.conversation_history,
            system_instructions=self.system_prompt,
        )

        # 2. 使用优化后的上下文调用 LLM
        messages = [
            {"role": "system", "content": optimized_context},
            {"role": "user", "content": user_input},
        ]
        response = self.llm.think(messages)
        if response is None:
            response = "(LLM 返回空，请检查 API 配置)"

        # 3. 更新对话历史
        self.conversation_history.append(
            Message(content=user_input, role="user", timestamp=datetime.now())
        )
        self.conversation_history.append(
            Message(content=response, role="assistant", timestamp=datetime.now())
        )

        # 4. 将重要交互记录到记忆系统
        self.memory.save(
            content=f"Q: {user_input}\nA: {response[:200]}...",
            memory_type="episodic",
            importance=0.6,
        )

        return response


# ═══════════════════════════════════════════════════════════════
# 使用示例
# ═══════════════════════════════════════════════════════════════
if __name__ == "__main__":
    from dotenv import load_dotenv
    load_dotenv()

    agent = ContextAwareAgent(
        name="数据分析顾问",
        llm=HelloAgentsLLM(),
        system_prompt="你是一位资深的 Python 数据工程顾问。",
        user_id="user123",
    )

    response = agent.run("如何优化 Pandas 的内存占用？")
    print(f"\n{'='*60}")
    print(f"最终回复:\n{response}")
