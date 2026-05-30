"""
简易测试：验证 ContextBuilder GSSC 流水线的基础功能

只测试核心上下文构建（不用 memory / RAG），验证：
  1. gather 能汇集系统指令 + 对话历史
  2. select 能正确评分和过滤
  3. structure 能输出格式化的模板
  4. build() 一次调用跑完整个流水线
"""

import os
import sys
from datetime import datetime

# ── 路径引导：自动向上搜索 hello_agents 包 ────────────
_BASE = os.path.abspath(__file__)
while not os.path.isdir(os.path.join(os.path.dirname(_BASE), 'hello_agents')):
    _BASE = os.path.dirname(_BASE)
    if os.path.dirname(_BASE) == _BASE:
        break
_PROJECT_ROOT = os.path.dirname(_BASE)
if _PROJECT_ROOT not in sys.path:
    sys.path.insert(0, _PROJECT_ROOT)

from hello_agents.context import ContextBuilder, ContextConfig
from hello_agents.core.message import Message



# ── 1. 配置 ──────────────────────────────────────────────────────────────
config = ContextConfig(
    max_tokens=3000,
    reserve_ratio=0.2,
    min_relevance=0.1,
    enable_compression=True,
    recency_weight=0.3,
    relevance_weight=0.7,
)

builder = ContextBuilder(config=config)  # 不传 memory/rag，只测核心流水线

# ── 2. 对话历史 ─────────────────────────────────────────────────────────
now = datetime.now()
conversation_history = [
    Message(
        content="我正在开发一个数据分析工具",
        role="user",
        timestamp=now,
    ),
    Message(
        content="很好！您计划使用什么技术栈？",
        role="assistant",
        timestamp=now,
    ),
    Message(
        content="我打算使用 Python 和 Pandas，已经完成了 CSV 读取模块",
        role="user",
        timestamp=now,
    ),
]

# ── 3. 构建上下文 ───────────────────────────────────────────────────────
context = builder.build(
    user_query="如何优化 Pandas 的内存占用？",
    conversation_history=conversation_history,
    system_instructions="你是一位资深的 Python 数据工程顾问。回答需要："
                        "1) 提供具体可行的建议 "
                        "2) 解释技术原理 "
                        "3) 给出代码示例",
)

# ── 4. 输出结果 ─────────────────────────────────────────────────────────
print("=" * 80)
print("构建的上下文（GSSC 结构化模板）")
print("=" * 80)
print(context)
print("=" * 80)

# ── 5. 快速验证 ─────────────────────────────────────────────────────────
assert "[Role & Policies]" in context, "缺少 [Role & Policies] 分区"
assert "[Task]" in context, "缺少 [Task] 分区"
assert "如何优化" in context, "缺少用户查询"
assert "[Context]" in context, "缺少 [Context] 分区"
assert "[Output]" in context, "缺少 [Output] 分区"
assert "数据分析" in context, "缺少对话历史内容"
print("✅ 所有基础断言通过")

# ── 6. 额外：build_to_dicts 格式 ───────────────────────────────────────
dicts = builder.build_to_dicts(
    user_query="如何优化 Pandas 的内存占用？",
    conversation_history=conversation_history,
    system_instructions="你是一位资深 Python 数据工程顾问。",
)
print(f"\nbuild_to_dicts 输出：{len(dicts)} 条消息")
for msg in dicts:
    print(f"  [{msg['role']}] {msg['content'][:60]}...")
print("✅ build_to_dicts 输出正常")
