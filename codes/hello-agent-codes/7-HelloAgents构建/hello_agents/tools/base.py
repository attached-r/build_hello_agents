from abc import ABC, abstractmethod
from typing import Dict, List, Any, Callable, Optional
from pydantic import BaseModel

# ======================================================================
# ToolParameter — 工具参数定义
# ======================================================================
class ToolParameter(BaseModel):
    """工具参数定义"""
    name: str
    type: str
    description: str
    required: bool = True
    default: Any = None


# ======================================================================
# Tool — 工具基类
# ======================================================================

class Tool(ABC):
    """工具基类"""

    def __init__(self, name: str, description: str):
        self.name = name
        self.description = description

    @abstractmethod
    def run(self, parameters: Dict[str, Any]) -> str:
        """执行工具"""
        pass

    @abstractmethod
    def get_parameters(self) -> List[ToolParameter]:
        """获取工具参数定义"""
        pass

    def to_openai_schema(self) -> Dict[str, Any]:
        """转换为 OpenAI function calling schema 格式

        Returns:
            符合 OpenAI function calling 标准的 schema
        """
        parameters = self.get_parameters()

        properties = {}
        required = []

        for param in parameters:
            prop = {
                "type": param.type,
                "description": param.description
            }

            if param.default is not None:
                prop["description"] = f"{param.description} (默认: {param.default})"

            if param.type == "array":
                prop["items"] = {"type": "string"}

            properties[param.name] = prop

            if param.required:
                required.append(param.name)

        return {
            "type": "function",
            "function": {
                "name": self.name,
                "description": self.description,
                "parameters": {
                    "type": "object",
                    "properties": properties,
                    "required": required,
                },
            },
        }


# ======================================================================
# FunctionTool — 函数工具包装
# ======================================================================

class FunctionTool(Tool):
    """将普通函数包装为 Tool 对象

    适用于无需创建 Tool 子类、直接注册函数的场景。
    通过 ToolParameter 列表定义参数，确保 schema 一致性。
    """

    def __init__(
        self,
        name: str,
        description: str,
        fn: Callable[..., str],
        parameters: Optional[List[ToolParameter]] = None,
    ):
        super().__init__(name, description)
        self._fn = fn
        self._parameters = parameters or []

    def run(self, parameters: Dict[str, Any]) -> str:
        # 兼容场景：上层传递 {"input": "..."} 但工具期望具体参数名
        if "input" in parameters and self._parameters:
            param_names = [p.name for p in self._parameters]
            if "input" not in param_names:
                # 将 input 映射到工具的第一个参数
                return str(self._fn(**{param_names[0]: parameters["input"]}))
        return str(self._fn(**parameters))

    def get_parameters(self) -> List[ToolParameter]:
        return self._parameters


if __name__ == "__main__":

    # 测试 FunctionTool
    def echo(input: str) -> str:
        return input

    echo_tool = FunctionTool(
        name="echo",
        description="返回输入的文本",
        fn=echo,
        parameters=[
            ToolParameter(name="input", type="string", description="要回显的文本"),
        ],
    )
    print(echo_tool.to_openai_schema())