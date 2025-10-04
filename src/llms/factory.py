"""
KaFlow-Py LLM 工厂类

简化的工厂类，负责根据配置创建 LLM 实例，支持缓存优化。

Author: DevYK
微信公众号: DevYK
Email: yang1001yk@gmail.com
Github: https://github.com/yangkun19921001
"""

import threading
from typing import Dict, Optional, Any
from langchain_core.language_models import BaseChatModel

from .config import LLMConfig
from .providers import create_provider
from .exceptions import LLMError, LLMProviderError


class LLMFactory:
    """简化的 LLM 工厂类"""
    
    def __init__(self):
        """
        初始化 LLM 工厂
        
        Args:
        """
        self._lock = threading.RLock()
    
    def create_llm(self, config: LLMConfig) -> BaseChatModel:
        """
        根据配置创建 LLM 实例
        
        Args:
            config: LLM 配置对象
            
        Returns:
            LangChain 兼容的聊天模型实例
            
        Raises:
            LLMError: 创建失败
        """
        with self._lock:
            try:
                # 创建提供商
                provider = create_provider(config)
                
                # 创建客户端
                client = provider.create_client()
                
                # 将原始配置附加到 LLM 实例上，方便其他工具（如 browser_use）检测 provider 类型
                # 使用 _llm_config 作为内部属性名
                setattr(client, "_llm_config", config)
                
                return client
                
            except Exception as e:
                if isinstance(e, (LLMError, LLMProviderError)):
                    raise
                raise LLMError(f"Failed to create LLM: {str(e)}") from e
    


# 全局工厂实例
_global_factory: Optional[LLMFactory] = None
_factory_lock = threading.RLock()


def get_factory() -> LLMFactory:
    """获取全局工厂实例"""
    global _global_factory
    
    with _factory_lock:
        if _global_factory is None:
            _global_factory = LLMFactory()
        return _global_factory 