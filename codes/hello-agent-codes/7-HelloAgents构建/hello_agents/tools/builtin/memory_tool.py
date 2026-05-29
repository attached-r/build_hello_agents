"""
记忆工具 — 将记忆系统封装为 Tool，供 Agent 调用。

支持的操作:
  add          添加记忆
  search       检索记忆
  summary      记忆摘要
  stats        统计信息
  update       更新记忆
  remove       删除记忆
  forget       执行遗忘策略
  consolidate  执行记忆整合
  clear_all    清空所有
"""

from typing import Any

from ...tools.base import Tool, ToolParameter
from ...memory.manager import MemoryManager


class MemoryTool(Tool):
    """记忆管理工具 — Agent 通过它操作记忆"""

    def __init__(self, memory: MemoryManager):
        super().__init__(
            name="memory",
            description=(
                "一个记忆管理工具。用于存储和检索信息，"
                "支持工作记忆、情景记忆、语义记忆和感知记忆四种类型。"
            ),
        )
        self.memory = memory

    def run(self, parameters: dict[str, Any]) -> str:
        action = parameters.get("action", "search")
        handler = getattr(self, f"_{action}", None)
        if handler is None:
            return (
                f"未知操作: {action}，支持: "
                f"add/search/summary/stats/update/remove/"
                f"forget/consolidate/clear_all"
            )
        return handler(**parameters)

    def get_parameters(self) -> list[ToolParameter]:
        return [
            ToolParameter(
                name="action", type="string",
                description="操作类型: add/search/summary/stats/update/remove/forget/consolidate/clear_all",
            ),
            ToolParameter(
                name="content", type="string",
                description="记忆内容（add 操作需要）",
                required=False,
            ),
            ToolParameter(
                name="memory_type", type="string",
                description="记忆类型: working/episodic/semantic/perceptual",
                required=False,
            ),
            ToolParameter(
                name="query", type="string",
                description="检索内容（search 操作需要）",
                required=False,
            ),
            ToolParameter(
                name="limit", type="integer",
                description="检索返回数量",
                required=False,
            ),
            ToolParameter(
                name="importance", type="number",
                description="重要性 0-1（add 操作可选）",
                required=False,
            ),
            ToolParameter(
                name="memory_id", type="string",
                description="记忆 ID（update/remove 操作需要）",
                required=False,
            ),
            ToolParameter(
                name="strategy", type="string",
                description="遗忘策略: importance_based/time_based/capacity_based",
                required=False,
            ),
            ToolParameter(
                name="threshold", type="number",
                description="遗忘/整合阈值",
                required=False,
            ),
        ]

    # ── 操作实现 ──────────────────────────────────────────────

    def _add(self, **params) -> str:
        content = params.get("content", "")
        if not content:
            return "❌ 记忆内容不能为空"

        memory_type = params.get("memory_type", "working")
        importance = params.get("importance", 0.5)

        try:
            mid = self.memory.save(
                content=content,
                memory_type=memory_type,
                importance=float(importance),
            )
            return f"✅ 已添加 {memory_type} 记忆 (ID: {mid})"
        except NotImplementedError:
            return f"❌ {memory_type} 记忆类型尚未实现"
        except Exception as e:
            return f"❌ 添加失败: {e}"

    def _search(self, **params) -> str:
        query = params.get("query", "")
        if not query:
            return "❌ 检索内容不能为空"

        memory_type = params.get("memory_type")
        limit = int(params.get("limit", 5))

        try:
            results = self.memory.search(query, memory_type=memory_type, limit=limit)
            if not results:
                return "💡 未找到相关记忆"

            lines = [f"🔍 找到 {len(results)} 条相关记忆:\n"]
            for i, item in enumerate(results):
                lines.append(
                    f"  [{i+1}] [{item.memory_type}] {item.content[:120]}...\n"
                    f"       重要性: {item.importance:.2f} | "
                    f"时间: {item.timestamp.strftime('%m-%d %H:%M')}\n"
                )
            return "\n".join(lines)
        except NotImplementedError:
            return f"❌ {memory_type} 记忆类型尚未实现"
        except Exception as e:
            return f"❌ 检索失败: {e}"

    def _summary(self, **params) -> str:
        return self.memory.summary()

    def _stats(self, **params) -> str:
        stats = self.memory.stats()
        lines = ["📊 记忆统计:\n"]
        for _type, info in stats.items():
            status = "✅" if info["enabled"] else "⏳"
            lines.append(f"  {status} {_type}: {info['count']} 条")
        return "\n".join(lines)

    def _update(self, **params) -> str:
        mid = params.get("memory_id", "")
        if not mid:
            return "❌ 记忆 ID 不能为空"

        updates = {}
        if "content" in params:
            updates["content"] = params["content"]
        if "importance" in params:
            updates["importance"] = float(params["importance"])

        if not updates:
            return "❌ 没有要更新的字段"

        memory_type = params.get("memory_type", "working")
        ok = self.memory.update(mid, memory_type=memory_type, **updates)
        return f"✅ 记忆已更新" if ok else f"❌ 未找到记忆 {mid}"

    def _remove(self, **params) -> str:
        mid = params.get("memory_id", "")
        if not mid:
            return "❌ 记忆 ID 不能为空"

        memory_type = params.get("memory_type", "working")
        ok = self.memory.delete(mid, memory_type=memory_type)
        return f"✅ 记忆已删除" if ok else f"❌ 未找到记忆 {mid}"

    def _forget(self, **params) -> str:
        strategy = params.get("strategy", "importance_based")
        try:
            self.memory.forget(strategy, **params)
            return f"✅ 已执行遗忘策略: {strategy}"
        except Exception as e:
            return f"❌ 遗忘失败: {e}"

    def _consolidate(self, **params) -> str:
        threshold = params.get("threshold")
        count = self.memory.consolidate(threshold=float(threshold) if threshold else None)
        return f"✅ 已整合 {count} 条记忆到情景记忆"

    def _clear_all(self, **params) -> str:
        """清空所有记忆"""
        memory_type = params.get("memory_type")
        if memory_type:
            store = self.memory._type_map.get(memory_type)
            if store:
                try:
                    n = store.clear()
                    return f"✅ 已清空 {memory_type} 记忆 ({n} 条)"
                except NotImplementedError:
                    return f"❌ {memory_type} 记忆类型尚未实现"
            return f"❌ 未知记忆类型: {memory_type}"

        total = 0
        for _type, store in self.memory._type_map.items():
            try:
                total += store.clear()
            except NotImplementedError:
                continue
        return f"✅ 已清空所有记忆 ({total} 条)"