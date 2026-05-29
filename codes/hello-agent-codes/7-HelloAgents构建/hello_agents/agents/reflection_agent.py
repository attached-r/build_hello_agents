"""
ReflectionAgent — 反思型智能体。

基于 Reflection 范式:
  初始执行 → 反思（评审代码）→ 优化（根据反馈改进）→ 再反思 → ...

通过迭代的"生成-评审-优化"循环，逐步提升输出质量。
"""

from typing import Optional

from ..core.agent import Agent
from ..core.hello_agents import HelloAgentsLLM
from ..core.config import Config
from ..core.message import Message

# ── 提示词模板 ───────────────────────────────────────────────

INITIAL_PROMPT_TEMPLATE = """
你是一位资深的Python程序员。请根据以下要求，编写一个Python函数。
你的代码必须包含完整的函数签名、文档字符串，并遵循PEP 8编码规范。

要求: {task}

请直接输出代码，不要包含任何额外的解释。
"""

REFLECT_PROMPT_TEMPLATE = """
你是一位极其严格的代码评审专家和资深算法工程师，对代码的性能有极致的要求。
你的任务是审查以下Python代码，并专注于找出其在算法效率上的主要瓶颈。

# 原始任务:
{task}

# 待审查的代码:
```python
{code}
```

请分析该代码的时间复杂度，并思考是否存在一种算法上更优的解决方案来显著提升性能。
如果存在，请清晰地指出当前算法的不足，并提出具体的、可行的改进算法建议。
如果代码在算法层面已经达到最优，才能回答"无需改进"。

请直接输出你的反馈，不要包含任何额外的解释。
"""

REFINE_PROMPT_TEMPLATE = """
你是一位资深的Python程序员。你正在根据一位代码评审专家的反馈来优化你的代码。

# 原始任务:
{task}

# 你上一轮尝试的代码:
{last_code}
评审员的反馈：
{feedback}

请根据评审员的反馈，生成一个优化后的新版本代码。
你的代码必须包含完整的函数签名、文档字符串，并遵循PEP 8编码规范。
请直接输出优化后的代码，不要包含任何额外的解释。
"""


class ReflectionMemory:
    """简单的反思记忆模块"""

    def __init__(self):
        self.records: list[dict] = []

    def add_record(self, record_type: str, content: str):
        self.records.append({"type": record_type, "content": content})
        print(f"📝 记忆已更新，新增一条 '{record_type}' 记录。")

    def get_trajectory(self) -> str:
        """将所有记忆记录格式化为字符串"""
        parts = []
        for r in self.records:
            if r["type"] == "execution":
                parts.append(f"--- 上一轮尝试 (代码) ---\n{r['content']}")
            elif r["type"] == "reflection":
                parts.append(f"--- 评审员反馈 ---\n{r['content']}")
        return "\n\n".join(parts)

    def get_last_execution(self) -> Optional[str]:
        """获取最近一次的执行结果"""
        for r in reversed(self.records):
            if r["type"] == "execution":
                return r["content"]
        return None


class ReflectionAgent(Agent):
    """反思型智能体 —— 迭代生成-评审-优化"""

    def __init__(
        self,
        name: str,
        llm: HelloAgentsLLM,
        system_prompt: Optional[str] = None,
        config: Optional[Config] = None,
        max_iterations: int = 3,
    ):
        super().__init__(name, llm, system_prompt, config)
        self.max_iterations = max_iterations
        self.memory = ReflectionMemory()

    def run(self, input_text: str, **kwargs) -> str:
        print(f"\n🤔 {self.name} 启动 Reflection 推理: {input_text}")

        # 1. 初始执行
        print("\n📝 正在进行初始尝试...")
        initial_code = self._call_llm(
            INITIAL_PROMPT_TEMPLATE.format(task=input_text)
        )
        self.memory.add_record("execution", initial_code)
        print(f"✅ 初始回答已生成 ({len(initial_code)} 字符)")

        # 2. 迭代反思与优化
        for i in range(self.max_iterations):
            print(f"\n🔄 反思迭代 {i+1}/{self.max_iterations}")

            # a. 反思
            print("-> 正在进行反思评审...")
            last_code = self.memory.get_last_execution()
            feedback = self._call_llm(
                REFLECT_PROMPT_TEMPLATE.format(task=input_text, code=last_code)
            )
            self.memory.add_record("reflection", feedback)
            print(f"📋 评审意见已生成 ({len(feedback)} 字符)")

            if "无需改进" in feedback:
                print("✅ 反思认为回答已无需改进，任务完成。")
                break

            # b. 优化
            print("-> 正在进行优化...")
            refined = self._call_llm(
                REFINE_PROMPT_TEMPLATE.format(
                    task=input_text,
                    last_code=last_code,
                    feedback=feedback,
                )
            )
            self.memory.add_record("execution", refined)
            print("✅ 优化完成")

        final_code = self.memory.get_last_execution()
        print(f"\n✅ {self.name} Reflection 推理完成")
        print(f"\n最终回答:\n{final_code}")

        self.add_message(Message(input_text, "user"))
        self.add_message(Message(final_code, "assistant"))
        return final_code

    def _call_llm(self, prompt: str) -> str:
        """辅助方法：调用 LLM 返回完整响应"""
        messages = [{"role": "user", "content": prompt}]
        return self.llm.think(messages, temperature=0) or ""
