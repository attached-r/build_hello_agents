"""
工作记忆 — 短期记忆，纯内存存储。

核心特征：
  - 纯内存：列表存储，不持久化
  - TTL 管理：默认 60 分钟自动过期
  - 容量限制：默认最多 50 条，超出移除最旧
  - 检索策略：TF-IDF + 关键词匹配 + 时间衰减
"""

from datetime import datetime, timedelta
from typing import Optional

from ..base import MemoryItem, MemoryConfig, BaseMemory
from ..embedding import TFIDFEmbedding, BaseEmbedding


class WorkingMemory(BaseMemory):
    """工作记忆 —— 类比人类的短期记忆"""

    def __init__(
        self,
        config: Optional[MemoryConfig] = None,
        embedding: Optional[BaseEmbedding] = None,
    ):
        super().__init__(config or MemoryConfig())
        self._items: list[MemoryItem] = []             #? 记忆列表 存储短期记忆
        self._embedding = embedding or TFIDFEmbedding()
        self._ttl = timedelta(minutes=self.config.working_ttl_minutes)
        self._capacity = self.config.working_capacity

    # ── 核心操作 ──────────────────────────────────────────────
    def add(self, item: MemoryItem) -> str:
        self._expire()  # 每次添加前清理过期记忆
        if len(self._items) >= self._capacity:
            self._items.pop(0)
        self._items.append(item)
        return item.id

    def search(self, query: str, limit: int = 5, **kwargs) -> list[MemoryItem]:
        self._expire()
        if not self._items:
            return []

        query_vec = self._embedding.embed(query)

        # 评分：余弦相似度 × 时间衰减因子
        now = datetime.now()
        scored: list[tuple[float, MemoryItem]] = []
        for item in self._items:
            item_vec = self._embedding.embed(item.content)
            similarity = self._embedding.cosine_similarity(query_vec, item_vec)

            # 时间衰减：越近得分越高（1h 后衰减到约 0.37）
            age_hours = (now - item.timestamp).total_seconds() / 3600
            time_decay = 1.0 / (1.0 + age_hours)

            score = similarity * 0.7 + time_decay * 0.3
            scored.append((score, item))

        scored.sort(key=lambda x: x[0], reverse=True)
        return [item for _, item in scored[:limit]]

    def get(self, memory_id: str) -> Optional[MemoryItem]:
        self._expire()
        for item in self._items:
            if item.id == memory_id:
                return item
        return None

    def update(self, memory_id: str, **updates) -> bool:
        self._expire()
        for item in self._items:
            if item.id == memory_id:
                for k, v in updates.items():
                    if hasattr(item, k):
                        setattr(item, k, v)
                return True
        return False

    def delete(self, memory_id: str) -> bool:
        self._expire()
        for i, item in enumerate(self._items):
            if item.id == memory_id:
                self._items.pop(i)
                return True
        return False

    def clear(self) -> int:
        n = len(self._items)
        self._items.clear()
        return n

    def count(self) -> int:
        self._expire()
        return len(self._items)

    def get_all(self) -> list[MemoryItem]:
        self._expire()
        return self._items.copy()

    # ── TTL 过期清理 ─────────────────────────────────────────
    def _expire(self):
        now = datetime.now()
        self._items = [
            item for item in self._items
            if (now - item.timestamp) < self._ttl
        ]

    # ── 额外接口 ──────────────────────────────────────────────
    def get_recent(self, n: int = 5) -> list[MemoryItem]:
        """获取最近 n 条记忆（不过期清理）"""
        self._expire()
        return self._items[-n:]

    def forget_by_importance(self, threshold: float = 0.2):
        """遗忘重要性低于阈值的记忆"""
        self._items = [
            item for item in self._items
            if item.importance >= threshold
        ]

    def forget_by_age(self, max_age_days: int = 30):
        """遗忘超过指定天数的记忆"""
        cutoff = datetime.now() - timedelta(days=max_age_days)
        self._items = [
            item for item in self._items
            if item.timestamp >= cutoff
        ]

    def forget_by_capacity(self, threshold: float = 0.3):
        """超出容量时移除最不重要的记忆"""
        if len(self._items) <= self._capacity:
            return
        self._items.sort(key=lambda x: x.importance)
        self._items = self._items[-self._capacity:]

    def get_important(self, threshold: float = 0.7) -> list[MemoryItem]:
        """获取重要性超过阈值的记忆"""
        self._expire()
        return [item for item in self._items if item.importance >= threshold]
