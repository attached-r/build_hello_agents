"""
PlanAndSolveAgent — 先规划后执行智能体。

基于 Plan-and-Solve 范式:
  1. Planner: 将复杂问题分解为有序的子步骤
  2. Executor: 按计划逐步执行，每一步依赖上一步结果
  3. Summarizer: 汇总各步骤结果，输出最终答案
"""

import ast
import re
from typing import Optional

from ..core.agent import Agent
from ..core.hello_agents import HelloAgentsLLM
from ..core.config import Config
from ..core.message import Message

# ── 提示词模板 ───────────────────────────────────────────────

PLANNER_PROMPT_TEMPLATE = """
你是一个顶级的AI规划专家。你的任务是将用户提出的复杂问题分解成一个由多个简单步骤组成的行动计划。
请确保计划中的每个步骤都是一个独立的、可执行的子任务，并且严格按照逻辑顺序排列。
你的输出必须是一个Python列表，其中每个元素都是一个描述子任务的字符串。

问题: {question}

请严格按照以下格式输出你的计划,```python与```作为前后缀是必要的:
```python
["步骤1", "步骤2", "步骤3", ...]
```
"""

EXECUTOR_PROMPT_TEMPLATE = """
你是一位顶级的AI执行专家。你的任务是严格按照给定的计划，一步步地解决问题。
你将收到原始问题、完整的计划、以及到目前为止已经完成的步骤和结果。
请你专注于解决"当前步骤"，并仅输出该步骤的最终答案，不要输出任何额外的解释或对话。

# 原始问题:
{question}

# 完整计划:
{plan}

# 历史步骤与结果:
{history}

# 当前步骤:
{current_step}

请仅输出针对"当前步骤"的回答:
"""

SUMMARY_PROMPT_TEMPLATE = """
你是一位顶级的AI总结专家。你将收到一个原始问题和分步骤解决的答案，请整合这些信息，输出最终答案。

原始问题:
{question}

分步骤结果:
{history}

请给出最终总结性回答:
"""


class Planner:
    """规划器 —— 将问题分解为步骤清单"""

    def __init__(self, llm: HelloAgentsLLM):
        self.llm = llm

    def plan(self, question: str) -> list[str]:
        """生成行动计划"""
        prompt = PLANNER_PROMPT_TEMPLATE.format(question=question)
        messages = [{"role": "user", "content": prompt}]

        print("📋 正在生成计划...")
        response = self.llm.think(messages, temperature=0) or ""

        print(f"📋 计划原始输出:\n{response}")

        try:
            # 解析 ```python [...] ``` 中的列表
            match = re.search(r"```python\s*(.*?)\s*```", response, re.DOTALL)
            if match:
                plan_str = match.group(1).strip()
            else:
                plan_str = response.strip()
            plan = ast.literal_eval(plan_str)
            return plan if isinstance(plan, list) else []
        except Exception as e:
            print(f"❌ 计划解析失败: {e}")
            return []


class Executor:
    """执行器 —— 按计划逐步执行"""

    def __init__(self, llm: HelloAgentsLLM):
        self.llm = llm

    def execute(self, question: str, plan: list[str]) -> tuple[str, str]:
        """逐步执行计划，返回 (history, last_response)"""
        history = ""
        last_response = ""

        print(f"🚀 正在执行计划（共 {len(plan)} 步）...\n")

        for i, step in enumerate(plan, 1):
            print(f"  🔹 步骤 {i}/{len(plan)}: {step}")
            prompt = EXECUTOR_PROMPT_TEMPLATE.format(
                question=question,
                plan=plan,
                history=history if history else "无",
                current_step=step,
            )
            messages = [{"role": "user", "content": prompt}]
            response = self.llm.think(messages, temperature=0) or ""
            history += f"步骤 {i}: {step}\n结果: {response}\n\n"
            last_response = response
            print(f"  ✅ 步骤 {i} 完成")

        return history, last_response


class PlanAndSolveAgent(Agent):
    """规划-执行智能体 —— 先分解问题，再逐步解决"""

    def __init__(
        self,
        name: str,
        llm: HelloAgentsLLM,
        system_prompt: Optional[str] = None,
        config: Optional[Config] = None,
    ):
        super().__init__(name, llm, system_prompt, config)
        self.planner = Planner(llm)
        self.executor = Executor(llm)

    def run(self, input_text: str, **kwargs) -> str:
        print(f"\n🧠 {self.name} 启动 Plan-and-Solve 推理: {input_text}")

        # 1. 规划
        plan = self.planner.plan(input_text)
        if not plan:
            msg = "无法生成有效的行动计划"
            print(f"❌ {msg}")
            return msg

        print(f"\n📋 已生成计划: {plan}")

        # 2. 执行
        history, last_response = self.executor.execute(input_text, plan)

        # 3. 汇总
        print(f"\n  🔹 汇总步骤结果...")
        final_prompt = SUMMARY_PROMPT_TEMPLATE.format(
            question=input_text,
            history=history,
        )
        messages = [{"role": "user", "content": final_prompt}]
        final_answer = self.llm.think(messages, temperature=0) or last_response

        print(f"\n✅ {self.name} Plan-and-Solve 推理完成")
        print(f"\n最终答案:\n{final_answer}")

        self.add_message(Message(input_text, "user"))
        self.add_message(Message(final_answer, "assistant"))
        return final_answer
