"""
感知记忆 — 处理多模态信息（文本、图像、音频）。

架构:
  - 按模态分离的向量存储（text / image / audio）
  - 同模态 / 跨模态检索
  - 评分: (向量相似度 × 0.8 + 时间近因性 × 0.2) × (0.8 + 重要性 × 0.4)
"""

import math
from datetime import datetime
from typing import Any, Optional

from ..base import MemoryItem, MemoryConfig, BaseMemory


class PerceptualMemory(BaseMemory):
    """感知记忆 —— 多模态存储与检索"""

    def __init__(
        self,
        config: Optional[MemoryConfig] = None,
        embedding=None,
        vector_stores: Optional[dict[str, Any]] = None,
        **kwargs,
    ):
        super().__init__(config or MemoryConfig())
        self.embedding = embedding
        self._vector_stores: dict[str, Any] = vector_stores or {}

        # 内存缓存（无后端时兜底）
        self._items: dict[str, MemoryItem] = {}
        self._modality_index: dict[str, set[str]] = {
            "text": set(),
            "image": set(),
            "audio": set(),
        }

    # ── 后端惰性初始化 ────────────────────────────────────────

    def _get_store(self, modality: str):
        """获取指定模态的向量存储，不存在则惰性创建"""
        if modality not in self._vector_stores:
            try:
                from ..storage.qdrant_store import QdrantVectorStore

                self._vector_stores[modality] = QdrantVectorStore(
                    collection_name=f"perceptual_{modality}",
                    embedding_fn=self.embedding.embed if self.embedding else None,
                )
            except Exception:
                pass
        return self._vector_stores.get(modality)

    # ── 编码（简化实现，无 CLIP/CLAP 时全部走文本嵌入） ──────

    def _encode_data(self, data: str, modality: str) -> list[float]:
        """将输入数据编码为向量"""
        if self.embedding:
            return self.embedding.embed(data)
        raise ValueError("未配置嵌入模型，无法编码")

    # ── 时间近因性 ────────────────────────────────────────────

    @staticmethod
    def _calculate_recency_score(timestamp: str) -> float:
        """指数衰减：24 小时内保持高分，之后逐渐衰减"""
        try:
            memory_time = datetime.fromisoformat(timestamp)
            age_hours = (datetime.now() - memory_time).total_seconds() / 3600
            decay = math.exp(-0.1 * age_hours / 24)
            return max(0.1, decay)
        except Exception:
            return 0.5

    # ── CRUD ──────────────────────────────────────────────────

    def add(self, item: MemoryItem) -> str:
        """添加感知记忆"""
        modality = item.metadata.get("modality", "text")
        self._items[item.id] = item
        self._modality_index.setdefault(modality, set()).add(item.id)

        store = self._get_store(modality)
        if store:
            try:
                store.upsert([{
                    "id": item.id,
                    "payload": {
                        "memory_id": item.id,
                        "content": item.content,
                        "modality": modality,
                        "memory_type": item.memory_type,
                        "importance": item.importance,
                        "user_id": item.user_id,
                        "session_id": item.session_id,
                        "timestamp": item.timestamp.isoformat(),
                        **item.metadata,
                    },
                }])
            except Exception:
                pass

        return item.id

    def search(self, query: str, limit: int = 5, **kwargs) -> list[MemoryItem]:
        """
        检索感知记忆（可筛模态；纯向量检索+时间/重要性融合）。

        Args:
            query: 查询文本
            limit: 返回条数
            target_modality: 目标模态（None 表示所有模态）
            query_modality: 查询模态（默认与 target_modality 相同，或 text）
            user_id: 用户 ID 过滤
        """
        user_id = kwargs.get("user_id", "")
        target_modality = kwargs.get("target_modality")
        query_modality = kwargs.get("query_modality", target_modality or "text")

        modalities = [target_modality] if target_modality else list(self._modality_index.keys())

        hits: list[dict] = []
        for mod in modalities:
            store = self._get_store(mod)
            if not store:
                continue
            try:
                query_vector = self._encode_data(query, query_modality)
                where: dict[str, Any] = {"memory_type": "perceptual", "modality": mod}
                if user_id:
                    where["user_id"] = user_id

                for hit in store.search(
                    query=query_vector,
                    limit=max(limit * 5, 20),
                    payload_filter=where,
                ):
                    payload = hit.get("payload", {})
                    hits.append({
                        "score": hit.get("score", 0.0),
                        "memory_id": payload.get("memory_id", ""),
                        "content": payload.get("content", ""),
                        "modality": payload.get("modality", mod),
                        "importance": payload.get("importance", 0.5),
                        "timestamp": payload.get("timestamp", ""),
                        "user_id": payload.get("user_id", ""),
                    })
            except Exception:
                continue

        # 无向量后端：内存关键词匹配回退
        if not hits:
            q = query.lower()
            for item in self._items.values():
                mod = item.metadata.get("modality", "text")
                if target_modality and mod != target_modality:
                    continue
                if q in item.content.lower():
                    hits.append({
                        "score": 0.5,
                        "memory_id": item.id,
                        "content": item.content,
                        "modality": mod,
                        "importance": item.importance,
                        "timestamp": item.timestamp.isoformat(),
                        "user_id": item.user_id,
                    })

        # 评分排序
        scored: list[tuple[float, MemoryItem]] = []
        for hit in hits:
            vector_score = float(hit.get("score", 0.0))
            recency_score = self._calculate_recency_score(hit.get("timestamp", ""))
            importance = float(hit.get("importance", 0.5))

            base_rel = vector_score * 0.8 + recency_score * 0.2
            importance_weight = 0.8 + importance * 0.4
            combined_score = base_rel * importance_weight

            item = self._items.get(hit["memory_id"])
            if item is None:
                item = MemoryItem(
                    id=hit["memory_id"],
                    content=hit.get("content", ""),
                    memory_type="perceptual",
                    importance=importance,
                    metadata={"modality": hit.get("modality", "text")},
                    timestamp=(
                        datetime.fromisoformat(hit["timestamp"])
                        if hit.get("timestamp") else datetime.now()
                    ),
                )
            scored.append((combined_score, item))

        scored.sort(key=lambda x: x[0], reverse=True)
        return [item for _, item in scored[:limit]]

    def get(self, memory_id: str) -> Optional[MemoryItem]:
        return self._items.get(memory_id)

    def update(self, memory_id: str, **updates) -> bool:
        item = self._items.get(memory_id)
        if item is None:
            return False
        for k, v in updates.items():
            if hasattr(item, k):
                setattr(item, k, v)
        return True

    def delete(self, memory_id: str) -> bool:
        if memory_id not in self._items:
            return False
        item = self._items.pop(memory_id)
        mod = item.metadata.get("modality", "text")
        self._modality_index.get(mod, set()).discard(memory_id)
        store = self._get_store(mod)
        if store:
            try:
                store.delete_by_filter({"memory_id": memory_id})
            except Exception:
                pass
        return True

    def clear(self) -> int:
        n = len(self._items)
        self._items.clear()
        self._modality_index = {"text": set(), "image": set(), "audio": set()}
        return n

    def count(self) -> int:
        return len(self._items)
