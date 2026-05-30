"""
记忆系统基础数据结构与抽象基类。

核心组件:
  - MemoryItem: 记忆数据单元（标准化字段）
  - MemoryConfig: 记忆系统配置
  - BaseMemory: 所有记忆类型的抽象基类
"""

import uuid
from abc import ABC, abstractmethod
from datetime import datetime
from typing import Any, Optional

from pydantic import BaseModel, Field


class MemoryItem(BaseModel):
    """一条记忆的标准结构"""

    id: str = Field(default_factory=lambda: uuid.uuid4().hex[:12])
    content: str = ""
    memory_type: str = "working"         # working / episodic / semantic / perceptual
    user_id: str = ""
    session_id: str = ""
    importance: float = 0.5              # [0, 1]
    timestamp: datetime = Field(default_factory=datetime.now)
    metadata: dict[str, Any] = Field(default_factory=dict)


class MemoryConfig(BaseModel):
    """记忆系统配置"""

    # 工作记忆
    working_ttl_minutes: int = 60
    working_capacity: int = 50

    # 情景记忆
    episodic_db_path: str = "memory.db" # 数据库文件路径
    episodic_db_type: str = "mysql"     # sqlite / mysql

    # 预留类型开关
    semantic_enabled: bool = False
    perceptual_enabled: bool = False

    # 嵌入
    embedding_model: str = "fastembed"    # tfidf / fastembed
    embedding_dim: int = 384

    # 整合与遗忘
    consolidation_importance_threshold: float = 0.7
    forget_importance_threshold: float = 0.2
    forget_max_age_days: int = 30


class BaseMemory(ABC):
    """
    记忆类型的抽象基类。
    所有具体记忆类型（WorkingMemory / EpisodicMemory 等）必须继承此类。
    """

    def __init__(self, config: MemoryConfig):
        self.config = config

    @abstractmethod
    def add(self, item: MemoryItem) -> str:
        """添加一条记忆，返回记忆 ID"""
        ...

    @abstractmethod
    def search(self, query: str, limit: int = 5, **kwargs) -> list[MemoryItem]:
        """检索记忆"""
        ...

    @abstractmethod
    def get(self, memory_id: str) -> Optional[MemoryItem]:
        """根据 ID 获取单条记忆"""
        ...

    @abstractmethod
    def update(self, memory_id: str, **updates) -> bool:
        """更新记忆字段"""
        ...

    @abstractmethod
    def delete(self, memory_id: str) -> bool:
        """删除单条记忆"""
        ...

    @abstractmethod
    def clear(self) -> int:
        """清空所有记忆，返回删除条数"""
        ...

    @abstractmethod
    def count(self) -> int:
        """统计记忆条数"""
        ...
