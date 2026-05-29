"""
情景记忆 — 用于长期保存交互事件和历史经历。

核心特征：
  - 持久化存储：基于 DocumentStore（SQLite / MySQL）
  - 检索评分：语义相似度 × 0.5 + 时间近因 × 0.3 + 重要性 × 0.2
  - 遗忘策略：按时间 / 按重要性
"""

from datetime import datetime, timedelta
from typing import Optional

from ..base import MemoryItem, MemoryConfig, BaseMemory
from ..embedding import TFIDFEmbedding, BaseEmbedding
from ..storage.document_store import DocumentStore


class EpisodicMemory(BaseMemory):
    """情景记忆 —— 类比人类对经历过事件的记忆"""

    def __init__(
        self,
        config: Optional[MemoryConfig] = None,
        embedding: Optional[BaseEmbedding] = None,
    ):
        super().__init__(config or MemoryConfig())
        self._embedding = embedding or TFIDFEmbedding()
        self._store = DocumentStore(
            db_path=self.config.episodic_db_path,
            db_type=self.config.episodic_db_type,
        )

    # ── 核心操作 ──────────────────────────────────────────────

    def add(self, item: MemoryItem) -> str:
        return self._store.insert(item)

    def search(self, query: str, limit: int = 5, **kwargs) -> list[MemoryItem]:
        items = self._store.fetch_all("episodic")
        if not items:
            return []

        query_vec = self._embedding.embed(query)
        now = datetime.now()

        scored: list[tuple[float, MemoryItem]] = []
        for item in items:
            # 语义相似度
            item_vec = self._embedding.embed(item.content)
            similarity = self._embedding.cosine_similarity(query_vec, item_vec)

            # 时间近因：1 / (1 + age_days)
            age_days = (now - item.timestamp).total_seconds() / 86400
            recency = 1.0 / (1.0 + age_days)

            # 加权评分
            score = similarity * 0.5 + recency * 0.3 + item.importance * 0.2
            scored.append((score, item))

        scored.sort(key=lambda x: x[0], reverse=True)
        return [item for _, item in scored[:limit]]

    def get(self, memory_id: str) -> Optional[MemoryItem]:
        return self._store.fetch(memory_id)

    def update(self, memory_id: str, **updates) -> bool:
        return self._store.update(memory_id, **updates)

    def delete(self, memory_id: str) -> bool:
        return self._store.delete(memory_id)

    def clear(self) -> int:
        return self._store.clear("episodic")

    def count(self) -> int:
        return self._store.count("episodic")

    def get_all(self) -> list[MemoryItem]:
        return self._store.fetch_all("episodic")

    # ── 遗忘策略 ──────────────────────────────────────────────

    def forget_by_age(self, max_age_days: int = 30):
        """删除超过指定天数的记忆"""
        cutoff = datetime.now() - timedelta(days=max_age_days)
        self._store.delete_before("episodic", cutoff.isoformat())

    def forget_by_importance(self, threshold: float = 0.2):
        """删除重要性低于阈值的记忆"""
        self._store.delete_by_importance("episodic", threshold)
