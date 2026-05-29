
"""
HelloAgents 框架主模块
"""

# 导入核心组件
from .core.agent import Agent
from .core.hello_agents import HelloAgentsLLM
from .core.config import Config
from .core.message import Message

# 定义 SimpleAgent（如果需要的话）
class SimpleAgent(Agent):
    """简单Agent实现，提供基本的运行功能"""
    def run(self, input_text: str, **kwargs) -> str:
        """运行Agent的默认实现"""
        # 构建消息历史
        messages = []
        if self.system_prompt:
            messages.append(Message(content=self.system_prompt, role="system"))
        
        # 添加历史消息
        for msg in self.get_history():
            messages.append(msg.to_dict())
        
        # 添加当前输入
        messages.append(Message(content=input_text, role="user").to_dict())
        
        # 使用LLM生成回复
        response = self.llm.think(messages, temperature=self.config.temperature if self.config else 0.7)
        
        # 添加到历史记录
        self.add_message(Message(content=response, role="assistant"))
        
        return response

__all__ = ['Agent', 'SimpleAgent', 'HelloAgentsLLM', 'Config', 'Message']