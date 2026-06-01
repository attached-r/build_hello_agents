"""
Neo4j 图存储 — 知识图谱管理。

提供实体和关系的图数据库操作，支持语义记忆的图检索。
依赖: pip install neo4j
"""

import os
from typing import Any, Optional


try:
    from neo4j import GraphDatabase

    NEO4J_AVAILABLE = True
except ImportError:
    NEO4J_AVAILABLE = False


class Neo4jGraphStore:
    """Neo4j 图数据库存储封装"""

    def __init__(
        self,
        uri: Optional[str] = None,
        user: Optional[str] = None,
        password: Optional[str] = None,
        database: Optional[str] = None,
        **kwargs,
    ):
        if not NEO4J_AVAILABLE:
            raise ImportError("Neo4j 驱动未安装: pip install neo4j")

        self._uri = uri or os.getenv("NEO4J_URI", "bolt://localhost:7687")
        self._user = user or os.getenv("NEO4J_USER", "neo4j")
        self._password = password or os.getenv("NEO4J_PASSWORD", "neo4j")
        self._database = database or os.getenv("NEO4J_DATABASE") or None
        self._driver = GraphDatabase.driver(self._uri, auth=(self._user, self._password))
        self._driver.verify_connectivity()

    def close(self):
        """关闭连接"""
        if self._driver:
            self._driver.close()

    def __del__(self):
        self.close()

    # ── 底层执行 ──────────────────────────────────────────────

    def _run(self, cypher: str, params: Optional[dict] = None) -> list[dict[str, Any]]:
        """执行 Cypher 查询并返回结果列表"""
        params = params or {}
        with self._driver.session(database=self._database) as session:
            return [record.data() for record in session.run(cypher, params)]

    # ── 实体操作 ──────────────────────────────────────────────

    def create_entity(
        self,
        entity_id: str,
        name: str,
        entity_type: str = "concept",
        memory_id: str = "",
        properties: Optional[dict] = None,
    ) -> bool:
        """创建实体节点（MERGE 避免重复）"""
        props = properties or None  # None → 不设置 e.properties
        result = self._run(
            "MERGE (e:Entity {entity_id: $entity_id}) "
            "SET e.name = $name, e.type = $entity_type, e.memory_id = $memory_id, "
            "    e.created_at = timestamp() "
            "SET e.properties = $props "
            "RETURN e",
            {
                "entity_id": entity_id,
                "name": name,
                "entity_type": entity_type,
                "memory_id": memory_id,
                "props": props,
            },
        )
        return len(result) > 0

    def get_entity(self, entity_id: str) -> Optional[dict]:
        """按 ID 获取实体"""
        result = self._run(
            "MATCH (e:Entity {entity_id: $entity_id}) RETURN e AS entity",
            {"entity_id": entity_id},
        )
        return result[0]["entity"] if result else None

    def search_entities(self, query: str, limit: int = 10) -> list[dict]:
        """按名称模糊搜索实体"""
        return self._run(
            "MATCH (e:Entity) "
            "WHERE e.name CONTAINS $query OR toLower(e.name) CONTAINS toLower($query) "
            "RETURN e AS entity, e.name AS name, e.type AS entity_type, "
            "       e.memory_id AS memory_id "
            "LIMIT $limit",
            {"query": query, "limit": limit},
        )

    def delete_entity(self, entity_id: str) -> bool:
        """删除实体及其所有关系"""
        self._run(
            "MATCH (e:Entity {entity_id: $entity_id}) DETACH DELETE e",
            {"entity_id": entity_id},
        )
        return True

    # ── 关系操作 ──────────────────────────────────────────────

    def create_relation(
        self,
        subject_id: str,
        object_id: str,
        relation_type: str,
        memory_id: str = "",
        properties: Optional[dict] = None,
    ) -> bool:
        """创建实体间关系"""
        props = properties or None
        if props is not None:
            result = self._run(
                "MATCH (s:Entity {entity_id: $subject_id}) "
                "MATCH (o:Entity {entity_id: $object_id}) "
                "MERGE (s)-[r:RELATION {type: $relation_type}]->(o) "
                "SET r.memory_id = $memory_id, r.properties = $props, "
                "    r.created_at = timestamp() "
                "RETURN r",
                {
                    "subject_id": subject_id,
                    "object_id": object_id,
                    "relation_type": relation_type,
                    "memory_id": memory_id,
                    "props": props,
                },
            )
        else:
            result = self._run(
                "MATCH (s:Entity {entity_id: $subject_id}) "
                "MATCH (o:Entity {entity_id: $object_id}) "
                "MERGE (s)-[r:RELATION {type: $relation_type}]->(o) "
                "SET r.memory_id = $memory_id, "
                "    r.created_at = timestamp() "
                "RETURN r",
                {
                    "subject_id": subject_id,
                    "object_id": object_id,
                    "relation_type": relation_type,
                    "memory_id": memory_id,
                },
            )
        return len(result) > 0

    def get_relations(
        self,
        entity_id: str,
        relation_type: Optional[str] = None,
    ) -> list[dict]:
        """获取实体的所有关系（含方向）"""
        if relation_type:
            return self._run(
                "MATCH (s:Entity {entity_id: $entity_id})"
                "-[r:RELATION {type: $relation_type}]->(o:Entity) "
                "RETURN s.name AS subject, r.type AS relation_type, "
                "       o.name AS object, o.entity_id AS object_id, "
                "       r.memory_id AS memory_id "
                "UNION "
                "MATCH (s:Entity)"
                "-[r:RELATION {type: $relation_type}]->(o:Entity {entity_id: $entity_id}) "
                "RETURN s.name AS subject, r.type AS relation_type, "
                "       o.name AS object, s.entity_id AS object_id, "
                "       r.memory_id AS memory_id",
                {"entity_id": entity_id, "relation_type": relation_type},
            )
        return self._run(
            "MATCH (s:Entity {entity_id: $entity_id})-[r:RELATION]->(o:Entity) "
            "RETURN s.name AS subject, r.type AS relation_type, "
            "       o.name AS object, o.entity_id AS object_id, "
            "       r.memory_id AS memory_id "
            "UNION "
            "MATCH (s:Entity)-[r:RELATION]->(o:Entity {entity_id: $entity_id}) "
            "RETURN s.name AS subject, r.type AS relation_type, "
            "       o.name AS object, s.entity_id AS object_id, "
            "       r.memory_id AS memory_id",
            {"entity_id": entity_id},
        )

    # ── 图搜索（语义记忆专用） ────────────────────────────────

    def graph_search(self, query: str, limit: int = 10) -> list[dict]:
        """
        图搜索：找到匹配实体 → 再探索其关联记忆，返回带评分的结果。

        Returns:
            [{"memory_id", "entity_name", "entity_type", "relation_info", "similarity"}, ...]
        """
        entities = self.search_entities(query, limit=limit)
        if not entities:
            return []

        results: list[dict] = []
        seen_memory_ids: set[str] = set()

        for ent in entities:
            entity = ent.get("entity", {}) if isinstance(ent.get("entity"), dict) else {}
            entity_id = entity.get("entity_id", "") if isinstance(entity, dict) else ""
            memory_id = entity.get("memory_id", ent.get("memory_id", ""))
            entity_name = entity.get("name", ent.get("name", ""))
            entity_type = entity.get("type", ent.get("entity_type", ""))

            # 直接匹配
            if memory_id and memory_id not in seen_memory_ids:
                seen_memory_ids.add(memory_id)
                results.append({
                    "memory_id": memory_id,
                    "entity_name": entity_name,
                    "entity_type": entity_type,
                    "relation_info": "直接匹配",
                    "similarity": 0.9,
                })

            # 探索关联实体
            if not entity_id:
                continue
            for rel in self.get_relations(entity_id):
                mid = rel.get("memory_id", "")
                if mid and mid not in seen_memory_ids:
                    seen_memory_ids.add(mid)
                    results.append({
                        "memory_id": mid,
                        "entity_name": rel.get("object", ""),
                        "entity_type": "related",
                        "relation_info": (
                            f"{rel.get('subject', '')} "
                            f"--[{rel.get('relation_type', '')}]--> "
                            f"{rel.get('object', '')}"
                        ),
                        "similarity": 0.6,
                    })

        return results[:limit]

    # ── 维护操作 ──────────────────────────────────────────────

    def clear_all(self) -> int:
        """清空所有节点和关系"""
        result = self._run("MATCH (n) DETACH DELETE n RETURN count(n) AS count")
        return result[0]["count"] if result else 0

    def count_entities(self) -> int:
        """统计实体数"""
        result = self._run("MATCH (e:Entity) RETURN count(e) AS count")
        return result[0]["count"] if result else 0

    def count_relations(self) -> int:
        """统计关系数"""
        result = self._run("MATCH ()-[r:RELATION]->() RETURN count(r) AS count")
        return result[0]["count"] if result else 0