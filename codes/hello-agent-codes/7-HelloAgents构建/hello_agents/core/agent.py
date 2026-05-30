"""Agent基类"""
import os
import sys
from abc import ABC, abstractmethod   #? 抽象类和抽象方法
from typing import Dict, List, Optional, Any

# ── 路径引导: 自动向上搜索项目根目录 ────────────
_BASE = os.path.abspath(__file__)
while not os.path.isdir(os.path.join(os.path.dirname(_BASE), 'hello_agents')):
    _BASE = os.path.dirname(_BASE)
    if os.path.dirname(_BASE) == _BASE:
        break
_PROJECT_ROOT = os.path.dirname(_BASE)
if _PROJECT_ROOT not in sys.path:
    sys.path.insert(0, _PROJECT_ROOT)

from hello_agents.core.message import Message
from hello_agents.core.hello_agents import HelloAgentsLLM
from hello_agents.core.config import Config
from hello_agents.context import ContextBuilder, ContextPacket

class Agent(ABC):
    """Agent基类"""  #? ABC 抽象类 不能直接实例化，必须继承后实现

    def __init__(
        self,
        name: str,
        llm: HelloAgentsLLM,        #? 使用基类 HelloAgentsLLM 实现 LLM 功能
        system_prompt: Optional[str] = None,
        config: Optional[Config] = None,
        context_builder: Optional[ContextBuilder] = None,
    ):
        self.name = name
        self.llm = llm
        self.system_prompt = system_prompt
        self.config = config or Config()
        self.context_builder = context_builder
        self._history: list[Message] = []
    
    @abstractmethod   #! 抽象方法，必须在子类中实现
    def run(self, input_text: str, **kwargs) -> str:
        """运行Agent"""
        pass
    
    def add_message(self, message: Message):
        """添加消息到历史记录"""
        self._history.append(message)
    
    def clear_history(self):
        """清空历史记录"""
        self._history.clear()
    
    def get_history(self) -> list[Message]:
        """获取历史记录"""
        return self._history.copy()

    # ── 上下文构建 ──────────────────────────────────────────────

    def build_context_messages(
        self,
        user_query: str,
        system_prompt: Optional[str] = None,
        custom_packets: Optional[List[ContextPacket]] = None,
    ) -> List[Dict[str, str]]:
        """
        使用 ContextBuilder 构建消息列表。

        若未配置 context_builder，降级为手动拼接 system_prompt + history + user_query。
        """
        if not self.context_builder:
            return self._fallback_messages(user_query, system_prompt)

        return self.context_builder.build_to_dicts(
            user_query=user_query,
            conversation_history=self._history,
            system_instructions=system_prompt or self.system_prompt,
            custom_packets=custom_packets,
        )

    def _fallback_messages(
        self,
        user_query: str,
        system_prompt: Optional[str] = None,
    ) -> List[Dict[str, str]]:
        """降级方案：无 ContextBuilder 时手动拼接消息列表。"""
        messages: List[Dict[str, str]] = []
        sp = system_prompt or self.system_prompt
        if sp:
            messages.append({"role": "system", "content": sp})
        for msg in self._history:
            messages.append({"role": msg.role, "content": msg.content})
        messages.append({"role": "user", "content": user_query})
        return messages

    def __str__(self) -> str:
        return f"Agent(name={self.name}, provider={self.llm.provider})"
