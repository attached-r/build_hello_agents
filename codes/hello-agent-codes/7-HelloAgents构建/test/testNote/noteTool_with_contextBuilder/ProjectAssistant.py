"""
ProjectAssistant — 长期项目助手，集成 NoteTool + ContextBuilder

演示如何将 NoteTool 和 ContextBuilder 组合使用：
  1. 用户输入 → 2. 检索相关笔记 → 3. 构建结构化上下文
  → 4. 调用 LLM → 5. 可选保存为笔记 → 6. 更新对话历史
"""
import sys
import os
# 将项目根目录加入模块搜索路径
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../../.."))

from typing import List, Dict, Optional
from datetime import datetime

from hello_agents import SimpleAgent, HelloAgentsLLM
from hello_agents.context import ContextBuilder, ContextConfig, ContextPacket
from hello_agents.tools import NoteTool
from hello_agents.memory.manager import MemoryManager
from hello_agents.memory.rag.pipeline import RAGPipeline
from hello_agents.core.message import Message

class ProjectAssistant(SimpleAgent):
    """长期项目助手，集成 NoteTool 和 ContextBuilder"""

    def __init__(
        self,
        name: str,
        project_name: str,
        llm: Optional[HelloAgentsLLM] = None,
        **kwargs,
    ):
        super().__init__(name=name, llm=llm or HelloAgentsLLM(), **kwargs)

        self.project_name = project_name

        # ── 1. 初始化记忆系统 ────────────────────────────────────────────
        self.memory_manager = MemoryManager(user_id=project_name)

        # ── 2. 初始化 RAG 知识库（使用当前 LLM 实例） ────────────────────
        self.rag_pipeline = RAGPipeline(
            llm=self.llm,
            collection_name=f"{project_name}_kb",
        )

        # ── 3. 初始化笔记工具 ────────────────────────────────────────────
        self.note_tool = NoteTool(workspace=f"./{project_name}_notes")

        # ── 4. 初始化上下文构建器（GSSC 流水线） ─────────────────────────
        #     ContextBuilder 直接接收 MemoryManager 和 RAGPipeline，
        #     而非 MemoryTool / RAGTool（工具是给 Agent 调用的，构建器
        #     需要的是底层检索接口）
        self.context_builder = ContextBuilder(
            memory=self.memory_manager,
            rag=self.rag_pipeline,
            config=ContextConfig(max_tokens=4000),
        )

        # ── 5. 对话历史 ──────────────────────────────────────────────────
        self.conversation_history: List[Message] = []

    # ══════════════════════════════════════════════════════════════════════
    # 主入口
    # ══════════════════════════════════════════════════════════════════════

    def run(self, user_input: str, note_as_action: bool = False) -> str:
        """运行助手，自动集成笔记上下文

        Args:
            user_input: 用户输入
            note_as_action: 是否将本次交互自动保存为笔记

        Returns:
            str: LLM 回复
        """
        # 1. 从 NoteTool 检索相关笔记
        relevant_notes = self._retrieve_relevant_notes(user_input)

        # 2. 将笔记转换为 ContextPacket（GSSC 自定义信息包）
        note_packets = self._notes_to_packets(relevant_notes)

        # 3. 构建优化的结构化上下文（GSSC 流水线）
        context = self.context_builder.build(
            user_query=user_input,
            conversation_history=self.conversation_history,
            system_instructions=self._build_system_instructions(),
            custom_packets=note_packets,
        )

        # 4. 调用 LLM
        messages = [
            {"role": "system", "content": context},
            {"role": "user", "content": user_input},
        ]
        response = self.llm.think(messages) or ""

        # 5. 如需自动记录，将交互保存为笔记
        if note_as_action:
            self._save_as_note(user_input, response)

        # 6. 更新对话历史
        self._update_history(user_input, response)

        return response

    # ══════════════════════════════════════════════════════════════════════
    # 笔记检索与转换
    # ══════════════════════════════════════════════════════════════════════

    def _retrieve_relevant_notes(self, query: str, limit: int = 3) -> List[Dict]:
        """检索与当前问题相关的笔记

        策略：优先取出 blocker 类型的笔记，再补充全文搜索结果。
        """
        notes: List[Dict] = []

        try:
            # 优先检索 blocker（阻塞问题）
            blockers = self.note_tool.run({
                "action": "list",
                "note_type": "blocker",
                "limit": 2,
            })
            if isinstance(blockers, list):
                notes.extend(blockers)

            # 通用全文搜索
            search_results = self.note_tool.run({
                "action": "search",
                "query": query,
                "limit": limit,
            })
            if isinstance(search_results, list):
                # 合并结果，按 note_id 去重
                seen = {n.get("note_id") for n in notes if isinstance(n, dict)}
                for note in search_results:
                    if isinstance(note, dict) and note.get("note_id") not in seen:
                        seen.add(note["note_id"])
                        notes.append(note)

        except Exception as e:
            print(f"[WARNING] 笔记检索失败: {e}")

        return notes[:limit]

    def _notes_to_packets(self, notes: List[Dict]) -> List[ContextPacket]:
        """将笔记列表转换为 ContextPacket，供 ContextBuilder 消费"""
        packets: List[ContextPacket] = []

        for note in notes:
            if not isinstance(note, dict):
                continue

            title = note.get("title", "无标题")
            content = note.get("content", "")
            note_content = f"[笔记:{title}]\n{content}"

            # 解析时间戳
            updated_at_str = note.get("updated_at")
            try:
                timestamp = datetime.fromisoformat(updated_at_str) if updated_at_str else datetime.now()
            except (ValueError, TypeError):
                timestamp = datetime.now()

            packets.append(ContextPacket(
                content=note_content,
                timestamp=timestamp,
                token_count=max(1, len(note_content) // 4),
                relevance_score=0.75,
                metadata={
                    "type": "note",
                    "note_type": note.get("type"),
                    "note_id": note.get("note_id"),
                },
            ))

        return packets

    # ══════════════════════════════════════════════════════════════════════
    # 自动保存笔记
    # ══════════════════════════════════════════════════════════════════════

    def _save_as_note(self, user_input: str, response: str):
        """将用户交互自动保存为笔记"""
        try:
            # 根据输入内容判断笔记类型
            if "问题" in user_input or "阻塞" in user_input:
                note_type = "blocker"
            elif "计划" in user_input or "下一步" in user_input:
                note_type = "action"
            else:
                note_type = "conclusion"

            self.note_tool.run({
                "action": "create",
                "title": f"{user_input[:30]}...",
                "content": f"## 问题\n{user_input}\n\n## 分析\n{response}",
                "note_type": note_type,
                "tags": [self.project_name, "auto_generated"],
            })
            print(f"📝 已自动保存为 {note_type} 类型笔记")

        except Exception as e:
            print(f"[WARNING] 保存笔记失败: {e}")

    # ══════════════════════════════════════════════════════════════════════
    # 系统指令 & 对话历史
    # ══════════════════════════════════════════════════════════════════════

    def _build_system_instructions(self) -> str:
        """构建系统角色指令"""
        return f"""你是 {self.project_name} 项目的长期助手。

你的职责:
1. 基于历史笔记提供连贯的建议
2. 追踪项目进展和待解决问题
3. 在回答时引用相关的历史笔记
4. 提供具体、可操作的下一步建议

注意:
- 优先关注标记为 blocker 的问题
- 在建议中说明依据来源（笔记、记忆或知识库）
- 保持对项目整体进度的认识"""

    def _update_history(self, user_input: str, response: str):
        """更新对话历史，并限制长度"""
        self.conversation_history.append(
            Message(content=user_input, role="user")
        )
        self.conversation_history.append(
            Message(content=response, role="assistant")
        )

        # 只保留最近 10 条（5 轮对话）
        if len(self.conversation_history) > 10:
            self.conversation_history = self.conversation_history[-10:]


# ═══════════════════════════════════════════════════════════════════════════
# 使用示例
# ═══════════════════════════════════════════════════════════════════════════
if __name__ == "__main__":
    assistant = ProjectAssistant(
        name="项目助手",
        project_name="data_pipeline_refactoring",
    )

    # 第一次交互：记录项目状态
    print("=" * 50)
    response = assistant.run(
        "我们已经完成了数据模型层的重构，测试覆盖率达到85%。"
        "下一步计划重构业务逻辑层。",
        note_as_action=True,
    )
    print(f"🤖: {response}\n")

    # 第二次交互：提出问题
    print("=" * 50)
    response = assistant.run(
        "在重构业务逻辑层时，我遇到了依赖版本冲突的问题，该如何解决?"
    )
    

    # 查看笔记摘要
    print("=" * 50)
    summary = assistant.note_tool.run({"action": "summary"})
    print(f"📊 笔记摘要:\n{summary}")
