"""统一嵌入服务 — 为记忆检索提供文本向量化能力"""

import math
from abc import ABC, abstractmethod
from collections import Counter
from typing import Optional


# ═══════════════════════════════════════════════════════════════
# BaseEmbedding — 嵌入服务抽象基类
# ═══════════════════════════════════════════════════════════════
class BaseEmbedding(ABC):
    """嵌入服务基类"""

    dimension: int = 0          #? 向量维度

    @abstractmethod
    def embed(self, text: str) -> list[float]:
        """将单条文本转为向量"""
        ...

    def embed_batch(self, texts: list[str]) -> list[list[float]]:
        """批量文本转向量（默认逐个调用，子类可覆写优化）"""
        return [self.embed(t) for t in texts]

    def cosine_similarity(self, a: list[float], b: list[float]) -> float:
        """计算余弦相似度"""
        dot = sum(x * y for x, y in zip(a, b))
        na = math.sqrt(sum(x * x for x in a))
        nb = math.sqrt(sum(y * y for y in b))
        if na == 0 or nb == 0:
            return 0.0
        return dot / (na * nb)


# ═══════════════════════════════════════════════════════════════
# TFIDFEmbedding — 轻量级本地嵌入（无需外部 API）
# ═══════════════════════════════════════════════════════════════
class TFIDFEmbedding(BaseEmbedding):
    """
    基于 TF-IDF 的本地嵌入实现。
    不依赖任何外部服务，适合本地开发和演示。
    """

    dimension: int = 0  # 动态计算

    def __init__(self, max_features: int = 256):
        self.max_features = max_features
        self._vocab: dict[str, int] = {}       # 词 -> id
        self._idf: dict[str, float] = {}        # 词 -> idf 值
        self._doc_texts: list[str] = []          # 训练文档原文（用于短查询扩展）
        self._doc_vectors: list[list[float]] = []  # 训练文档向量
        self._fitted = False

    # ── 分词 ──────────────────────────────────────────────────
    def _tokenize(self, text: str) -> list[str]:
        """简单中文分词+英文小写分词"""
        tokens: list[str] = []
        buffer: list[str] = []

        for ch in text.lower():
            if ch.isalnum():
                buffer.append(ch)
            else:
                if buffer:
                    tokens.append("".join(buffer))
                    buffer = []
        if buffer:
            tokens.append("".join(buffer))

        # 拆分单字词（中文）-> 保留长度为1的中文字符，过滤其它单字符
        result: list[str] = []
        for t in tokens:
            if len(t) == 1 and not ('一' <= t <= '龿'):
                continue
            result.append(t)
        return result

    # ── 训练 ──────────────────────────────────────────────────
    def fit(self, texts: list[str]):
        """从文本集合中构建词表与 IDF"""
        doc_count = len(texts)
        df: Counter = Counter()

        for text in texts:
            tokens = set(self._tokenize(text))  # 每个文档只计一次
            for token in tokens:
                df[token] += 1

        # 按频率排序取 top max_features
        sorted_terms = [t for t, _ in df.most_common(self.max_features)]
        self._vocab = {term: idx for idx, term in enumerate(sorted_terms)}
        self.dimension = len(self._vocab)

        # 计算 IDF
        for term, freq in df.items():
            if term in self._vocab:
                self._idf[term] = math.log((doc_count + 1) / (freq + 1)) + 1.0

        self._fitted = True

        # 缓存训练文档向量（用于短查询的上下文扩展）
        self._doc_texts = texts
        self._doc_vectors = [self._vectorize(t) for t in texts]

    # ── 内部向量化（不包含上下文扩展） ────────────────────────
    def _vectorize(self, text: str) -> list[float]:
        """纯词袋向量化（无上下文扩展）"""
        tokens = self._tokenize(text)
        tf = Counter(tokens)
        vec = [0.0] * self.dimension
        for token, count in tf.items():
            if token in self._vocab:
                idx = self._vocab[token]
                vec[idx] = count * self._idf.get(token, 1.0)
        norm = math.sqrt(sum(v * v for v in vec))
        if norm > 0:
            vec = [v / norm for v in vec]
        return vec

    # ── 向量化 ────────────────────────────────────────────────
    def embed(self, text: str) -> list[float]:
        if not self._fitted or self.dimension == 0:
            return []

        # 1) 直接词袋向量
        vec = self._vectorize(text)

        # 2) 短查询（词数 ≤ 2）→ 用文档上下文扩展
        tokens = self._tokenize(text)
        if len(tokens) <= 2 and self._doc_vectors:
            query_terms = set(tokens)
            # 找到所有包含查询词的文档
            ctx_vectors = []
            for i, doc_text in enumerate(self._doc_texts):
                doc_terms = set(self._tokenize(doc_text))
                if query_terms & doc_terms:
                    ctx_vectors.append(self._doc_vectors[i])

            if ctx_vectors:
                # 平均上下文向量
                ctx = [0.0] * self.dimension
                for dv in ctx_vectors:
                    for j, val in enumerate(dv):
                        ctx[j] += val
                ctx = [v / len(ctx_vectors) for v in ctx]

                # 混合: 0.3 × 直接 + 0.7 × 上下文
                has_own = any(v != 0.0 for v in vec)
                if has_own:
                    vec = [0.3 * vec[j] + 0.7 * ctx[j] for j in range(self.dimension)]
                else:
                    vec = ctx

                # 归一化
                norm = math.sqrt(sum(v * v for v in vec))
                if norm > 0:
                    vec = [v / norm for v in vec]

        return vec


# ═══════════════════════════════════════════════════════════════
# FastEmbedEmbedding — Qdrant fastembed 本地嵌入
# ═══════════════════════════════════════════════════════════════
class FastEmbedEmbedding(BaseEmbedding):
    """
    基于 Qdrant fastembed 的本地嵌入实现。
    默认模型: BAAI/bge-small-en-v1.5（384 维）
    备选: sentence-transformers/all-MiniLM-L6-v2（384 维）

    依赖: pip install fastembed
    """

    dimension: int = 384  # all-MiniLM-L6-v2

    def __init__(self, model_name: str = "all-MiniLM-L6-v2", **kwargs):
        self.model_name = model_name
        self._kwargs = kwargs
        self._model = None

    def _lazy_init(self):
        if self._model is not None:
            return
        try:
            from fastembed import TextEmbedding
        except ImportError:
            raise ImportError(
                "fastembed 未安装，请执行: pip install fastembed"
            )
        self._model = TextEmbedding(model_name=self.model_name, **self._kwargs)
        self.dimension = self._model.model_config.dim

    def embed(self, text: str) -> list[float]:
        self._lazy_init()
        # fastembed.embed 返回生成器，取第一条结果
        return list(self._model.embed(text))[0]

    def embed_batch(self, texts: list[str]) -> list[list[float]]:
        self._lazy_init()
        return [list(v)[0] for v in self._model.embed(texts)]


# ═══════════════════════════════════════════════════════════════
# PlaceholderEmbedding — 供后续接入 API 嵌入时占位
# ═══════════════════════════════════════════════════════════════
class PlaceholderEmbedding(BaseEmbedding):
    """占位嵌入器，始终返回空向量，用于禁用嵌入的场景"""

    dimension: int = 0

    def embed(self, text: str) -> list[float]:
        return []


# ── 工厂 ──────────────────────────────────────────────────────
def create_embedding(model: str = "tfidf", **kwargs) -> BaseEmbedding:
    """创建嵌入服务实例"""
    if model == "tfidf":
        return TFIDFEmbedding(**kwargs)
    if model == "fastembed":
        return FastEmbedEmbedding(**kwargs)
    return PlaceholderEmbedding()
