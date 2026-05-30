"""
上下文构建器 —— GSSC 流水线：Gather → Select → Structure → Compress

将 Agent 运行过程中分散的信息源（系统指令、记忆检索、RAG 知识库、
对话历史、自定义数据）汇集为结构化的上下文模板，供 LLM 消费。

GSSC 是本框架上下文工程的核心设计模式，四个阶段职责分明：
  1. Gather  （收集）    — 从多源无差别汇集候选信息包
  2. Select  （选择）    — 评分 + 排序 + 贪心裁剪，选出高价值信息
  3. Structure（结构化） — 按稳定模板组织为 LLM 友好的格式
  4. Compress（压缩）    — 超限时兜底压缩，保证上下文不溢出

用法:
    builder = ContextBuilder(config, memory=memory_mgr, rag=rag_pipe)
    context_str = builder.build(
        user_query="如何优化 Python 内存?",
        conversation_history=history,
        system_instructions="你是一位 Python 性能优化专家。",
    )
    # → 返回结构化模板字符串，可直接放入 system message
"""

import logging
import math
from dataclasses import dataclass
from datetime import datetime
from typing import Any, Dict, List, Optional

from hello_agents.core.message import Message


# ═══════════════════════════════════════════════════════════════════════════════
# ContextPacket — 候选信息包
# ═══════════════════════════════════════════════════════════════════════════════

@dataclass
class ContextPacket:
    """候选信息包 —— GSSC 流水线中流动的基本数据单元。

    每个 ContextPacket 代表一条候选信息，包含内容、时间戳、token 估算、
    相关性分数和元数据。流水线各阶段通过 metadata 中的 type 标签
    区分信息来源（system_instruction / memory / rag / conversation_history）。

    Attributes:
        content:          信息正文
        timestamp:        信息产生时间（用于新近性评分）
        token_count:      Token 数量估算值（4 字符 ≈ 1 token）
        relevance_score:  语义相关性分数，范围 [0.0, 1.0]
        metadata:         元数据字典，至少应包含 "type" 键
    """
    content: str
    timestamp: datetime
    token_count: int
    relevance_score: float = 0.5
    metadata: Optional[Dict[str, Any]] = None

    def __post_init__(self):
        """初始化后处理：确保 metadata 存在、relevance_score 合法。"""
        if self.metadata is None:
            self.metadata = {}
        # 将相关性分数钳制在 [0, 1] 区间
        self.relevance_score = max(0.0, min(1.0, self.relevance_score))


# ═══════════════════════════════════════════════════════════════════════════════
# ContextConfig — 上下文构建配置
# ═══════════════════════════════════════════════════════════════════════════════

@dataclass
class ContextConfig:
    """上下文构建配置 —— 控制 GSSC 流水线的各项参数。

    核心参数说明:
      max_tokens         控制上下文窗口总预算（不是 LLM 的 max_tokens，而是
                         构建器内部用于裁剪的预算）。
      reserve_ratio      为系统指令预留的 token 比例，确保角色设定不被裁剪。
      min_relevance      相关性门槛，低于此值的记忆/RAG 结果被直接丢弃。
      recency_weight / relevance_weight
                         新近性与相关性的相对权重，两者之和必须为 1.0。
      enable_compression 是否在 Structure 后启用 Compress 兜底压缩。

    Attributes:
        max_tokens:          上下文最大 token 预算
        reserve_ratio:       系统指令预留比例 [0.0, 1.0]
        min_relevance:       最低相关性阈值，低于此值的包被过滤
        enable_compression:  是否启用 Compress 阶段压缩
        recency_weight:      新近性评分权重（与 relevance_weight 之和为 1）
        relevance_weight:    相关性评分权重
        memory_search_limit: 单次记忆检索最大条数
        rag_search_limit:    单次 RAG 检索最大条数
        recent_history_count:保留的最近对话历史条数
        memory_min_importance:记忆最低重要性阈值
    """
    # ── 通用参数 ──
    max_tokens: int = 3000
    reserve_ratio: float = 0.2
    min_relevance: float = 0.1
    enable_compression: bool = True

    # ── 评分权重（须满足 recency_weight + relevance_weight == 1.0） ──
    recency_weight: float = 0.3
    relevance_weight: float = 0.7

    # ── 各源限制 ──
    memory_search_limit: int = 10
    rag_search_limit: int = 5
    recent_history_count: int = 5
    memory_min_importance: float = 0.3

    def __post_init__(self):
        """参数校验：确保权重和为 1、比例在合法区间。"""
        assert 0.0 <= self.reserve_ratio <= 1.0, \
            f"reserve_ratio 必须在 [0, 1] 范围内，当前为 {self.reserve_ratio}"
        assert 0.0 <= self.min_relevance <= 1.0, \
            f"min_relevance 必须在 [0, 1] 范围内，当前为 {self.min_relevance}"
        # 权重之和应恰好为 1.0（容忍浮点误差 1e-6）
        weight_sum = self.recency_weight + self.relevance_weight
        assert abs(weight_sum - 1.0) < 1e-6, (
            f"recency_weight({self.recency_weight}) + relevance_weight({self.relevance_weight})"
            f" 必须等于 1.0，当前为 {weight_sum}"
        )


# ═══════════════════════════════════════════════════════════════════════════════
# ContextBuilder — GSSC 流水线实现
# ═══════════════════════════════════════════════════════════════════════════════

class ContextBuilder:
    """GSSC 流水线构建器 —— 将分散信息汇集为结构化上下文。

    四阶段流水线：
        Gather ──→ Select ──→ Structure ──→ Compress ──→ str
          │           │            │              │
          ▼           ▼            ▼              ▼
        汇集候选   评分+选择    组织为模板   超限时压缩

    支持两种输出格式：
      1. build()            → str                : 结构化模板（GSSC 标准输出）
      2. build_to_dicts()   → List[Dict[str,str]]: OpenAI 兼容消息列表

    Args:
        config: 上下文构建配置，不传则使用 ContextConfig() 默认值
        memory: MemoryManager 实例（非 MemoryTool），提供 search() 接口
        rag:    RAGPipeline 实例（非 RAGTool），提供 query() 接口
    """

    def __init__(
        self,
        config: Optional["ContextConfig"] = None,
        memory: Optional[Any] = None,
        rag: Optional[Any] = None,
    ):
        self.config = config or ContextConfig()
        self.memory = memory   # MemoryManager.search(query, limit) → List[MemoryItem]
        self.rag = rag         # RAGPipeline.query(query_text) → RAGQueryResult
        self._logger = logging.getLogger("hello_agents.context.ContextBuilder")

    # ═══════════════════════════════════════════════════════════════════════════
    # 工具方法
    # ═══════════════════════════════════════════════════════════════════════════

    @staticmethod
    def _count_tokens(text: str) -> int:
        """估算 token 数量。

        采用 4 字符 ≈ 1 token 的粗略估算规则。
        生产环境可替换为 tiktoken 等精确分词器。
        """
        return max(1, len(text) // 4)

    @staticmethod
    def _calc_jaccard_similarity(text1: str, text2: str) -> float:
        """计算 Jaccard 相似度 —— 基于词集合的交并比。

        Jaccard(text1, text2) = |words(text1) ∩ words(text2)|
                              / |words(text1) ∪ words(text2)|

        用于衡量两段文本的词级重叠程度，作为内容相关性的快速估算。
        若任一段落为空，返回 0.0。
        """
        # 分词：按空白符切分后取集合
        set1 = set(text1.split())
        set2 = set(text2.split())

        # 空集合无法计算相似度
        if not set1 or not set2:
            return 0.0

        intersection = set1 & set2  # 交集
        union = set1 | set2         # 并集

        return len(intersection) / len(union) if union else 0.0

    @staticmethod
    def _calc_recency_score(timestamp: datetime, now: Optional[datetime] = None) -> float:
        """计算新近性评分 —— 指数衰减模型。

        score = exp(-hours / 24)

        衰减半衰期约为 24 小时：
          - 刚发生的事件 → score ≈ 1.0
          - 24 小时后    → score ≈ 0.37
          - 7 天后       → score ≈ 0.001（几乎无影响）

        这种指数衰减比线性衰减更符合人类记忆遗忘曲线。
        """
        if now is None:
            now = datetime.now()
        delta_hours = (now - timestamp).total_seconds() / 3600
        return math.exp(-delta_hours / 24.0)

    # ═══════════════════════════════════════════════════════════════════════════
    # 第 1 阶段：Gather（收集）
    # ═══════════════════════════════════════════════════════════════════════════

    def gather(
        self,
        user_query: str,
        conversation_history: Optional[List["Message"]] = None,
        system_instructions: Optional[str] = None,
        custom_packets: Optional[List["ContextPacket"]] = None,
    ) -> List["ContextPacket"]:
        """Gather 阶段：从多个信息源汇集候选 ContextPacket。

        汇集来源（按添加顺序）：
          1. 系统指令        → type="system_instruction"，最高优先级
          2. 记忆检索        → type="memory"，从 MemoryManager.search() 获取
          3. RAG 检索        → type="rag"，从 RAGPipeline.query() 获取
          4. 对话历史        → type="conversation_history"，仅保留最近 N 条
          5. 自定义信息包    → 原样加入

        每个外部来源都有 try-except 容错，单源失败不影响其他源。

        Args:
            user_query:         用户当前问题（用于检索记忆和 RAG）
            conversation_history:对话历史 Message 列表
            system_instructions: 系统指令文本
            custom_packets:     调用方自行构造的信息包列表

        Returns:
            未经过滤的候选信息包列表
        """
        packets: List["ContextPacket"] = []

        # ── 1. 系统指令 ──────────────────────────────────────────────
        # 系统指令定义 Agent 的角色和行为边界，是最高优先级信息。
        # 赋予 relevance_score=1.0 确保它在 Select 阶段不会被过滤。
        if system_instructions:
            packets.append(ContextPacket(
                content=system_instructions,
                timestamp=datetime.now(),
                token_count=self._count_tokens(system_instructions),
                relevance_score=1.0,
                metadata={"type": "system_instruction", "priority": "high"},
            ))

        # ── 2. 记忆检索 ──────────────────────────────────────────────
        # 从记忆系统中检索与当前查询相关的历史记忆。
        # 绕过 MemoryTool（返回格式化字符串），直接调用
        # MemoryManager.search() 获取结构化 MemoryItem。
        if self.memory:
            try:
                items = self.memory.search(
                    query=user_query,
                    limit=self.config.memory_search_limit,
                )
                for item in items:
                    # 跳过重要性低于阈值的记忆
                    if item.importance < self.config.memory_min_importance:
                        continue

                    # importance 本身已是 [0,1] 的语义重要性评分，
                    # 直接映射为 relevance_score，略做放大以便高重要性记忆更易被选中
                    score = min(1.0, item.importance * 1.2)

                    packets.append(ContextPacket(
                        content=item.content,
                        timestamp=item.timestamp,
                        token_count=self._count_tokens(item.content),
                        relevance_score=score,
                        metadata={
                            "type": "memory",
                            "memory_type": item.memory_type,
                            "memory_id": item.id,
                            "importance": item.importance,
                        },
                    ))
            except Exception as e:
                # 记忆检索失败不应阻断整个流水线，记录警告后继续
                self._logger.warning("Gather: 记忆检索失败 —— %s", e)

        # ── 3. RAG 检索 ──────────────────────────────────────────────
        # 从外部知识库检索与当前查询相关的知识片段。
        # 绕过 RAGTool（返回格式化字符串），直接调用
        # RAGPipeline.query() 获取结构化 Chunk 列表。
        if self.rag:
            try:
                result = self.rag.query(query_text=user_query)
                # 取前 N 个最相关的 chunk
                for chunk in result.chunks[:self.config.rag_search_limit]:
                    chunk_score = chunk.get("score", 0.5)
                    packets.append(ContextPacket(
                        content=chunk["content"],
                        timestamp=self._parse_chunk_timestamp(chunk),
                        token_count=self._count_tokens(chunk["content"]),
                        relevance_score=chunk_score,
                        metadata={
                            "type": "rag",
                            "source": chunk.get("source", "unknown"),
                            "score": chunk_score,
                        },
                    ))
            except Exception as e:
                self._logger.warning("Gather: RAG 检索失败 —— %s", e)

        # ── 4. 对话历史 ──────────────────────────────────────────────
        # 仅保留最近 N 条对话历史，避免上下文被旧消息淹没。
        # 越新的消息相关性越高（relevance 呈线性递增趋势）。
        if conversation_history:
            recent = conversation_history[-self.config.recent_history_count:]
            n = len(recent)
            for i, msg in enumerate(recent):
                # relevance 从 0.4 + 0.4/n 线性增长到 0.8
                # 最新一条消息的 relevance = 0.8，最旧一条 ≈ 0.4
                rel = 0.4 + 0.4 * (i + 1) / n if n > 0 else 0.5
                packets.append(ContextPacket(
                    content=msg.content,
                    timestamp=getattr(msg, "timestamp", datetime.now()),
                    token_count=self._count_tokens(msg.content),
                    relevance_score=rel,
                    metadata={
                        "type": "conversation_history",
                        "role": getattr(msg, "role", "user"),
                    },
                ))

        # ── 5. 自定义信息包 ──────────────────────────────────────────
        # 由调用方自行构造，例如 NoteTool 的结构化笔记、
        # TerminalTool 的探索结果等。
        if custom_packets:
            packets.extend(custom_packets)

        self._logger.info("Gather: 从 %d 个来源汇集了 %d 个候选信息包",
                          1 + bool(self.memory) + bool(self.rag) + bool(conversation_history),
                          len(packets))
        return packets

    # ═══════════════════════════════════════════════════════════════════════════
    # 第 2 阶段：Select（选择）—— 评分 + 排序 + 贪心裁剪
    # ═══════════════════════════════════════════════════════════════════════════

    def select(
        self,
        packets: List["ContextPacket"],
        user_query: str = "",
    ) -> List["ContextPacket"]:
        """Select 阶段：对候选包进行评分、过滤、贪心选择。

        本阶段包含三个子步骤：
          1. 评分（Scoring）
             - 相关性评分: 使用 Jaccard 相似度（内容与用户查询的词重叠率）
             - 新近性评分: 指数衰减模型（24 小时半衰期）
             - 综合分: relevance_weight × relevance_score
                     + recency_weight × recency_score
          2. 过滤（Filtering）
             - 系统指令包（type="system_instruction"）始终保留
             - 低于 min_relevance 的包被丢弃
          3. 选择（Selection）
             - 系统指令占用 reserve_ratio 预留的 token 预算
             - 其余包按综合分从高到低排序
             - 贪心选取直到耗尽 max_tokens 预算

        Args:
            packets:    Gather 阶段产出的候选包列表
            user_query: 用户当前查询（用于计算 Jaccard 相似度）

        Returns:
            经过评分、过滤、排序、裁剪后的选中包列表
        """
        if not packets:
            return []

        now = datetime.now()

        # ── 分离系统指令包和其他包 ──────────────────────────────────
        # 系统指令包走特殊通道：不参与评分、不过滤、有独立预算
        sys_packets: List["ContextPacket"] = []
        other_packets: List["ContextPacket"] = []
        for p in packets:
            if p.metadata.get("type") == "system_instruction":
                sys_packets.append(p)
            else:
                other_packets.append(p)

        # ── 评分：为每个非系统包计算综合分 ──────────────────────────
        for p in other_packets:
            # ① 相关性评分（Jaccard 相似度）
            #    用内容与用户查询的词重叠率估算语义相关性
            if user_query and p.content:
                jaccard = self._calc_jaccard_similarity(p.content, user_query)
            else:
                # 没有查询或内容为空时，回退到 packet 自带的 relevance_score
                jaccard = p.relevance_score

            # ② 新近性评分（指数衰减）
            recency = self._calc_recency_score(p.timestamp, now)

            # ③ 综合分 = 加权求和
            composite = (
                jaccard * self.config.relevance_weight
                + recency * self.config.recency_weight
            )

            # 将各项分数写入 metadata，便于调试和分析
            p.metadata["jaccard_score"] = round(jaccard, 4)
            p.metadata["recency_score"] = round(recency, 4)
            p.metadata["composite_score"] = round(composite, 4)

        # ── 过滤低相关度包 ──────────────────────────────────────────
        # min_relevance 是比较 relevance_score（原始语义相关性），
        # 而非 composite_score（综合分），因为新近性可能补偿低相关性
        filtered = [p for p in other_packets
                     if p.relevance_score >= self.config.min_relevance]

        # ── 按综合分降序排列 ────────────────────────────────────────
        filtered.sort(key=lambda p: p.metadata.get("composite_score", 0), reverse=True)

        # ── 贪心选择：在预算内取高分包 ──────────────────────────────
        cfg = self.config
        sys_budget = int(cfg.max_tokens * cfg.reserve_ratio)

        # 系统指令包占用预留预算
        sys_tokens = sum(p.token_count for p in sys_packets)
        if sys_tokens > sys_budget:
            self._logger.warning(
                "Select: 系统指令超预算 (%d > %d)，可能被截断",
                sys_tokens, sys_budget,
            )

        selected: List["ContextPacket"] = list(sys_packets)
        used_tokens = sys_tokens

        for p in filtered:
            if used_tokens + p.token_count > cfg.max_tokens:
                self._logger.debug(
                    "Select: 跳过 '%s...' (token=%d, composite=%.4f) —— 预算不足",
                    p.content[:30], p.token_count,
                    p.metadata.get("composite_score", 0),
                )
                continue
            selected.append(p)
            used_tokens += p.token_count

        self._logger.info(
            "Select: %d 个候选包 → %d 个选中 (%d / %d tokens, 综合分最高=%.4f)",
            len(packets), len(selected), used_tokens, cfg.max_tokens,
            selected[-1].metadata.get("composite_score", 0) if selected else 0,
        )
        return selected

    # ═══════════════════════════════════════════════════════════════════════════
    # 第 3 阶段：Structure（结构化）
    # ═══════════════════════════════════════════════════════════════════════════

    def structure(
        self,
        selected_packets: List["ContextPacket"],
        user_query: str,
    ) -> str:
        """Structure 阶段：将选中的信息包组织为结构化模板。

        模板分为五个清晰的分区，LLM 能够准确理解每条信息的用途：

          [Role & Policies]  —— 系统指令，定义 Agent 角色和行为边界
          [Task]              —— 用户当前的问题/任务
          [Evidence]          —— 检索到的证据（记忆 + RAG 知识库）
          [Context]           —— 对话历史等上下文信息
          [Output]            —— 回答指令

        每个 [type] 标签让 LLM 能区分信息来源，减少注意力分散。
        Evidence 中的条目带来源标签（[记忆]/[知识库]）和相关性分数。

        Args:
            selected_packets: Select 阶段选中的包列表
            user_query:       用户当前查询

        Returns:
            结构化的上下文字符串
        """
        # ── 按类型分组 ──────────────────────────────────────────────
        system_blocks: List[str] = []   # [Role & Policies]
        evidence_blocks: List[str] = [] # [Evidence]
        context_blocks: List[str] = []  # [Context]

        for packet in selected_packets:
            ptype = packet.metadata.get("type", "general")

            if ptype == "system_instruction":
                # 系统指令 → [Role & Policies]
                system_blocks.append(packet.content)

            elif ptype in ("memory", "rag"):
                # 记忆和 RAG → [Evidence]，带中文来源标签
                source_tag = {"memory": "记忆", "rag": "知识库"}.get(ptype, ptype)

                # 获取相关性分数（优先用 composite_score，其次 importance/score）
                importance = packet.metadata.get(
                    "composite_score",
                    packet.metadata.get("importance",
                    packet.metadata.get("score", "")),
                )

                tag = f"[{source_tag}"
                if importance:
                    tag += f", 相关度: {importance:.2f}"
                tag += "]"

                evidence_blocks.append(f"{tag}\n{packet.content}")

            elif ptype == "conversation_history":
                # 对话历史 → [Context]，带角色标签
                role = packet.metadata.get("role", "user")
                context_blocks.append(f"[{role}]\n{packet.content}")

            else:
                # 其他类型统一归入 [Context]
                context_blocks.append(f"[{ptype}]\n{packet.content}")

        # ── 组装模板 ────────────────────────────────────────────────
        sections: List[str] = []

        # [Role & Policies]
        if system_blocks:
            sections.append("[Role & Policies]\n" + "\n".join(system_blocks))

        # [Task]
        sections.append(f"[Task]\n{user_query}")

        # [Evidence] —— 多条证据用 "---" 分隔
        if evidence_blocks:
            sections.append("[Evidence]\n" + "\n---\n".join(evidence_blocks))

        # [Context]
        if context_blocks:
            sections.append("[Context]\n" + "\n".join(context_blocks))

        # [Output] —— 固定的回答指令
        sections.append("[Output]\n请基于以上信息，提供准确、有据的回答。")

        return "\n\n".join(sections)

    # ═══════════════════════════════════════════════════════════════════════════
    # 第 4 阶段：Compress（压缩）
    # ═══════════════════════════════════════════════════════════════════════════

    def compress(
        self,
        structured_context: str,
        _selected_packets: List["ContextPacket"],
        user_query: str,
    ) -> str:
        """Compress 阶段：结构化上下文超限时的兜底压缩。

        压缩策略（优先级从低到高执行）：
          1. 若未超限或 enable_compression=False，直接返回
          2. 裁剪 [Context] 部分（对话历史），替换为简短标记
          3. 如仍超限，裁剪 [Evidence] 部分（保留前半部分）
          4. 最后兜底：直接按字符截断

        压缩是"兜底"手段而非常规流程。理想情况下应通过调整
        max_tokens 和 min_relevance 来避免触发压缩。

        Args:
            structured_context: Structure 阶段产出的模板字符串
            selected_packets:   Select 阶段选中的包列表（暂未使用，保留接口）
            user_query:         用户当前查询（用于重建模板）

        Returns:
            压缩后的上下文字符串
        """
        # 若压缩功能关闭，直接返回
        if not self.config.enable_compression:
            return structured_context

        token_count = self._count_tokens(structured_context)
        # 未超限，无需压缩
        if token_count <= self.config.max_tokens:
            return structured_context

        self._logger.warning(
            "Compress: 上下文超限 (%d > %d tokens)，执行压缩",
            token_count, self.config.max_tokens,
        )

        # ── 解析结构化模板为各节内容 ──────────────────────────────
        sections = {"role": "", "task": "", "evidence": "", "context": "", "output": ""}
        current_key = None

        for line in structured_context.split("\n"):
            stripped = line.strip()
            if stripped == "[Role & Policies]":
                current_key = "role"
            elif stripped == "[Task]":
                current_key = "task"
            elif stripped == "[Evidence]":
                current_key = "evidence"
            elif stripped == "[Context]":
                current_key = "context"
            elif stripped == "[Output]":
                current_key = "output"
            elif current_key:
                sections[current_key] += line + "\n"

        # 各节去除首尾空白
        for k in sections:
            sections[k] = sections[k].strip()

        # ── 压缩策略 1：裁剪 [Context] 部分 ─────────────────────────
        if sections["context"] and self._count_tokens(structured_context) > self.config.max_tokens:
            self._logger.info("Compress: 裁剪 [Context] 部分")
            sections["context"] = "（上下文历史已压缩，保留关键信息）"

        # ── 压缩策略 2：裁剪 [Evidence] 部分（保留前半段） ─────────
        rebuilt = self._rebuild_sections(sections, user_query)
        if sections["evidence"] and self._count_tokens(rebuilt) > self.config.max_tokens:
            self._logger.info("Compress: 裁剪 [Evidence] 部分")
            lines = sections["evidence"].split("\n")
            mid = max(1, len(lines) // 2)
            sections["evidence"] = "\n".join(lines[:mid]) + "\n...（更多证据已压缩）..."
            rebuilt = self._rebuild_sections(sections, user_query)

        # ── 压缩策略 3：最后兜底 —— 直接截断 ───────────────────────
        if self._count_tokens(rebuilt) > self.config.max_tokens:
            self._logger.warning("Compress: 执行最终截断")
            max_chars = self.config.max_tokens * 4  # 4 字符/token 换算
            rebuilt = rebuilt[:max_chars] + "\n\n[上下文已截断至预算上限]"

        return rebuilt

    def _rebuild_sections(self, sections: Dict[str, str], user_query: str) -> str:
        """从各节内容重建结构化模板。

        Args:
            sections:   各节内容字典（role / task / evidence / context / output）
            user_query: 用户查询（用于填充 [Task] 部分）

        Returns:
            完整的结构化模板字符串
        """
        parts: List[str] = []

        # [Role & Policies]
        if sections["role"]:
            parts.append("[Role & Policies]\n" + sections["role"])

        # [Task]
        parts.append(f"[Task]\n{user_query}")

        # [Evidence]
        if sections["evidence"]:
            parts.append("[Evidence]\n" + sections["evidence"])

        # [Context]
        if sections["context"]:
            parts.append("[Context]\n" + sections["context"])

        # [Output]
        parts.append("[Output]\n请基于以上信息，提供准确、有据的回答。")

        return "\n\n".join(parts)

    # ═══════════════════════════════════════════════════════════════════════════
    # 便捷方法：完整流水线
    # ═══════════════════════════════════════════════════════════════════════════

    def build(
        self,
        user_query: str,
        conversation_history: Optional[List["Message"]] = None,
        system_instructions: Optional[str] = None,
        custom_packets: Optional[List["ContextPacket"]] = None,
    ) -> str:
        """完整 GSSC 流水线：Gather → Select → Structure → Compress → str。

        这是 GSSC 的标准入口，返回结构化模板字符串。
        调用方可将返回值放入 system message 作为 LLM 的上下文。

        Args:
            user_query:          用户当前问题
            conversation_history:对话历史 Message 列表
            system_instructions: 系统指令
            custom_packets:      自定义信息包

        Returns:
            结构化上下文字符串（可直接放入 system prompt）
        """
        packets = self.gather(
            user_query=user_query,
            conversation_history=conversation_history,
            system_instructions=system_instructions,
            custom_packets=custom_packets,
        )
        selected = self.select(packets, user_query=user_query)
        structured = self.structure(selected, user_query)
        return self.compress(structured, selected, user_query)

    # ── 兼容输出格式 ───────────────────────────────────────────────
    # 以下方法为 Agent 集成提供 OpenAI 兼容的消息列表输出。
    # 它们遵循 GSSC 同样的 Gather → Select 逻辑，但 Compose 阶段
    # 输出的是消息列表而非模板字符串。

    def build_to_dicts(
        self,
        user_query: str,
        conversation_history: Optional[List["Message"]] = None,
        system_instructions: Optional[str] = None,
        custom_packets: Optional[List["ContextPacket"]] = None,
    ) -> List[Dict[str, str]]:
        """Gather → Select → Compose（消息列表格式）。

        GSSC 的变体输出：将结构化的上下文转为 OpenAI 兼容的消息字典列表，
        每条消息带有 role（system / user / assistant）和 content。

        与标准 GSSC 的差异：
          - 跳过 Structure（因为消息列表不需要模板分区）
          - 跳过 Compress（因为消息列表可自然分段）

        Args:
            user_query:          用户当前问题
            conversation_history:对话历史 Message 列表
            system_instructions: 系统指令
            custom_packets:      自定义信息包

        Returns:
            [{"role": "system", "content": "..."}, {"role": "user", "content": "..."}]
        """
        packets = self.gather(
            user_query=user_query,
            conversation_history=conversation_history,
            system_instructions=system_instructions,
            custom_packets=custom_packets,
        )
        selected = self.select(packets, user_query=user_query)
        return self._compose_to_dicts(selected, user_query)

    def _compose_to_dicts(
        self,
        packets: List["ContextPacket"],
        user_query: str,
    ) -> List[Dict[str, str]]:
        """将选中的 ContextPacket 组装为 OpenAI 兼容消息字典列表。

        消息顺序：
          1. 系统指令 → role="system"
          2. 检索上下文（记忆、RAG）→ role="system"，带 [type] 前缀
          3. 对话历史  → role 取自 metadata.role
          4. 用户查询  → role="user"
        """
        messages: List[Dict[str, str]] = []

        # 1. 系统指令
        for p in packets:
            if p.metadata.get("type") == "system_instruction":
                messages.append({"role": "system", "content": p.content})

        # 2. 检索上下文（记忆、RAG、自定义）
        for p in packets:
            ptype = p.metadata.get("type", "context")
            if ptype not in ("system_instruction", "conversation_history"):
                messages.append({
                    "role": "system",
                    "content": f"[{ptype}]: {p.content}",
                })

        # 3. 对话历史（按时间正序恢复原始顺序）
        history = [p for p in packets if p.metadata.get("type") == "conversation_history"]
        history.sort(key=lambda p: p.timestamp)
        for p in history:
            role = p.metadata.get("role", "user")
            messages.append({"role": role, "content": p.content})

        # 4. 用户查询
        messages.append({"role": "user", "content": user_query})

        return messages

    # ═══════════════════════════════════════════════════════════════════════════
    # 内部辅助
    # ═══════════════════════════════════════════════════════════════════════════

    @staticmethod
    def _parse_chunk_timestamp(chunk: dict) -> datetime:
        """解析 RAG chunk 的时间戳，兼容多种格式。

        Args:
            chunk: RAG 返回的字典，可能包含 "timestamp" 字段

        Returns:
            解析后的 datetime 对象，解析失败时返回当前时间
        """
        ts = chunk.get("timestamp")
        if isinstance(ts, datetime):
            return ts
        if isinstance(ts, str):
            try:
                return datetime.fromisoformat(ts)
            except (ValueError, TypeError):
                pass
        return datetime.now()


# ═══════════════════════════════════════════════════════════════════════════════
# 辅助函数
# ═══════════════════════════════════════════════════════════════════════════════

def _append_msg(
    messages: List["Message"],
    content: str,
    role: str,
    prefix: str = "",
) -> None:
    """向消息列表添加一条消息（支持可选前缀）。

    这是旧版 compose_to_messages 的辅助函数，保留以保持
    向下兼容。新代码应使用 build_to_dicts()。

    Args:
        messages: 消息列表
        content:  消息内容
        role:     角色（system / user / assistant）
        prefix:   可选前缀，如 "[memory]"
    """
    text = f"{prefix}: {content}" if prefix else content
    messages.append(Message(content=text, role=role))
