# d:\learnings\py_learning\agent_learn\Hello_Agents\codes\hello-agent-codes\7-HelloAgents构建\hello_agents\agents\__init__.py
"""
HelloAgents Agent 模块

提供五种 Agent 实现:
  - MySimpleAgent: 基础对话 + 工具调用
  - MyFunctionAgent: 函数调用模式智能体
  - ReActAgent: 推理-行动循环 (Thought→Action→Observation)
  - ReflectionAgent: 反思迭代 (生成→评审→优化)
  - PlanAndSolveAgent: 先规划后执行
"""
from .my_simple_agent import MySimpleAgent
from .my_function_agent import MyFunctionAgent
from .react_agent import ReActAgent
from .reflection_agent import ReflectionAgent
from .plan_solve_agent import PlanAndSolveAgent

__all__ = [
    'MySimpleAgent',
    'MyFunctionAgent',
    'ReActAgent',
    'ReflectionAgent',
    'PlanAndSolveAgent',
]