"""
KaFlow-Py LLMs 异常定义

定义 LLM 模块相关的异常类，提供清晰的错误信息和错误处理。

Author: DevYK
WeChat: DevYK
Email: yang1001yk@gmail.com
Github: https://github.com/yangkun19921001
"""

from typing import Optional, Any


class LLMError(Exception):
    """LLM 模块基础异常类"""
    
    def __init__(self, message: str, error_code: Optional[str] = None, details: Optional[dict] = None):
        super().__init__(message)
        self.message = message
        self.error_code = error_code
        self.details = details or {}

    def __str__(self) -> str:
        if self.error_code:
            return f"[{self.error_code}] {self.message}"
        return self.message


class LLMConfigError(LLMError):
    """LLM 配置错误异常"""
    
    def __init__(self, message: str, config_key: Optional[str] = None, **kwargs):
        super().__init__(message, error_code="CONFIG_ERROR", **kwargs)
        self.config_key = config_key


class LLMProviderError(LLMError):
    """LLM 提供商错误异常"""
    
    def __init__(self, message: str, provider_name: Optional[str] = None, **kwargs):
        super().__init__(message, error_code="PROVIDER_ERROR", **kwargs)
        self.provider_name = provider_name


class LLMConnectionError(LLMError):
    """LLM 连接错误异常"""
    
    def __init__(self, message: str, **kwargs):
        super().__init__(message, error_code="CONNECTION_ERROR", **kwargs)


class LLMTimeoutError(LLMError):
    """LLM 超时错误异常"""
    
    def __init__(self, message: str, timeout_seconds: Optional[int] = None, **kwargs):
        super().__init__(message, error_code="TIMEOUT_ERROR", **kwargs)
        self.timeout_seconds = timeout_seconds


class LLMRateLimitError(LLMError):
    """LLM 速率限制错误异常"""
    
    def __init__(self, message: str, retry_after: Optional[int] = None, **kwargs):
        super().__init__(message, error_code="RATE_LIMIT_ERROR", **kwargs)
        self.retry_after = retry_after


class LLMAuthenticationError(LLMError):
    """LLM 认证错误异常"""
    
    def __init__(self, message: str = "Authentication failed", **kwargs):
        super().__init__(message, error_code="AUTH_ERROR", **kwargs)


class LLMValidationError(LLMError):
    """LLM 验证错误异常"""
    
    def __init__(self, message: str, field_name: Optional[str] = None, **kwargs):
        super().__init__(message, error_code="VALIDATION_ERROR", **kwargs)
        self.field_name = field_name 