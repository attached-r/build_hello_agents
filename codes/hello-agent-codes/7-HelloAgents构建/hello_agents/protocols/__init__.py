"""
协议模块 — MCP / A2A / ANP 等外部通信协议封装

当前实现了:
  - MCP (Model Context Protocol): 智能体与外部工具的标准化通信

计划实现:
  - A2A (Agent-to-Agent Protocol): 智能体间点对点协作
  - ANP (Agent Network Protocol): 大规模智能体网络基础设施
"""

from .mcp import MCPClient

__all__ = ["MCPClient"]
