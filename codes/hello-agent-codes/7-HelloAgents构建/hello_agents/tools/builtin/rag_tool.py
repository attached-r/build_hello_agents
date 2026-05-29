"""
RAG 工具 — 将 RAG 系统封装为 Tool，供 Agent 调用。

支持的操作:
  - query:     知识库查询（可选 MQE / HyDE 增强）
  - ingest:    导入文档到知识库
  - ingest_text: 直接导入文本
  - list:      列出知识库
  - create:    创建知识库
  - delete:    删除知识库
"""

import os
from typing import Any

from ..base import Tool, ToolParameter
from ...memory.rag.pipeline import RAGPipeline

class RAGTool(Tool):
    """RAG 知识检索工具"""

    def __init__(self, rag_pipeline: RAGPipeline):
        super().__init__(
            name="rag",
            description="一个知识检索工具。用于从知识库中检索信息和回答问题。"
        )
        self.rag = rag_pipeline

    def run(self, parameters: dict[str, Any]) -> str:
        action = parameters.get("action", "query")
        handler = getattr(self, f"_{action}", None)
        if handler is None:
            return (
                f"未知操作: {action}，支持: "
                f"query/ingest/ingest_text/list/create/delete"
            )
        return handler(**parameters)

    def get_parameters(self) -> list[ToolParameter]:
        return [
            ToolParameter(
                name="action",
                type="string",
                description="操作类型: query/ingest/ingest_text/list/create/delete",
            ),
            ToolParameter(
                name="query",
                type="string",
                description="查询内容（query 操作需要）",
                required=False,
            ),
            ToolParameter(
                name="collection",
                type="string",
                description="知识库名称",
                required=False,
            ),
            ToolParameter(
                name="file_path",
                type="string",
                description="文件路径（ingest 操作需要）",
                required=False,
            ),
            ToolParameter(
                name="text",
                type="string",
                description="要导入的文本内容（ingest_text 操作需要）",
                required=False,
            ),
            ToolParameter(
                name="use_mqe",
                type="string",
                description="是否启用多查询扩展 (true/false)",
                required=False,
            ),
            ToolParameter(
                name="use_hyde",
                type="string",
                description="是否启用假设文档嵌入 (true/false)",
                required=False,
            ),
            ToolParameter(
                name="name",
                type="string",
                description="知识库名称（create/delete 操作需要）",
                required=False,
            ),
        ]

    # ── 操作实现 ──────────────────────────────────────────────
    #? 查询知识库
    def _query(self, **params) -> str:
        query_text = params.get("query", "")
        if not query_text:
            return "❌ 查询内容不能为空"

        collection = params.get("collection")
        use_mqe = params.get("use_mqe", "false").lower() == "true"
        use_hyde = params.get("use_hyde", "false").lower() == "true"

        try:
            result = self.rag.query(
                query_text=query_text,
                collection_name=collection,
                use_mqe=use_mqe,
                use_hyde=use_hyde,
            )

            parts = [f"🔍 RAG 查询结果:\n"]

            if result.expanded_queries:
                parts.append(
                    "扩展查询:\n" + "\n".join(
                        f"  · {q}" for q in result.expanded_queries
                    ) + "\n"
                )

            parts.append(f"检索到 {len(result.chunks)} 个相关文档块:\n")
            for i, c in enumerate(result.chunks[:5]):
                source = c.get("source", "未知")
                score = c.get("score", 0)
                content = c["content"][:150]
                parts.append(
                    f"  [{i+1}] ({source}, 相关度:{score:.3f})\n"
                    f"      {content}...\n"
                )

            if result.answer:
                parts.append(f"\n💡 回答:\n{result.answer}")

            return "\n".join(parts)

        except Exception as e:
            return f"❌ 查询失败: {e}"
        
    #? 导入文件到知识库
    def _ingest(self, **params) -> str:
        file_path = params.get("file_path", "")
        if not file_path:
            return "❌ 文件路径不能为空"
        if not os.path.exists(file_path):
            return f"❌ 文件不存在: {file_path}"

        collection = params.get("collection")

        try:
            count = self.rag.ingest(file_path, collection_name=collection)
            return f"✅ 已导入 '{os.path.basename(file_path)}'，共 {count} 个分块"
        except Exception as e:
            return f"❌ 导入失败: {e}"
        
    #? 导入文本到知识库
    def _ingest_text(self, **params) -> str:
        text = params.get("text", "")
        if not text:
            return "❌ 文本不能为空"

        source = params.get("source", "text_input")
        collection = params.get("collection")

        try:
            count = self.rag.ingest_text(text, source=source, collection_name=collection)
            return f"✅ 已导入文本，共 {count} 个分块"
        except Exception as e:
            return f"❌ 导入失败: {e}"
        
    #? 获取知识库列表
    def _list(self, **params) -> str:
        try:
            bases = self.rag.list_knowledge_bases()
            if not bases:
                return "💡 暂无知识库"
            return "📚 知识库列表:\n" + "\n".join(f"  · {b}" for b in bases)
        except Exception as e:
            return f"❌ 获取列表失败: {e}"
        
    #? 创建知识库
    def _create(self, **params) -> str:
        name = params.get("name", "")
        if not name:
            return "❌ 知识库名称不能为空"
        try:
            ok = self.rag.create_knowledge_base(name)
            return f"✅ 已创建知识库 '{name}'" if ok else f"⚠️ 知识库 '{name}' 已存在"
        except Exception as e:
            return f"❌ 创建失败: {e}"
        
    #? 删除知识库
    def _delete(self, **params) -> str:
        name = params.get("name", "")
        if not name:
            return "❌ 知识库名称不能为空"
        try:
            ok = self.rag.delete_knowledge_base(name)
            return f"✅ 已删除知识库 '{name}'" if ok else f"❌ 知识库 '{name}' 不存在"
        except Exception as e:
            return f"❌ 删除失败: {e}"
