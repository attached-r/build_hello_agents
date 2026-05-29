"""消息系统"""
from typing import Optional, Dict, Any, Literal
from datetime import datetime    # 导入 datetime 类，用于记录消息时间 
from pydantic import BaseModel   # 导入 BaseModel 类，用于定义数据模型

#! 定义消息角色的类型，限制其取值 Literal是字面量类型
MessageRole = Literal["user", "assistant", "system", "tool"] 

class Message(BaseModel):
    """消息类"""
    
    content: str
    role: MessageRole
    timestamp: datetime = None
    metadata: Optional[Dict[str, Any]] = None
    
    def __init__(self, content: str, role: MessageRole, **kwargs):
        super().__init__(  #? BaseModel 是 pydantic 提供的基类，用于定义数据模型
            content=content,
            role=role,
            timestamp=kwargs.get('timestamp', datetime.now()),
            metadata=kwargs.get('metadata', {})
        )
    
    #? 转换为字典格式（OpenAI API格式）
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典格式（OpenAI API格式）"""
        return {
            "role": self.role,
            "content": self.content
        }
    
    #? 转换为字符串格式
    def __str__(self) -> str:
        return f"[{self.role}] {self.content}"
    
#? 关键库/类说明：
# 1. pydantic.BaseModel: 用于数据校验和解析的基类，提供自动类型转换和验证功能
# 2. typing.Optional: 表示某个类型可以是该类型或 None
# 3. typing.Dict: 表示字典类型，Dict[K, V] 表示键为 K 类型、值为 V 类型的字典
# 4. typing.Any: 表示任意类型
# 5. typing.Literal: 限制值只能是特定的字面量值
# 6. datetime: 日期时间类，用于处理时间相关操作

if __name__ == "__main__":
    msg = Message("你好", "user")
    print(msg)
    print(msg.to_dict())