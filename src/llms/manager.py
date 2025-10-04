"""
KaFlow-Py LLM 管理器

简化的 LLM 管理器，只支持参数传入，实现函数重载机制。

Author: DevYK
微信公众号: DevYK
Email: yang1001yk@gmail.com
Github: https://github.com/yangkun19921001
"""

from typing import Any
from contextlib import contextmanager
import threading

from .config import LLMConfig, LLMProviderType
from .factory import LLMFactory
from .exceptions import LLMError


class LLMManager:
    """简化的 LLM 管理器"""
    
    def __init__(self):
        """
        初始化 LLM 管理器
        
        Args:
        """
        self._factory = LLMFactory()
        self._lock = threading.RLock()
    
    def get_llm(
        self,
        config: LLMConfig,
    ) -> Any:
        """
        获取 LLM 实例
        
        Args:
            config: 配置对象
            
        Returns:
            LLM 实例
            
        Examples:
            config = LLMConfig(provider="openai", api_key="xxx")
            llm = manager.get_llm(config)
            
            config = LLMConfig(provider="openai", api_key="xxx", temperature=0.9)
            llm = manager.get_llm(config)
        """
        with self._lock:
            try:
                # 通过工厂创建 LLM
                return self._factory.create_llm(config)
            except Exception as e:
                if isinstance(e, LLMError):
                    raise
                raise LLMError(f"Failed to get LLM: {str(e)}") from e


# 全局管理器实例
_global_manager: LLMManager = None
_manager_lock = threading.RLock()


def get_manager() -> LLMManager:
    """获取全局 LLM 管理器实例"""
    global _global_manager
    with _manager_lock:
        if _global_manager is None:
            _global_manager = LLMManager()
        return _global_manager


def get_llm(config: LLMConfig) -> Any:
    """
    全局 get_llm 函数
    
    Args:
        config: LLM 配置
        
    Returns:
        LLM 实例
    """
    manager = get_manager()
    return manager.get_llm(config)
    
