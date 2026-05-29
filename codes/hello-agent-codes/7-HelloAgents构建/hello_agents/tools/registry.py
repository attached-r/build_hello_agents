import os
import sys
from typing import Callable, Any, Dict, List, Optional

# ── 路径引导: 自动向上搜索项目根目录 ────────────
_BASE = os.path.abspath(__file__)
while not os.path.isdir(os.path.join(os.path.dirname(_BASE), 'hello_agents')):
    _BASE = os.path.dirname(_BASE)
    if os.path.dirname(_BASE) == _BASE:
        break
_PROJECT_ROOT = os.path.dirname(_BASE)
if _PROJECT_ROOT not in sys.path:
    sys.path.insert(0, _PROJECT_ROOT)

from hello_agents.tools.base import Tool


def _is_dict_like(value: Any) -> bool:
    """检查值是否为 dict 类型（不含 str，避免 str 被序列索引误判）"""
    return isinstance(value, dict)


class ToolRegistry:
    """HelloAgents工具注册表"""

    def __init__(self):
        self._tools: dict[str, Tool] = {}
        self._functions: dict[str, dict[str, Any]] = {}

    #? 注册Tool对象
    def register_tool(self, tool: Tool):
        """注册Tool对象"""
        if tool.name in self._tools:
            print(f"⚠️ 警告:工具 '{tool.name}' 已存在，将被覆盖。")
        self._tools[tool.name] = tool
        print(f"✅ 工具 '{tool.name}' 已注册。")

    #? 直接注册函数作为工具（简便方式）
    def register_function(self, name: str, description: str, func: Callable[..., str]):
        """
        直接注册函数作为工具（简便方式）

        Args:
            name: 工具名称
            description: 工具描述
            func: 工具函数，接受关键字参数，返回字符串结果
        """
        if name in self._functions:
            print(f"⚠️ 警告:工具 '{name}' 已存在，将被覆盖。")

        self._functions[name] = {
            "description": description,
            "func": func,
        }
        print(f"✅ 工具 '{name}' 已注册。")

    def execute_tool(self, name: str, parameters: Any) -> str:
        """
        执行指定名称的工具

        Args:
            name: 工具名称
            parameters: 工具参数字典（Tool 对象）或字符串（注册函数兼容）

        Returns:
            工具执行结果字符串
        """
        # 首先尝试执行 Tool 对象
        if name in self._tools:
            tool = self._tools[name]
            if not _is_dict_like(parameters):
                return tool.run({"input": str(parameters)})
            return tool.run(parameters)

        # 然后尝试执行注册的函数
        elif name in self._functions:
            func = self._functions[name]['func']
            if _is_dict_like(parameters):
                return func(**parameters)
            return func(parameters)

        else:
            raise ValueError(f"工具 '{name}' 不存在")

    def get_tools_description(self) -> str:
        """
        获取所有可用工具的格式化描述字符串
        """
        descriptions = []

        # Tool对象描述
        for tool in self._tools.values():
            descriptions.append(f"- {tool.name}: {tool.description}")

        # 函数工具描述
        for name, info in self._functions.items():
            descriptions.append(f"- {name}: {info['description']}")

        return "\n".join(descriptions) if descriptions else "暂无可用工具"

    def get_tool(self, name: str) -> Optional[Tool]:
        """根据名称获取 Tool 对象"""
        return self._tools.get(name)

    def list_tools(self) -> List[Tool]:
        """列出所有已注册的 Tool 对象"""
        return list(self._tools.values())

    def unregister(self, name: str) -> None:
        """注销指定名称的工具（同时检查 Tool 和 Function）"""
        removed = False
        if name in self._tools:
            del self._tools[name]
            removed = True
        if name in self._functions:
            del self._functions[name]
            removed = True
        if removed:
            print(f"🔧 工具 '{name}' 已注销。")

    def to_openai_tools(self) -> List[Dict[str, Any]]:
        """将所有 Tool 对象转换为 OpenAI function calling schema 列表"""
        return [tool.to_openai_schema() for tool in self._tools.values()]
    

if __name__ == "__main__":
    registry = ToolRegistry()
    def echo(input: str) -> str:
        return input
    registry.register_tool(Tool(name="echo", description="返回输入的文本", fn=echo))
    print(registry.to_openai_tools())