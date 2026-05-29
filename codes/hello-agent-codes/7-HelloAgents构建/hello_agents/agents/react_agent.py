"""
ReActAgent — 推理+行动循环智能体。

基于 ReAct（Reasoning + Acting）范式:
  Thought → Action → Observation → Thought → ... → Finish

与 ToolRegistry 深度集成，支持多轮推理与工具调用。
"""

import re
from typing import Optional

from ..core.agent import Agent
from ..core.hello_agents import HelloAgentsLLM
from ..core.config import Config
from ..tools.registry import ToolRegistry

# ── 提示词模板 ─────────────────────────────────────────────

REACT_PROMPT_TEMPLATE = """
你是一个有能力调用外部工具的智能助手。

可用工具如下:
{tools}

请严格按照以下格式进行回应:

Thought: 你的思考过程，用于分析问题、拆解任务和规划下一步行动。
Action: 你决定采取的行动，必须是以下格式之一:
- `{{tool_name}}[{{tool_input}}]`: 调用一个可用工具。
- `Finish[最终答案]`: 当你认为已经获得最终答案时。

当你收集到足够的信息，能够回答用户的最终问题时，
你必须在 Action: 字段后使用 Finish[最终答案] 来输出最终答案。

现在，请开始解决以下问题:
Question: {question}
History: {history}
"""

REENGAGE_PROMPT_TEMPLATE = """
你是一个有能力调用外部工具的智能助手。

可用工具如下:
{tools}

请严格按照以下格式进行回应:

Thought: 你的思考过程
Action: 工具名[输入] 或 Finish[答案]

Question: {question}
History: {history}
你之前的回应:
{last_response}

请注意，必须严格按照格式输出 Thought 和 Action。
请重新输出:
"""

FINAL_PROMPT_TEMPLATE = """
你是一个智能助手，已经进行了多轮推理和工具调用，但尚未完成最终回答。

问题: {question}
历史推理过程:
{history}

请基于以上过程给出最终总结性回答。
"""


class ReActAgent(Agent):
    """ReAct 推理-行动循环智能体"""

    def __init__(
        self,
        name: str,
        llm: HelloAgentsLLM,
        system_prompt: Optional[str] = None,
        config: Optional[Config] = None,
        tool_registry: Optional[ToolRegistry] = None,
        max_steps: int = 5,
    ):
        super().__init__(name, llm, system_prompt, config)
        self.tool_registry = tool_registry or ToolRegistry()
        self.max_steps = max_steps

    def run(self, input_text: str, **kwargs) -> str:
        """运行 ReAct 循环"""
        print(f"🤖 {self.name} 启动 ReAct 推理: {input_text}")

        self._history: list[str] = []
        current_step = 0

        while current_step < self.max_steps:
            current_step += 1
            print(f"\n{'='*40}")
            print(f"🔄 ReAct 第 {current_step}/{self.max_steps} 步")

            # 1. 构建提示词
            tools_desc = self.tool_registry.get_tools_description() or "暂无可用工具"
            history_str = "\n".join(self._history)
            prompt = REACT_PROMPT_TEMPLATE.format(
                tools=tools_desc,
                question=input_text,
                history=history_str,
            )

            # 2. 调用 LLM
            messages = [{"role": "user", "content": prompt}]
            response = self.llm.think(messages, temperature=kwargs.get("temperature", 0))
            if not response:
                print("❌ LLM 未能返回有效响应")
                break

            # 3. 解析输出
            thought, action = self._parse_output(response)
            if not action:
                # 重试引导
                print("⚠️  输出格式无法解析，重新引导...")
                re_prompt = REENGAGE_PROMPT_TEMPLATE.format(
                    tools=tools_desc,
                    question=input_text,
                    history=history_str,
                    last_response=response,
                )
                messages = [{"role": "user", "content": re_prompt}]
                response = self.llm.think(messages, temperature=kwargs.get("temperature", 0))
                if not response:
                    break
                thought, action = self._parse_output(response)
                if not action:
                    print("⚠️  重试后仍无法解析，跳过此步")
                    continue

            if thought:
                print(f"💭 Thought: {thought}")

            # 4. 执行 Action
            if action.startswith("Finish"):
                match = re.match(r"Finish\[(.*)\]", action, re.DOTALL)
                final_answer = match.group(1).strip() if match else action
                print(f"🏁 Finish: {final_answer}")
                return final_answer

            print(f"🔧 Action: {action}")

            tool_name, tool_input = self._parse_action(action)
            if not tool_name or tool_input is None:
                print("⚠️  Action 格式无效，跳过")
                continue

            # 执行工具
            try:
                param_dict = (
                    {"input": tool_input}
                    if "=" not in tool_input
                    else {
                        k.strip(): v.strip()
                        for pair in tool_input.split(",")
                        if "=" in pair
                        for k, v in (pair.split("=", 1),)
                    }
                )
                observation = self.tool_registry.execute_tool(tool_name, param_dict)
            except (ValueError, KeyError) as e:
                observation = f"错误: {e}"
            except Exception as e:
                observation = f"工具执行异常: {e}"

            print(f"📊 Observation: {observation[:200]}")

            # 5. 记录历史
            self._history.append(f"Action: {action}")
            self._history.append(f"Observation: {observation}")

        # 达到最大步数
        print(f"\n⚠️  已达到最大步数 ({self.max_steps})，强制结束")
        final_prompt = FINAL_PROMPT_TEMPLATE.format(
            question=input_text,
            history="\n".join(self._history),
        )
        messages = [{"role": "user", "content": final_prompt}]
        final_summary = self.llm.think(messages, temperature=kwargs.get("temperature", 0)) or ""
        print(f"最终总结性回答：{final_summary}")
        return f"最终总结性回答：{final_summary}"

    # ── 解析方法 ──────────────────────────────────────────────

    @staticmethod
    def _parse_output(text: str) -> tuple[Optional[str], Optional[str]]:
        """解析 LLM 输出，提取 Thought 和 Action"""
        thought_match = re.search(
            r"Thought:\s*(.*?)(?=\nAction:|$)", text, re.DOTALL
        )
        action_match = re.search(r"Action:\s*(.*?)$", text, re.DOTALL)
        thought = thought_match.group(1).strip() if thought_match else None
        action = action_match.group(1).strip() if action_match else None
        return thought, action

    @staticmethod
    def _parse_action(action_text: str) -> tuple[Optional[str], Optional[str]]:
        """解析 Action 字符串，提取工具名称和输入"""
        match = re.match(r"(\w+)\[(.*)\]", action_text, re.DOTALL)
        if match:
            return match.group(1), match.group(2)
        return None, None
