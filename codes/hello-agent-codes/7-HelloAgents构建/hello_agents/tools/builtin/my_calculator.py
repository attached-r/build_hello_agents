# my_calculator_tool.py
import ast          #? 用于解析和求值表达式
import operator     #? 提供基本运算符函数
import math
import os
import sys

# ── 路径引导: 自动向上搜索项目根目录 ────────────
_BASE = os.path.abspath(__file__)
while not os.path.isdir(os.path.join(os.path.dirname(_BASE), 'hello_agents')):
    _BASE = os.path.dirname(_BASE)
    if os.path.dirname(_BASE) == _BASE:
        break
_PROJECT_ROOT = os.path.dirname(_BASE)
if _PROJECT_ROOT not in sys.path:
    sys.path.insert(0, _PROJECT_ROOT)

from hello_agents.tools.registry import ToolRegistry

def my_calculate(expression: str) -> str:
    """简单的数学计算函数"""
    if not expression.strip():
        return "计算表达式不能为空"

    # 支持的基本运算
    operators = {
        ast.Add: operator.add,      # +
        ast.Sub: operator.sub,      # -
        ast.Mult: operator.mul,     # *
        ast.Div: operator.truediv,  # /
    }

    # 支持的基本函数
    functions = {
        'sqrt': math.sqrt,
        'pi': math.pi,
    }

    try:
        node = ast.parse(expression, mode='eval')
        result = _eval_node(node.body, operators, functions)
        return str(result)
    except:
        return "计算失败，请检查表达式格式"

def _eval_node(node, operators, functions):
    """简化的表达式求值"""
    if isinstance(node, ast.Constant):
        return node.value
    elif isinstance(node, ast.BinOp):
        left = _eval_node(node.left, operators, functions)
        right = _eval_node(node.right, operators, functions)
        op = operators.get(type(node.op))
        return op(left, right)
    elif isinstance(node, ast.Call):
        func_name = node.func.id
        if func_name in functions:
            args = [_eval_node(arg, operators, functions) for arg in node.args]
            return functions[func_name](*args)
    elif isinstance(node, ast.Name):
        if node.id in functions:
            return functions[node.id]

def create_calculator_registry():
    """创建包含计算器的工具注册表"""
    registry = ToolRegistry()

    # 注册计算器函数
    registry.register_function(
        name="my_calculator",
        description="简单的数学计算工具，支持基本运算(+,-,*,/)和sqrt函数",
        func=my_calculate
    )

    return registry


if __name__ == "__main__":
    print("=== 测试计算器工具 ===\n")
    
    # 测试单独的计算函数
    print("1. 测试单独的计算函数：")
    test_expressions = [
        "2 + 3",
        "10 - 4",
        "5 * 6",
        "15 / 3",
        "sqrt(16)",
        "2 * (3 + 4)",
        "",  # 空表达式测试
        "invalid expression"  # 无效表达式测试
    ]
    
    for expr in test_expressions:
        result = my_calculate(expr)
        print(f"  {expr} = {result}")
    
    print()
    
    # 测试工具注册表
    print("2. 测试工具注册表：")
    registry = create_calculator_registry()
    print(f"已注册工具数量: {len(registry._functions)}")
    for name, func_info in registry._functions.items():
        print(f"  - {name}: {func_info['description']}")
    
    print()
    
    # 测试注册表中的计算器函数
    print("3. 测试注册表中的计算器函数：")
    calc_func = registry._functions["my_calculator"]["func"]
    test_results = []
    for expr in ["10 + 5", "20 / 4", "sqrt(25)"]:
        result = calc_func(expr)
        test_results.append((expr, result))
        print(f"  {expr} = {result}")
    
    print("\n=== 计算器工具测试完成 ===")