"""
Qdrant 向量存储 — 高性能向量检索（支持本地和云端模式）。

支持两种连接模式:
  1. 本地模式: host + port（如 localhost:6333）
  2. 云端模式: url + api_key（如 Qdrant Cloud）

配置优先级: 构造参数 > 环境变量 > 默认值
  环境变量: QDRANT_CLUSTER_ENDPOINT, QDRANT_API_KEY, QDRANT_COLLECTION,
            QDRANT_VECTOR_SIZE, QDRANT_DISTANCE, QDRANT_TIMEOUT
"""

import os
import uuid
from typing import Any, Optional

from ..base import MemoryItem


# ── 尝试导入 qdrant-client ──────────────────────────────────
try:
    from qdrant_client import QdrantClient
    from qdrant_client.http import models as qmodels
    from qdrant_client.http.exceptions import UnexpectedResponse

    QDRANT_AVAILABLE = True
except ImportError:
    QDRANT_AVAILABLE = False


# ── Qdrant 距离映射 ─────────────────────────────────────────
DISTANCE_MAP = {
    "cosine": qmodels.Distance.COSINE,
    "dot": qmodels.Distance.DOT,
    "euclid": qmodels.Distance.EUCLID,
}


class QdrantVectorStore:
    """Qdrant 向量存储封装"""

    def __init__(
        self,
        collection_name: Optional[str] = None,
        host: Optional[str] = None,
        port: Optional[int] = None,
        url: Optional[str] = None,
        api_key: Optional[str] = None,
        vector_size: Optional[int] = None,
        distance: str = "cosine",
        timeout: Optional[int] = None,
        embedding_fn=None,
    ):
        """
        Args:
            collection_name: 集合名称（默认: 环境变量 QDRANT_COLLECTION 或 "knowledge_base"）
            host: Qdrant 主机地址（本地模式），设置后自动切换本地模式
            port: Qdrant 端口（本地模式，默认 6333）
            url: Qdrant 云端 URL（云端模式），设置后自动切换云端模式
            api_key: Qdrant API Key（云端模式必需）
            vector_size: 向量维度（默认: 环境变量 QDRANT_VECTOR_SIZE 或 768）
            distance: 距离度量（cosine/dot/euclid，默认: 环境变量 QDRANT_DISTANCE 或 cosine）
            timeout: 请求超时秒数（默认: 环境变量 QDRANT_TIMEOUT 或 30）
            embedding_fn: 嵌入函数，接收 str → list[float]  支持TFIDFEmbedding 和 FastEmbedEmbedding
        """
        # ── 读取环境变量 ──────────────────────────────────────
        env_url = os.getenv("QDRANT_CLUSTER_ENDPOINT", "")
        env_api_key = os.getenv("QDRANT_API_KEY", "")
        env_collection = os.getenv("QDRANT_COLLECTION", "")
        env_vector_size = os.getenv("QDRANT_VECTOR_SIZE", "")
        env_distance = os.getenv("QDRANT_DISTANCE", "cosine")
        env_timeout = os.getenv("QDRANT_TIMEOUT", "30")

        # ── 确定连接模式 ──────────────────────────────────────
        self.collection_name = collection_name or env_collection or "knowledge_base"
        self.vector_size = vector_size or int(env_vector_size) if env_vector_size else 768
        self._embedding_fn = embedding_fn

        if not QDRANT_AVAILABLE:
            raise ImportError("请安装 qdrant-client: pip install qdrant-client")

        # 云端模式：显式传入 url 或有 QDRANT_CLUSTER_ENDPOINT 环境变量
        resolved_url = url or (env_url if env_url else None)
        resolved_api_key = api_key or env_api_key or None

        if resolved_url:
            self._client = QdrantClient(
                url=resolved_url,
                api_key=resolved_api_key,
                timeout=timeout or int(env_timeout),
            )
        else:
            # 本地模式
            self._client = QdrantClient(
                host=host or "localhost",
                port=port or 6333,
                timeout=timeout or int(env_timeout),
                api_key=resolved_api_key,
            )

        # 距离度量
        self._distance = DISTANCE_MAP.get(distance or env_distance, qmodels.Distance.COSINE)

    # ── 集合管理 ──────────────────────────────────────────────

    def create_collection(
        self,
        collection_name: Optional[str] = None,
        force: bool = False,
    ) -> bool:
        """创建集合，已存在时若 force=True 则删除重建"""
        name = collection_name or self.collection_name
        if self._collection_exists(name):
            if not force:
                return False
            self._client.delete_collection(name)

        self._client.create_collection(
            collection_name=name,
            vectors_config=qmodels.VectorParams(
                size=self.vector_size,
                distance=self._distance,
            ),
        )
        return True

    def delete_collection(self, collection_name: Optional[str] = None) -> bool:
        """删除集合"""
        name = collection_name or self.collection_name
        if not self._collection_exists(name):
            return False
        self._client.delete_collection(name)
        return True

    def list_collections(self) -> list[str]:
        """列出所有集合名称"""
        return [c.name for c in self._client.get_collections().collections]

    def collection_exists(self, name: Optional[str] = None) -> bool:
        """检查集合是否存在"""
        return self._collection_exists(name or self.collection_name)

    def _collection_exists(self, name: str) -> bool:
        try:
            self._client.get_collection(name)
            return True
        except (UnexpectedResponse, ValueError):
            return False

    # ── 数据写入 ──────────────────────────────────────────────

    def upsert(
        self,
        points: list[dict[str, Any]],
        collection_name: Optional[str] = None,
    ) -> int:
        """
        批量写入/更新向量点。

        points 格式:
            [{
                "id": str | int,        # 可选，自动生成 UUID
                "vector": list[float],  # 若不提供且 embedding_fn 存在则自动计算
                "payload": {...},       # 可选
            }]
        Returns:
            写入的点数
        """
        name = collection_name or self.collection_name
        qdrant_points: list[qmodels.PointStruct] = []

        for pt in points:
            point_id = pt.get("id", str(uuid.uuid4()))
            vector = pt.get("vector")
            if vector is None and self._embedding_fn:
                text = (pt.get("payload") or {}).get("content", "")
                vector = self._embedding_fn(text)

            if vector is None:
                continue

            qdrant_points.append(
                qmodels.PointStruct(
                    id=str(point_id),
                    vector=vector,
                    payload=pt.get("payload", {}),
                )
            )

        if not qdrant_points:
            return 0

        self._client.upsert(
            collection_name=name,
            points=qdrant_points,
        )
        return len(qdrant_points)

    def add_memory_item(
        self,
        item: MemoryItem,
        collection_name: Optional[str] = None,
    ) -> str:
        """将 MemoryItem 写入 Qdrant"""
        vector = None
        if self._embedding_fn:
            vector = self._embedding_fn(item.content)

        pt_id = str(uuid.uuid4())
        self._client.upsert(
            collection_name=collection_name or self.collection_name,
            points=[
                qmodels.PointStruct(
                    id=pt_id,
                    vector=vector or [0.0] * self.vector_size,
                    payload={
                        "memory_id": item.id,
                        "content": item.content,
                        "memory_type": item.memory_type,
                        "importance": item.importance,
                        "timestamp": item.timestamp.isoformat(),
                        "metadata": item.metadata,
                    },
                )
            ],
        )
        return pt_id

    # ── 搜索 ──────────────────────────────────────────────────

    def search(
        self,
        query: str | list[float],
        collection_name: Optional[str] = None,
        limit: int = 10,
        score_threshold: Optional[float] = None,
        payload_filter: Optional[dict] = None,
    ) -> list[dict[str, Any]]:
        """
        语义搜索。

        Args:
            query: 查询文本（自动嵌入）或原始向量
            limit: 返回数量
            score_threshold: 最低相似度阈值
            payload_filter: Qdrant 过滤条件
        Returns:
            [{"id", "score", "payload": {...}}, ...]
        """
        name = collection_name or self.collection_name

        # 文本 → 向量
        if isinstance(query, str):
            if self._embedding_fn:
                query_vector = self._embedding_fn(query)
            else:
                raise ValueError("未提供 embedding_fn，无法将文本转为向量")
        else:
            query_vector = query

        # 构建过滤条件
        qdrant_filter = None
        if payload_filter:
            conditions = []
            for key, value in payload_filter.items():
                conditions.append(
                    qmodels.FieldCondition(
                        key=key,
                        match=qmodels.MatchValue(value=value),
                    )
                )
            qdrant_filter = qmodels.Filter(
                must=conditions,
            )

        hits = self._client.search(
            collection_name=name,
            query_vector=query_vector,
            limit=limit,
            score_threshold=score_threshold,
            query_filter=qdrant_filter,
        )

        return [
            {
                "id": hit.id,
                "score": hit.score,
                "payload": hit.payload or {},
            }
            for hit in hits
        ]

    # ── 滚动遍历 ──────────────────────────────────────────────

    def scroll(
        self,
        collection_name: Optional[str] = None,
        limit: int = 100,
        payload_filter: Optional[dict] = None,
    ) -> list[dict[str, Any]]:
        """滚动获取所有点"""
        name = collection_name or self.collection_name
        qdrant_filter = None
        if payload_filter:
            conditions = [
                qmodels.FieldCondition(
                    key=k, match=qmodels.MatchValue(v)
                )
                for k, v in payload_filter.items()
            ]
            qdrant_filter = qmodels.Filter(must=conditions)

        hits, _ = self._client.scroll(
            collection_name=name,
            limit=limit,
            scroll_filter=qdrant_filter,
        )
        return [
            {
                "id": hit.id,
                "payload": hit.payload or {},
            }
            for hit in hits
        ]

    # ── 删除 ──────────────────────────────────────────────────

    def delete(
        self,
        point_id: str,
        collection_name: Optional[str] = None,
    ) -> bool:
        """删除单个点"""
        name = collection_name or self.collection_name
        self._client.delete(
            collection_name=name,
            points_selector=qmodels.PointIdsList(
                points=[point_id],
            ),
        )
        return True

    def delete_by_filter(
        self,
        payload_filter: dict,
        collection_name: Optional[str] = None,
    ) -> int:
        """按条件删除"""
        name = collection_name or self.collection_name
        conditions = [
            qmodels.FieldCondition(
                key=k, match=qmodels.MatchValue(v)
            )
            for k, v in payload_filter.items()
        ]
        result = self._client.delete(
            collection_name=name,
            points_selector=qmodels.FilterSelector(
                filter=qmodels.Filter(must=conditions),
            ),
        )
        return 1 if result else 0

    def count(self, collection_name: Optional[str] = None) -> int:
        """统计集合中的点数"""
        name = collection_name or self.collection_name
        info = self._client.get_collection(name)
        return info.points_count

    # ── 连接状态 ──────────────────────────────────────────────

    def is_connected(self) -> bool:
        """检查 Qdrant 是否可连接"""
        try:
            self._client.get_collections()
            return True
        except Exception:
            return False
