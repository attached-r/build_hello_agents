"""
MySimpleAgent — 基于 HelloAgents 框架的自定义 Agent

支持三种运行模式:
  - 基础对话: 直接调用 LLM，无工具
  - 流式响应: 逐 token 输出
  - 工具增强: 自动解析并执行 LLM 输出的工具调用标记
"""

import os
import re
import sys
from typing import Iterator, Optional

# ── 路径引导: 自动向上搜索项目根目录 ────────────
_BASE = os.path.abspath(__file__)
while not os.path.isdir(os.path.join(os.path.dirname(_BASE), 'hello_agents')):
    _BASE = os.path.dirname(_BASE)
    if os.path.dirname(_BASE) == _BASE:
        break
_PROJECT_ROOT = os.path.dirname(_BASE)
if _PROJECT_ROOT not in sys.path:
    sys.path.insert(0, _PROJECT_ROOT)

from hello_agents.core.agent import Agent
from hello_agents.core.hello_agents import HelloAgentsLLM
from hello_agents.core.config import Config
from hello_agents.core.message import Message
from hello_agents.tools.registry import ToolRegistry


# ======================================================================
# MySimpleAgent
# ======================================================================

class MySimpleAgent(Agent):
    """可定制的对话 Agent。"""

    def __init__(
        self,
        name: str,
        llm: HelloAgentsLLM,
        system_prompt: Optional[str] = None,
        config: Optional[Config] = None,
        tool_registry: Optional[ToolRegistry] = None,
        enable_tool_calling: bool = True,
    ):
        super().__init__(name, llm, system_prompt, config)
        self.tool_registry = tool_registry
        self.enable_tool_calling = enable_tool_calling and tool_registry is not None
        status = "启用" if self.enable_tool_calling else "禁用"
        print(f"✅ {name} 初始化完成，工具调用: {status}")

    # ════════════════════════════════════════════════════════════════
    # 公共运行接口
    # ════════════════════════════════════════════════════════════════

    def run(self, input_text: str, max_tool_iterations: int = 3, **kwargs) -> str:
        """处理用户输入，返回最终回复。"""
        print(f"🤖 {self.name} 正在处理: {input_text}")

        messages = self._build_initial_messages(input_text)

        if not self.enable_tool_calling:
            return self._simple_run(messages, input_text, **kwargs)

        return self._run_with_tools(messages, input_text, max_tool_iterations, **kwargs)

    def stream_run(self, input_text: str, **kwargs) -> Iterator[str]:
        """流式处理用户输入。"""
        print(f"🌊 {self.name} 开始流式处理: {input_text}")

        messages = []
        if self.system_prompt:
            messages.append({"role": "system", "content": self.system_prompt})
        for msg in self._history:
            messages.append({"role": msg.role, "content": msg.content})
        messages.append({"role": "user", "content": input_text})

        print("📝 实时响应: ", end="")
        full_response = self.llm.think(messages, stream=True, **kwargs)
        print()

        self.add_message(Message(input_text, "user"))
        self.add_message(Message(full_response, "assistant"))
        print(f"✅ {self.name} 流式响应完成")

        yield full_response

    # ════════════════════════════════════════════════════════════════
    # 内部运行逻辑
    # ════════════════════════════════════════════════════════════════

    def _build_initial_messages(self, input_text: str) -> list:
        """构建初始消息列表（增强系统提示词 + 历史 + 当前输入）。"""
        messages = [
            {"role": "system", "content": self._get_enhanced_system_prompt()}
        ]
        for msg in self._history:
            messages.append({"role": msg.role, "content": msg.content})
        messages.append({"role": "user", "content": input_text})
        return messages

    def _simple_run(self, messages: list, input_text: str, **kwargs) -> str:
        """无工具的直接对话。"""
        response = self.llm.think(messages, **kwargs)
        self.add_message(Message(input_text, "user"))
        self.add_message(Message(response, "assistant"))
        print(f"✅ {self.name} 响应完成")
        return response

    def _run_with_tools(
        self, messages: list, input_text: str, max_iterations: int, **kwargs
    ) -> str:
        """多轮工具调用循环。

        每一轮: LLM 回复 → 检测工具调用标记 → 执行工具 → 回注结果 → 下一轮
        直到 LLM 输出纯文本回复或达到最大迭代次数。
        """
        final_response = ""

        for _ in range(max_iterations):
            response = self.llm.think(messages, **kwargs)
            tool_calls = self._parse_tool_calls(response)

            if not tool_calls:
                final_response = response
                break

            print(f"🔧 检测到 {len(tool_calls)} 个工具调用")

            clean_response = response
            results = []
            for call in tool_calls:
                result = self._execute_tool_call(call["tool_name"], call["parameters"])
                results.append(result)
                clean_response = clean_response.replace(call["original"], "")

            messages.append({"role": "assistant", "content": clean_response.strip()})
            messages.append(
                {
                    "role": "user",
                    "content": (
                        "工具执行结果:\n"
                        + "\n\n".join(results)
                        + "\n\n请基于这些结果给出完整回答。"
                    ),
                }
            )
        else:
            # 所有迭代均未得到纯文本回复，再调一次 LLM
            final_response = self.llm.think(messages, **kwargs)

        self.add_message(Message(input_text, "user"))
        self.add_message(Message(final_response, "assistant"))
        print(f"✅ {self.name} 响应完成")
        return final_response

    # ════════════════════════════════════════════════════════════════
    # 系统提示词
    # ════════════════════════════════════════════════════════════════

    def _get_enhanced_system_prompt(self) -> str:
        """构建系统提示词，启用工具时附加工具说明与调用格式。"""
        base = self.system_prompt or "你是一个有用的AI助手。"

        if not self.enable_tool_calling or not self.tool_registry:
            return base

        desc = self.tool_registry.get_tools_description()
        if not desc or desc == "暂无可用工具":
            return base

        return (
            base
            + "\n\n## 可用工具\n"
            + "你可以使用以下工具来帮助回答问题:\n"
            + desc
            + "\n\n## 工具调用格式\n"
            + "当需要使用工具时，请使用以下格式:\n"
            + "`[TOOL_CALL:工具名:参数]`\n"
            + "例如: `[TOOL_CALL:calculator:1+2*3]`\n\n"
            + "工具调用结果会自动插入到对话中，然后你可以基于结果继续回答。"
        )

    # ════════════════════════════════════════════════════════════════
    # 工具解析与执行
    # ════════════════════════════════════════════════════════════════

    TOOL_CALL_PATTERN = re.compile(r"\[TOOL_CALL:([^:]+):([^\]]+)\]")  #? 工具调用标记模式

    def _parse_tool_calls(self, text: str) -> list:
        """从 LLM 输出中解析 `[TOOL_CALL:工具名:参数]` 标记。"""
        return [
            {
                "tool_name": name.strip(),
                "parameters": params.strip(),
                "original": f"[TOOL_CALL:{name}:{params}]",
            }
            for name, params in self.TOOL_CALL_PATTERN.findall(text)
        ]

    def _execute_tool_call(self, tool_name: str, parameters: str) -> str:
        """执行单个工具调用。"""
        if not self.tool_registry:
            return "错误:未配置工具注册表"

        try:
            param_dict = self._parse_tool_parameters(parameters)
            result = self.tool_registry.execute_tool(tool_name, param_dict)
            return f"🔧 工具 {tool_name} 执行结果:\n{result}"
        except Exception as e:
            return f"工具调用失败: {e}"

    def _parse_tool_parameters(self, parameters: str) -> dict:
        """智能解析工具参数字符串为字典。"""
        if "=" not in parameters:
            # 纯字符串参数 → 使用通用 input key
            return {"input": parameters}

        if "," in parameters and "=" in parameters:
            # key=value 对，逗号分隔
            return {
                k.strip(): v.strip()
                for pair in parameters.split(",")
                if "=" in pair
                for k, v in (pair.split("=", 1),)
            }

        # 单个 key=value
        k, v = parameters.split("=", 1)
        return {k.strip(): v.strip()}

    # ════════════════════════════════════════════════════════════════
    # 工具管理便利接口
    # ════════════════════════════════════════════════════════════════

    def add_tool(self, tool) -> None:
        """添加工具到 Agent。首次添加时自动创建 ToolRegistry。"""
        if not self.tool_registry:
            self.tool_registry = ToolRegistry()
            self.enable_tool_calling = True
        self.tool_registry.register_tool(tool)
        print(f"🔧 工具 '{tool.name}' 已添加")

    def remove_tool(self, tool_name: str) -> bool:
        """移除工具。"""
        if self.tool_registry:
            self.tool_registry.unregister(tool_name)
            return True
        return False

    def has_tools(self) -> bool:
        """检查是否有可用工具。"""
        return self.enable_tool_calling and self.tool_registry is not None

    def list_tools(self) -> list:
        """列出所有已注册工具。"""
        return self.tool_registry.list_tools() if self.tool_registry else []


# ======================================================================
# 测试
# ======================================================================

if __name__ == "__main__":
    from dotenv import load_dotenv

    load_dotenv()

    llm = HelloAgentsLLM()

    # ── 测试 1: 基础对话 ──────────────────────────────────────────
    print("=== 测试 1: 基础对话 ===")
    basic_agent = MySimpleAgent(
        name="基础助手",
        llm=llm,
        system_prompt="你是一个友好的AI助手，请用简洁的方式回答问题。",
    )
    resp = basic_agent.run("你好，请介绍一下自己")
    print(f"\n基础对话响应: {resp}\n")

    # ── 测试 2: 流式响应 ──────────────────────────────────────────
    print("=== 测试 2: 流式响应 ===")
    for _ in basic_agent.stream_run("请用一句话解释什么是人工智能"):
        pass
    print(f"对话历史: {len(basic_agent.get_history())} 条消息\n")

    # ── 测试 3: 工具增强对话 ──────────────────────────────────────
    print("=== 测试 3: 工具增强对话 ===")

    def calculator_fn(expression: str) -> str:
        try:
            return str(eval(expression, {"__builtins__": {}}, {}))
        except Exception as e:
            return f"计算错误: {e}"

    from hello_agents.tools.base import FunctionTool, ToolParameter

    calc_tool = FunctionTool(
        name="calculator",
        description="执行数学计算，传入表达式如 '1+2*3'",
        fn=calculator_fn,
        parameters=[ToolParameter(name="expression", type="string", description="数学表达式")],
    )

    registry = ToolRegistry()
    registry.register_tool(calc_tool)

    tool_agent = MySimpleAgent(
        name="增强助手",
        llm=llm,
        system_prompt="你是一个智能助手，可以使用计算器工具。当需要计算时，使用 [TOOL_CALL:calculator:表达式] 格式。",
        tool_registry=registry,
        enable_tool_calling=True,
    )
    resp = tool_agent.run("请计算 15 * 8 + 32 等于多少？")
    print(f"\n工具增强响应: {resp}\n")

    # ── 测试 4: 动态工具管理 ──────────────────────────────────────
    print("=== 测试 4: 动态工具管理 ===")
    print(f"添加工具前: {basic_agent.has_tools()}")
    basic_agent.add_tool(calc_tool)
    print(f"添加工具后: {basic_agent.has_tools()}")
    print(f"可用工具: {[t.name for t in basic_agent.list_tools()]}")
