"""
MyFunctionAgent — 函数调用智能体。

基于 Function Calling 范式:
  - 将工具注册为函数 schema
  - 检测 LLM 文本输出中的函数调用模式 tool_name({'param': 'value'})
  - 执行工具并将结果回注到对话中
  - 多轮迭代直到 LLM 输出纯文本回复
"""

import json
import re
from typing import Any, Optional

from ..core.agent import Agent
from ..core.hello_agents import HelloAgentsLLM
from ..core.config import Config
from ..core.message import Message
from ..tools.registry import ToolRegistry

# ── 函数调用提示词模板 ─────────────────────────────────────

FUNCTION_CALLING_PROMPT_TEMPLATE = """
你是一个智能助手，可以使用外部工具函数来帮助回答问题。

可用函数:
{functions_desc}

当需要使用函数时，请严格按照以下格式输出:
函数名({{"参数名": "参数值"}})

例如:
calculator({{"expression": "1+2*3"}})

然后系统会执行函数并将结果返回给你，你需要基于结果继续回答。
如果你不需要调用函数，直接输出回答即可。

现在，请处理以下请求:
用户: {question}
"""


# ── 函数调用模式检测 ────────────────────────────────────────
# 匹配: tool_name({"key": "value", ...}) 或 tool_name({"key": "value"})
FUNCTION_CALL_PATTERN = re.compile(
    r"(\w+)\s*\(\s*(\{.*?\})\s*\)\s*",
    re.DOTALL,
)


def _parse_function_call(text: str) -> Optional[tuple[str, dict[str, Any]]]:
    """从文本中检测函数调用，返回 (函数名, 参数字典) 或 None"""
    for match in FUNCTION_CALL_PATTERN.finditer(text):
        name = match.group(1)
        try:
            params = json.loads(match.group(2))
            return name, params
        except (json.JSONDecodeError, ValueError):
            continue
    return None


class MyFunctionAgent(Agent):
    """函数调用智能体 —— 通过文本函数调用模式使用工具"""

    def __init__(
        self,
        name: str,
        llm: HelloAgentsLLM,
        system_prompt: Optional[str] = None,
        config: Optional[Config] = None,
        tool_registry: Optional[ToolRegistry] = None,
        max_iterations: int = 5,
    ):
        super().__init__(name, llm, system_prompt, config)
        self.tool_registry = tool_registry or ToolRegistry()
        self.max_iterations = max_iterations

    def run(self, input_text: str, **kwargs) -> str:
        print(f"⚡ {self.name} 启动 Function Calling 推理: {input_text}")

        # 构建函数描述
        functions_desc = self._build_functions_desc()

        # 构建消息
        messages = []
        if self.system_prompt:
            messages.append({"role": "system", "content": self.system_prompt})
        for msg in self._history:
            messages.append({"role": msg.role, "content": msg.content})

        prompt = FUNCTION_CALLING_PROMPT_TEMPLATE.format(
            functions_desc=functions_desc,
            question=input_text,
        )
        messages.append({"role": "user", "content": prompt})

        # 多轮函数调用
        for i in range(self.max_iterations):
            print(f"\n{'='*40}")
            print(f"🔄 Function Call 第 {i+1}/{self.max_iterations} 轮")

            response = self.llm.think(messages, temperature=kwargs.get("temperature", 0))
            if not response:
                print("❌ LLM 未能返回有效响应")
                break

            # 检测函数调用
            call = _parse_function_call(response)

            if not call:
                # 纯文本回复 —— 函数调用结束
                print(f"💬 最终回复: {response}")
                self.add_message(Message(input_text, "user"))
                self.add_message(Message(response, "assistant"))
                print(f"✅ {self.name} Function Calling 推理完成")
                return response

            name, params = call
            print(f"🔧 (文本回退) 检测到函数调用: {name}({params})")

            # 执行函数
            try:
                result = self.tool_registry.execute_tool(name, params)
            except Exception as e:
                result = f"函数调用失败: {e}"

            print(f"  <- 结果: {result}")

            # 将函数调用和结果注入消息历史
            messages.append({"role": "assistant", "content": response})
            messages.append({"role": "user", "content": f"函数 {name} 返回结果: {result}"})

        # 达到最大迭代次数
        print(f"⚠️  已达到最大迭代次数 ({self.max_iterations})")
        result_text = "无法在限定步数内完成函数调用"
        self.add_message(Message(input_text, "user"))
        self.add_message(Message(result_text, "assistant"))
        return result_text

    def _build_functions_desc(self) -> str:
        """构建函数描述文本"""
        descriptions = []
        for tool in self.tool_registry.list_tools():
            params_desc = []
            for p in tool.get_parameters():
                params_desc.append(f"    - {p.name} ({p.type}): {p.description}")
            param_str = "\n".join(params_desc) if params_desc else "    无参数"
            descriptions.append(f"- {tool.name}: {tool.description}\n{param_str}")

        for name, info in self.tool_registry._functions.items():
            descriptions.append(f"- {name}: {info['description']}\n    参数: 可变参数")

        return "\n\n".join(descriptions) if descriptions else "暂无可用函数"

    def add_tool(self, tool) -> None:
        """添加工具"""
        self.tool_registry.register_tool(tool)
        print(f"🔧 工具 '{tool.name}' 已添加")

    def has_tools(self) -> bool:
        """检查是否有可用工具"""
        return (
            len(self.tool_registry._tools) > 0
            or len(self.tool_registry._functions) > 0
        )

    def list_tools(self) -> list:
        """列出所有已注册工具"""
        return self.tool_registry.list_tools()
