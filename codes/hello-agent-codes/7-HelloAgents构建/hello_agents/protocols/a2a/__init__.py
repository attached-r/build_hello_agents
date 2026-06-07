"""A2A 协议模块 — 基于 a2a-sdk 实现智能体间通信

提供:
    - A2AAgentExecutor — 将 HelloAgents Agent 包装为 A2A 执行器
    - A2AServer        — 启动 A2A 服务器

A2ATool 已移至 hello_agents.tools.builtin.protocol_tools，作为内置工具使用。
"""
from .implementation import A2AAgentExecutor, A2AServer

__all__ = ["A2AAgentExecutor", "A2AServer"]
