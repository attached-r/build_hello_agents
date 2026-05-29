"""
语义记忆 — 存储抽象知识、概念和规则，使用向量+图的混合检索。

架构:
  - 嵌入向量: 通过 BaseEmbedding 进行语义检索
  - 知识图谱: 通过 Neo4j 存储实体和关系，支持关系推理
  - 混合评分: (向量相似度 × 0.7 + 图相似度 × 0.3) × (0.8 + 重要性 × 0.4)
"""

import re
import uuid
from datetime import datetime
from typing import Optional

from ..base import MemoryItem, MemoryConfig, BaseMemory


class SemanticMemory(BaseMemory):
    """语义记忆 —— 知识图谱 + 向量混合检索"""

    def __init__(
        self,
        config: Optional[MemoryConfig] = None,
        embedding=None,
        vector_store=None,
        graph_store=None,
    ):
        super().__init__(config or MemoryConfig())
        self.embedding = embedding
        self._vector_store = vector_store
        self._graph_store = graph_store

        # 内存缓存（无后端时兜底）
        self._items: dict[str, MemoryItem] = {}
        self._entities: dict[str, dict] = {}
        self._relations: list[dict] = []

    def _ensure_graph_store(self):
        """惰性初始化 Neo4j"""
        if self._graph_store is not None:
            return
        try:
            from ..storage.neo4j_store import Neo4jGraphStore
            self._graph_store = Neo4jGraphStore()
        except Exception:
            pass

    # ── 实体与关系提取 ────────────────────────────────────────

    ENTITY_PATTERN = re.compile(
        r'[""「『\"]?([一-鿿\w]+(?:[一-鿿\w\s]*[一-鿿\w])?)[""」』\"]?'
        r"(?:是一种|是一个|是一|指|表示|指的是|是指|意为|意思是|属于|是)"
    )

    RELATION_PATTERN = re.compile(
        r'[""「『\"]?([一-鿿\w]+)[""」』\"]?'
        r"(?:是|属于|位于|包含|包括|拥有|使用|依赖|产生|导致|影响|关联|"
        r"定义|继承|实现|创建|调用)"
        r'[""「『\"]?([一-鿿\w]+)[""」』\"]?'
    )

    def _extract_entities(self, text: str) -> list[dict]:
        """从文本中提取实体"""
        entities: list[dict] = []
        seen: set[str] = set()

        for match in self.ENTITY_PATTERN.finditer(text):
            name = match.group(1).strip()
            if name and name not in seen:
                seen.add(name)
                entities.append({
                    "entity_id": uuid.uuid4().hex[:12],
                    "name": name,
                    "type": "concept",
                })

        if not entities:
            for w in re.findall(r"[一-鿿]{2,}", text):
                if w not in seen:
                    seen.add(w)
                    entities.append({
                        "entity_id": uuid.uuid4().hex[:12],
                        "name": w,
                        "type": "concept",
                    })

        return entities

    def _extract_relations(self, text: str, entities: list[dict]) -> list[dict]:
        """从文本中提取实体间关系"""
        relations: list[dict] = []
        entity_names = {e["name"]: e["entity_id"] for e in entities}

        REL_KEYWORDS = [
            "是", "属于", "位于", "包含", "包括", "拥有", "使用",
            "依赖", "产生", "导致", "影响", "关联", "定义", "继承",
            "实现", "创建", "调用",
        ]

        for match in self.RELATION_PATTERN.finditer(text):
            subj_name = match.group(1).strip()
            obj_name = match.group(2).strip()
            rel_type = "related_to"
            for kw in REL_KEYWORDS:
                if kw in match.group(0):
                    rel_type = kw
                    break

            relations.append({
                "subject_id": entity_names.get(subj_name, uuid.uuid4().hex[:12]),
                "object_id": entity_names.get(obj_name, uuid.uuid4().hex[:12]),
                "type": rel_type,
            })

        return relations

    # ── CRUD ──────────────────────────────────────────────────

    def add(self, item: MemoryItem) -> str:
        """添加语义记忆（向量 + 图 + 内存）"""
        self._items[item.id] = item

        entities = self._extract_entities(item.content)
        relations = self._extract_relations(item.content, entities)

        # 图存储
        self._ensure_graph_store()
        if self._graph_store:
            try:
                for e in entities:
                    self._graph_store.create_entity(
                        entity_id=e["entity_id"],
                        name=e["name"],
                        entity_type=e["type"],
                        memory_id=item.id,
                    )
                for r in relations:
                    self._graph_store.create_relation(
                        subject_id=r["subject_id"],
                        object_id=r["object_id"],
                        relation_type=r["type"],
                        memory_id=item.id,
                    )
            except Exception:
                pass

        # 缓存实体关系
        self._entities.update({e["entity_id"]: {**e, "memory_id": item.id} for e in entities})
        self._relations.extend({**r, "memory_id": item.id} for r in relations)

        # 向量存储
        if self._vector_store:
            try:
                self._vector_store.upsert([{
                    "id": item.id,
                    "payload": {
                        "memory_id": item.id,
                        "content": item.content,
                        "memory_type": item.memory_type,
                        "importance": item.importance,
                        "user_id": item.user_id,
                        "session_id": item.session_id,
                        "timestamp": item.timestamp.isoformat(),
                    },
                }])
            except Exception:
                pass

        return item.id

    def search(self, query: str, limit: int = 5, **kwargs) -> list[MemoryItem]:
        """混合检索：向量 + 图 + 混合排序"""
        user_id = kwargs.get("user_id", "")

        vector_results = self._vector_search(query, limit * 2, user_id)
        graph_results = self._graph_search(query, limit * 2, user_id)

        return self._combine_and_rank(vector_results, graph_results, limit)

    def _vector_search(self, query: str, limit: int = 10, user_id: str = "") -> list[dict]:  # noqa: ARG002
        """向量相似度检索"""
        results: list[dict] = []

        if self._vector_store:
            try:
                for hit in self._vector_store.search(query=query, limit=max(limit, 20)):
                    payload = hit.get("payload", {})
                    results.append({
                        "memory_id": payload.get("memory_id", hit.get("id", "")),
                        "score": hit.get("score", 0.0),
                        "content": payload.get("content", ""),
                        "importance": payload.get("importance", 0.5),
                        "timestamp": payload.get("timestamp", ""),
                    })
            except Exception:
                pass

        # 内存向量检索回退
        if not results and self.embedding and self._items:
            query_vec = self.embedding.embed(query)
            scored = []
            for item in self._items.values():
                sim = self.embedding.cosine_similarity(query_vec, self.embedding.embed(item.content))
                scored.append((sim, item))
            scored.sort(key=lambda x: x[0], reverse=True)
            results = [
                {
                    "memory_id": item.id,
                    "score": sim,
                    "content": item.content,
                    "importance": item.importance,
                    "timestamp": item.timestamp.isoformat(),
                }
                for sim, item in scored[:limit]
            ]

        return results

    def _graph_search(self, query: str, limit: int = 10, user_id: str = "") -> list[dict]:  # noqa: ARG002
        """图检索：通过实体关系发现关联记忆"""
        results: list[dict] = []

        self._ensure_graph_store()
        if self._graph_store:
            try:
                for hit in self._graph_store.graph_search(query=query, limit=limit):
                    mid = hit.get("memory_id", "")
                    item = self._items.get(mid)
                    results.append({
                        "memory_id": mid,
                        "similarity": hit.get("similarity", 0.5),
                        "content": item.content if item else "",
                        "importance": item.importance if item else 0.5,
                        "timestamp": item.timestamp.isoformat() if item else "",
                        "relation_info": hit.get("relation_info", ""),
                    })
            except Exception:
                pass

        # 内存实体匹配回退
        if not results:
            q = query.lower()
            for entity in self._entities.values():
                if q in entity.get("name", "").lower():
                    item = self._items.get(entity.get("memory_id", ""))
                    if item:
                        results.append({
                            "memory_id": item.id,
                            "similarity": 0.5,
                            "content": item.content,
                            "importance": item.importance,
                            "timestamp": item.timestamp.isoformat(),
                            "relation_info": entity.get("name", ""),
                        })

        return results

    def _combine_and_rank(
        self,
        vector_results: list[dict],
        graph_results: list[dict],
        limit: int,
    ) -> list[MemoryItem]:
        """混合排序：（向量×0.7 + 图×0.3）×（0.8 + 重要性×0.4）"""
        combined: dict[str, dict] = {}

        for r in vector_results:
            mid = r["memory_id"]
            combined[mid] = {**r, "vector_score": r.get("score", 0.0), "graph_score": 0.0}

        for r in graph_results:
            mid = r["memory_id"]
            if mid in combined:
                combined[mid]["graph_score"] = r.get("similarity", 0.0)
            else:
                combined[mid] = {
                    **r, "vector_score": 0.0,
                    "graph_score": r.get("similarity", 0.0),
                }

        scored: list[tuple[float, MemoryItem]] = []
        for mid, result in combined.items():
            vs = result.get("vector_score", 0.0)
            gs = result.get("graph_score", 0.0)
            imp = result.get("importance", 0.5)
            base = vs * 0.7 + gs * 0.3
            weight = 0.8 + imp * 0.4
            combined_score = base * weight

            item = self._items.get(mid)
            if item is None:
                item = MemoryItem(
                    id=mid,
                    content=result.get("content", ""),
                    memory_type="semantic",
                    importance=imp,
                    timestamp=(
                        datetime.fromisoformat(result["timestamp"])
                        if result.get("timestamp") else datetime.now()
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
        del self._items[memory_id]
        if self._vector_store:
            try:
                self._vector_store.delete_by_filter({"memory_id": memory_id})
            except Exception:
                pass
        return True

    def clear(self) -> int:
        n = len(self._items)
        self._items.clear()
        self._entities.clear()
        self._relations.clear()
        return n

    def count(self) -> int:
        return len(self._items)