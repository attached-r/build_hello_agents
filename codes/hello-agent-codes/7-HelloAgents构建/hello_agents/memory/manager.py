"""
记忆管理器 — 统一协调调度四种记忆类型。

Agent 通过 MemoryManager 操作所有记忆:
  save → search → get/update/delete → forget → consolidate → summary → stats
"""

from typing import Optional

from .base import MemoryItem, MemoryConfig
from .embedding import create_embedding, TFIDFEmbedding
from .types.working import WorkingMemory
from .types.episodic import EpisodicMemory
from .types.semantic import SemanticMemory
from .types.perceptual import PerceptualMemory


class MemoryManager:
    """记忆管理器 —— 统一入口"""

    def __init__(
        self,
        config: Optional[MemoryConfig] = None,
        user_id: str = "",
        session_id: str = "",
    ):
        self.config = config or MemoryConfig()
        self.user_id = user_id
        self.session_id = session_id

        # 嵌入服务
        emb = create_embedding(self.config.embedding_model)

        # 初始化四种记忆类型
        self.working = WorkingMemory(self.config, embedding=emb)
        self.episodic = EpisodicMemory(self.config, embedding=emb)
        self.semantic = SemanticMemory(self.config, embedding=emb)
        self.perceptual = PerceptualMemory(self.config, embedding=emb)

        # 类型映射
        self._type_map = {
            "working": self.working,
            "episodic": self.episodic,
            "semantic": self.semantic,
            "perceptual": self.perceptual,
        }

    # ── 核心操作 ──────────────────────────────────────────────

    def save(
        self,
        content: str,
        memory_type: str = "working",
        importance: float = 0.5,
        metadata: Optional[dict] = None,
        **kwargs,
    ) -> str:
        """添加记忆"""
        store = self._type_map.get(memory_type)
        if store is None:
            raise ValueError(f"未知记忆类型: {memory_type}")

        item = MemoryItem(
            content=content,
            memory_type=memory_type,
            user_id=kwargs.get("user_id", self.user_id),
            session_id=kwargs.get("session_id", self.session_id),
            importance=importance,
            metadata=metadata or {},
        )
        return store.add(item)

    def search(
        self,
        query: str,
        memory_type: Optional[str] = None,
        limit: int = 5,
        **kwargs,
    ) -> list[MemoryItem]:
        """检索记忆。不指定类型则跨类型搜索。"""
        if memory_type:
            store = self._type_map.get(memory_type)
            if store is None:
                raise ValueError(f"未知记忆类型: {memory_type}")
            return store.search(query, limit=limit, **kwargs)

        # 跨类型并行搜索
        results: list[MemoryItem] = []
        for _type, store in self._type_map.items():
            try:
                results.extend(store.search(query, limit=limit, **kwargs))
            except NotImplementedError:
                continue
        # 按 timestamp 降序排列
        results.sort(key=lambda x: x.timestamp, reverse=True)
        return results[:limit]

    def get(self, memory_id: str, memory_type: Optional[str] = None) -> Optional[MemoryItem]:
        """获取指定记忆"""
        if memory_type:
            return self._type_map[memory_type].get(memory_id)
        for store in self._type_map.values():
            try:
                item = store.get(memory_id)
                if item:
                    return item
            except NotImplementedError:
                continue
        return None

    def update(self, memory_id: str, memory_type: str = "working", **updates) -> bool:
        """更新记忆"""
        store = self._type_map.get(memory_type)
        if store is None:
            return False
        return store.update(memory_id, **updates)

    def delete(self, memory_id: str, memory_type: str = "working") -> bool:
        """删除记忆"""
        store = self._type_map.get(memory_type)
        if store is None:
            return False
        return store.delete(memory_id)

    # ── 遗忘策略 ──────────────────────────────────────────────

    def forget(self, strategy: str = "importance_based", **kwargs):
        """
        执行遗忘策略。

        Args:
            strategy: importance_based / time_based / capacity_based
        """
        if strategy == "importance_based":
            threshold = kwargs.get("threshold", self.config.forget_importance_threshold)
            self.working.forget_by_importance(threshold)
            self.episodic.forget_by_importance(threshold)
        elif strategy == "time_based":
            max_age_days = kwargs.get("max_age_days", self.config.forget_max_age_days)
            self.working.forget_by_age(max_age_days)
            self.episodic.forget_by_age(max_age_days)
        elif strategy == "capacity_based":
            self.working.forget_by_capacity()
        else:
            raise ValueError(f"未知遗忘策略: {strategy}")

    # ── 整合机制 ──────────────────────────────────────────────

    def consolidate(self, threshold: Optional[float] = None) -> int:
        """
        将重要的工作记忆提升为情景记忆（模拟睡眠整合）。

        Returns: 提升的记忆条数
        """
        threshold = threshold or self.config.consolidation_importance_threshold
        important = self.working.get_important(threshold)
        count = 0
        for item in important:
            item.memory_type = "episodic"
            self.episodic.add(item)
            self.working.delete(item.id)
            count += 1
        return count

    # ── 信息查询 ──────────────────────────────────────────────

    def summary(self) -> str:
        """生成当前记忆状态的文本摘要"""
        lines = ["📝 记忆系统摘要:\n"]
        for _type, store in self._type_map.items():
            try:
                cnt = store.count()
                lines.append(f"  · {_type}: {cnt} 条")
            except NotImplementedError:
                lines.append(f"  · {_type}: ❌ 未启用")
        return "\n".join(lines)

    def stats(self) -> dict:
        """返回各类型的详细统计"""
        result = {}
        for _type, store in self._type_map.items():
            try:
                result[_type] = {
                    "enabled": True,
                    "count": store.count(),
                }
            except NotImplementedError:
                result[_type] = {"enabled": False, "count": 0}
        return result
