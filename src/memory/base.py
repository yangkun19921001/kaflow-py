"""
KaFlow-Py BaseCheckpointer

Checkpointer 抽象基类，定义统一的接口

Author: DevYK
微信公众号: DevYK
Email: yang1001yk@gmail.com
Github: https://github.com/yangkun19921001
"""

from abc import ABC, abstractmethod
from typing import Any, Optional, Dict
from langgraph.checkpoint.base import BaseCheckpointSaver


class BaseCheckpointer(BaseCheckpointSaver, ABC):
    """
    Checkpointer 抽象基类
    
    所有 checkpointer 实现都应继承此类，并实现必要的抽象方法。
    
    设计原则：
    - 单一职责：每个 checkpointer 只负责一种存储方式
    - 开闭原则：对扩展开放，对修改封闭
    - 里氏替换：所有子类都可以替换基类使用
    """
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """
        初始化 Checkpointer
        
        Args:
            config: 配置字典，包含存储相关的配置
        """
        super().__init__()
        self.config = config or {}
        self._is_connected = False
    
    @abstractmethod
    async def setup(self) -> None:
        """
        设置/初始化存储连接
        
        此方法应该：
        - 建立到存储后端的连接
        - 创建必要的数据库/表/集合
        - 验证连接有效性
        """
        pass
    
    @abstractmethod
    async def teardown(self) -> None:
        """
        清理/关闭存储连接
        
        此方法应该：
        - 关闭数据库连接
        - 释放资源
        - 清理临时数据
        """
        pass
    
    @property
    def is_connected(self) -> bool:
        """返回连接状态"""
        return self._is_connected
    
    def validate_config(self) -> bool:
        """
        验证配置的有效性
        
        Returns:
            bool: 配置是否有效
        """
        return True  # 默认实现，子类可以重写

