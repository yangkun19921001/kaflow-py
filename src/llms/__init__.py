# -*- coding: utf-8 -*-
"""
KaFlow-Py LLMs 模块

简化的 LLM 封装模块，支持：
- 多种 LLM 提供商（OpenAI、Claude、DeepSeek、Ollama 等）
- 外部传参配置
- 函数重载机制
- 缓存优化
- 类型安全

Author: DevYK
WeChat: DevYK
Email: yang1001yk@gmail.com
Github: https://github.com/yangkun19921001
"""

# 核心管理器和工厂
from .manager import LLMManager, get_manager

# 便捷函数（支持函数重载）
from .manager import (
    get_llm,
)

# 配置相关
from .config import (
    LLMConfig,
    LLMProviderType,
)

# 工厂和提供商（高级使用）
from .factory import LLMFactory
from .providers import (
    LLMProvider,
    OpenAIProvider,
    AzureOpenAIProvider,
    ClaudeProvider,
    DeepSeekProvider,
    OllamaProvider,
    CustomProvider
)

# 异常处理
from .exceptions import (
    LLMError,
    LLMConfigError,
    LLMProviderError,
    LLMConnectionError,
    LLMTimeoutError,
    LLMRateLimitError,
    LLMAuthenticationError,
    LLMValidationError
)

__version__ = "2.0.0"

__all__ = [
    # 核心类
    "LLMManager",
    "LLMFactory",

    # 便捷函数
    "get_manager",
    "get_llm",

    # 配置
    "LLMConfig",
    "LLMProviderType",

    # 提供商
    "LLMProvider",
    "OpenAIProvider",
    "AzureOpenAIProvider",
    "ClaudeProvider",
    "DeepSeekProvider",
    "OllamaProvider",
    "CustomProvider",

    # 异常
    "LLMError",
    "LLMConfigError",
    "LLMProviderError",
    "LLMConnectionError",
    "LLMTimeoutError",
    "LLMRateLimitError",
    "LLMAuthenticationError",
    "LLMValidationError",
] 