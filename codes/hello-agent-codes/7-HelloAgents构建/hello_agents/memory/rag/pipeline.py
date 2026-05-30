"""
RAG 管道 — 端到端检索增强生成。

流程:
  用户查询
    ├─ [可选] MQE 多查询扩展（LLM 生成子问题）
    ├─ [可选] HyDE 假设文档嵌入（LLM 生成假设回答）
    ├─ Qdrant 向量检索
    ├─ 重排序（语义 × 0.6 + 时间 × 0.2 + 标题 × 0.2）
    ├─ 构建上下文
    └─ LLM 生成回答
"""

import json
import os
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Optional

from ..embedding import BaseEmbedding, create_embedding
from ..storage.qdrant_store import QdrantVectorStore
from .document import DocumentProcessor, DocumentChunk


@dataclass
class RAGQueryResult:
    """RAG 查询结果"""

    query: str
    chunks: list[dict[str, Any]] = field(default_factory=list)
    answer: str = ""
    expanded_queries: list[str] = field(default_factory=list)

    @property  #? 上下文属性
    def context(self) -> str:
        """格式化后的上下文字符串"""
        lines = [f"用户问题: {self.query}\n"]
        if self.expanded_queries:
            lines.append("扩展查询:\n" + "\n".join(
                f"  · {q}" for q in self.expanded_queries
            ) + "\n")
        lines.append("相关资料:\n")
        for i, c in enumerate(self.chunks):
            source = c.get("source", "未知")
            lines.append(f"  [{i+1}] ({source}) {c['content'][:200]}...\n")
        return "\n".join(lines)

    def to_dict(self) -> dict[str, Any]:
        return {
            "query": self.query,
            "chunks": self.chunks,
            "answer": self.answer,
            "expanded_queries": self.expanded_queries,
        }


class RAGPipeline:
    """
    RAG 端到端管道。

    Args:
        llm: LLM 实例，需要实现 think(messages) -> str
        embedding: 嵌入模型（默认 FastEmbed）
        collection_name: Qdrant 集合名（默认 knowledge_base）
        top_k: 默认返回数
        score_threshold: 最低相似度阈值
        qdrant_url/qdrant_api_key: Qdrant 云端配置
    """

    def __init__(
        self,
        llm: Any,
        embedding: Optional[BaseEmbedding] = None,
        collection_name: str = "knowledge_base",
        top_k: int = 5,
        score_threshold: float = 0.0,
        qdrant_url: Optional[str] = None,
        qdrant_api_key: Optional[str] = None,
    ):
        self.llm = llm
        self.embedding = embedding or create_embedding("fastembed")
        self.top_k = top_k
        self.score_threshold = score_threshold
        self.doc_processor = DocumentProcessor()

        # 初始化 Qdrant 向量存储
        try:
            self.vector_store = QdrantVectorStore(
                collection_name=collection_name,
                url=qdrant_url,
                api_key=qdrant_api_key,
                embedding_fn=self.embedding.embed,
            )
        except ImportError:
            self.vector_store = None

        # 确保集合存在
        if self.vector_store:
            self.vector_store.create_collection(collection_name)

    # ── 核心查询 ──────────────────────────────────────────────

    def query(
        self,
        query_text: str,
        collection_name: Optional[str] = None,
        use_mqe: bool = False,
        use_hyde: bool = False,
    ) -> RAGQueryResult:
        """执行 RAG 查询"""
        result = RAGQueryResult(query=query_text)
        queries = [query_text]

        # MQE 多查询扩展
        if use_mqe:
            expanded = self._expand_queries(query_text)
            result.expanded_queries = expanded
            queries.extend(expanded)

        # HyDE 假设文档嵌入
        if use_hyde:
            hypo = self._hypothetical_document(query_text)
            if hypo:
                queries.append(hypo)

        # 向量检索
        all_chunks: list[dict] = []
        seen: set[str] = set()

        for q in queries:
            chunks = self._retrieve(q, collection_name)
            for c in chunks:
                key = c["content"][:100]  # 按内容前 100 字符去重
                if key not in seen:
                    seen.add(key)
                    all_chunks.append(c)

        # 重排序
        all_chunks = self._rerank(all_chunks)
        result.chunks = all_chunks[:self.top_k]

        # 生成回答
        if result.chunks:
            result.answer = self._generate(query_text, result)

        return result

    # ── 文档导入 ──────────────────────────────────────────────

    def ingest(
        self,
        file_path: str,
        collection_name: Optional[str] = None,
    ) -> int:
        """导入文件到知识库"""
        text = self.doc_processor.parse(file_path)
        return self._store_chunks(
            self.doc_processor.chunk(text, source=os.path.basename(file_path)),
            collection_name,
        )

    def ingest_text(
        self,
        text: str,
        source: str = "text_input",
        collection_name: Optional[str] = None,
    ) -> int:
        """直接导入文本"""
        return self._store_chunks(
            self.doc_processor.chunk(text, source=source),
            collection_name,
        )

    # ── 知识库管理 ────────────────────────────────────────────

    def list_knowledge_bases(self) -> list[str]:
        """列出所有知识库"""
        if not self.vector_store:
            return []
        return self.vector_store.list_collections()

    def create_knowledge_base(self, name: str) -> bool:
        """创建知识库"""
        if not self.vector_store:
            return False
        return self.vector_store.create_collection(name)

    def delete_knowledge_base(self, name: str) -> bool:
        """删除知识库"""
        if not self.vector_store:
            return False
        return self.vector_store.delete_collection(name)

    # ── 内部方法 ──────────────────────────────────────────────

    def _retrieve(self, query: str, collection_name: Optional[str] = None) -> list[dict]:
        """向量检索"""
        if not self.vector_store:
            return []

        try:
            results = self.vector_store.search(
                query=query,
                collection_name=collection_name,
                limit=self.top_k * 2,
                score_threshold=self.score_threshold,
            )
            chunks = []
            for r in results:
                payload = r.get("payload", {})
                chunks.append({
                    "content": payload.get("content", ""),
                    "source": payload.get("source", "unknown"),
                    "heading": payload.get("heading", ""),
                    "heading_level": payload.get("heading_level", 0),
                    "timestamp": payload.get("timestamp", ""),
                    "score": r.get("score", 0),
                })
            return chunks
        except Exception:
            return []

    def _rerank(self, chunks: list[dict]) -> list[dict]:
        """重排序"""
        now = datetime.now()

        def _compute_score(c: dict) -> float:
            semantic = c.get("score", 0)
            # 时间近因加分
            ts_str = c.get("timestamp", "")
            recency_bonus = 0.0
            if ts_str:
                try:
                    ts = datetime.fromisoformat(ts_str)
                    age_days = (now - ts).total_seconds() / 86400
                    recency_bonus = 1.0 / (1.0 + age_days * 0.1)
                except ValueError:
                    pass
            # 标题加分
            heading_bonus = 0.3 if c.get("heading") else 0.0
            return semantic * 0.6 + recency_bonus * 0.2 + heading_bonus * 0.2

        chunks.sort(key=_compute_score, reverse=True)
        return chunks

    def _expand_queries(self, query: str) -> list[str]:
        """MQE: 用 LLM 生成多个语义等价的子问题"""
        prompt = (
            f"你是一个专业的查询扩展助手。请将以下用户问题改写为 3 个"
            f"语义等价的子问题（每个一行），帮助从知识库中检索更多相关信息。\n\n"
            f"用户问题: {query}\n\n"
            f"扩展查询:"
        )
        try:
            resp = self.llm.think([
                {"role": "system", "content": "你是一个查询扩展助手。"},
                {"role": "user", "content": prompt},
            ], temperature=0.3)
            return [line.strip().strip("- ") for line in resp.strip().split("\n") if line.strip()]
        except Exception:
            return []

    def _hypothetical_document(self, query: str) -> Optional[str]:
        """HyDE: 用 LLM 生成假设性回答文档"""
        prompt = (
            f"请根据以下问题，生成一个假设性的回答段落，作为检索时的虚拟文档。\n\n"
            f"问题: {query}\n\n"
            f"假设性回答:"
        )
        try:
            return self.llm.think([
                {"role": "system", "content": "你是一个文档生成助手。"},
                {"role": "user", "content": prompt},
            ], temperature=0.3)
        except Exception:
            return None

    def _generate(self, query: str, result: RAGQueryResult) -> str:
        """LLM 基于检索结果生成回答"""
        context_lines = []
        for i, c in enumerate(result.chunks):
            source = c.get("source", "未知")
            context_lines.append(f"[{i+1}] (来源: {source})\n{c['content']}\n")

        context = "\n".join(context_lines)
        prompt = (
            f"你是一个知识问答助手。请基于以下资料回答用户问题。\n"
            f"如果资料不足以回答问题，请如实说明。\n\n"
            f"===== 资料 =====\n{context}\n"
            f"===== 问题 =====\n{query}\n\n"
            f"回答:"
        )

        try:
            return self.llm.think([
                {"role": "system", "content": "你是一个严谨的知识问答助手。"},
                {"role": "user", "content": prompt},
            ], temperature=0.3)
        except Exception as e:
            return f"回答生成失败: {e}"

    def _store_chunks(
        self,
        chunks: list[DocumentChunk],
        collection_name: Optional[str] = None,
    ) -> int:
        """将分块存入 Qdrant"""
        if not self.vector_store:
            return 0

        name = collection_name or self.vector_store.collection_name
        self.vector_store.create_collection(name)

        points = [
            {
                "payload": {
                    "content": c.content,
                    "source": c.source,
                    "heading": c.heading,
                    "heading_level": c.heading_level,
                    "chunk_index": c.chunk_index,
                    "chunk_id": c.chunk_id,
                    "timestamp": datetime.now().isoformat(),
                },
            }
            for c in chunks
        ]
        return self.vector_store.upsert(points, collection_name=name)
