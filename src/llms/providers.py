"""
KaFlow-Py LLMs 提供商实现

定义 LLM 提供商的抽象基类和具体实现，支持多种 LLM 服务提供商。
采用策略模式，便于扩展新的提供商。

Author: DevYK
微信公众号: DevYK
Email: yang1001yk@gmail.com
Github: https://github.com/yangkun19921001
"""

import httpx
from abc import ABC, abstractmethod
from typing import Dict, Any, Optional, AsyncIterator
from langchain_core.language_models import BaseChatModel
from langchain_openai import ChatOpenAI, AzureChatOpenAI
from langchain_anthropic import ChatAnthropic
from langchain_community.llms import Ollama

from .config import LLMConfig, LLMProviderType
from .exceptions import LLMProviderError, LLMConnectionError, LLMAuthenticationError


class LLMProvider(ABC):
    """LLM 提供商抽象基类"""
    
    def __init__(self, config: LLMConfig):
        """
        初始化提供商
        
        Args:
            config: LLM 配置对象
        """
        self.config = config
        self._client: Optional[BaseChatModel] = None
        self._http_client: Optional[httpx.Client] = None
        self._async_http_client: Optional[httpx.AsyncClient] = None
    
    @property
    def provider_name(self) -> str:
        """提供商名称"""
        return self.config.provider.value
    
    @abstractmethod
    def create_client(self) -> BaseChatModel:
        """
        创建 LLM 客户端实例
        
        Returns:
            LangChain 兼容的聊天模型实例
            
        Raises:
            LLMProviderError: 创建客户端失败
        """
        pass
    
    def get_client(self) -> BaseChatModel:
        """
        获取 LLM 客户端实例（懒加载）
        
        Returns:
            LangChain 兼容的聊天模型实例
        """
        if self._client is None:
            self._client = self.create_client()
        return self._client
    
    def _create_http_clients(self) -> tuple[Optional[httpx.Client], Optional[httpx.AsyncClient]]:
        """创建 HTTP 客户端"""
        client_kwargs = {}
        
        # SSL 验证配置
        if not self.config.verify_ssl:
            client_kwargs['verify'] = False
        
        # 代理配置
        if self.config.proxy:
            client_kwargs['proxies'] = self.config.proxy
        
        # 超时配置
        if self.config.timeout:
            client_kwargs['timeout'] = self.config.timeout
        
        # 自定义请求头
        if self.config.headers:
            client_kwargs['headers'] = self.config.headers
        
        if client_kwargs:
            http_client = httpx.Client(**client_kwargs)
            async_http_client = httpx.AsyncClient(**client_kwargs)
            return http_client, async_http_client
        
        return None, None
    
    def _get_common_params(self) -> Dict[str, Any]:
        """获取通用参数"""
        params = {
            'model': self.config.model,
            'temperature': self.config.temperature,
            'max_tokens': self.config.max_tokens,
            'max_retries': self.config.max_retries,
        }
        
        # 添加 HTTP 客户端
        if not self.config.verify_ssl or self.config.proxy or self.config.headers:
            http_client, async_http_client = self._create_http_clients()
            if http_client:
                params['http_client'] = http_client
            if async_http_client:
                params['http_async_client'] = async_http_client
        
        return {k: v for k, v in params.items() if v is not None}
    
    def validate_connection(self) -> bool:
        """
        验证连接是否可用
        
        Returns:
            连接状态
            
        Raises:
            LLMConnectionError: 连接验证失败
        """
        try:
            client = self.get_client()
            # 发送一个简单的测试消息
            response = client.invoke("Hello")
            return True
        except Exception as e:
            raise LLMConnectionError(
                f"Connection validation failed for {self.provider_name}: {str(e)}"
            ) from e
    
    def get_model_info(self) -> Dict[str, Any]:
        """获取模型信息"""
        return {
            'provider': self.provider_name,
            'model': self.config.model,
            'base_url': self.config.base_url,
            'max_tokens': self.config.max_tokens,
            'temperature': self.config.temperature,
        }
    
    def __del__(self):
        """清理资源"""
        if self._http_client:
            self._http_client.close()
        if self._async_http_client and not self._async_http_client.is_closed:
            # 异步客户端需要在异步上下文中关闭
            pass


class OpenAIProvider(LLMProvider):
    """OpenAI 提供商实现"""
    
    def create_client(self) -> BaseChatModel:
        """创建 OpenAI 客户端"""
        try:
            params = self._get_common_params()
            params.update({
                'openai_api_key': self.config.api_key,
                'openai_api_base': self.config.base_url or "https://api.openai.com/v1",
            })
            
            # 添加 OpenAI 特定参数
            if self.config.top_p is not None:
                params['top_p'] = self.config.top_p
            if self.config.frequency_penalty is not None:
                params['frequency_penalty'] = self.config.frequency_penalty
            if self.config.presence_penalty is not None:
                params['presence_penalty'] = self.config.presence_penalty
            
            return ChatOpenAI(**params)
            
        except Exception as e:
            raise LLMProviderError(
                f"Failed to create OpenAI client: {str(e)}",
                provider_name="openai"
            ) from e


class AzureOpenAIProvider(LLMProvider):
    """Azure OpenAI 提供商实现"""
    
    def create_client(self) -> BaseChatModel:
        """创建 Azure OpenAI 客户端"""
        try:
            if not self.config.azure_endpoint:
                raise LLMProviderError(
                    "azure_endpoint is required for Azure OpenAI",
                    provider_name="azure_openai"
                )
            
            params = self._get_common_params()
            params.update({
                'azure_endpoint': self.config.azure_endpoint,
                'openai_api_key': self.config.api_key,
                'azure_deployment': self.config.azure_deployment or self.config.model,
                'openai_api_version': self.config.api_version or "2024-02-01",
            })
            
            # 添加 OpenAI 特定参数
            if self.config.top_p is not None:
                params['top_p'] = self.config.top_p
            if self.config.frequency_penalty is not None:
                params['frequency_penalty'] = self.config.frequency_penalty
            if self.config.presence_penalty is not None:
                params['presence_penalty'] = self.config.presence_penalty
            
            return AzureChatOpenAI(**params)
            
        except Exception as e:
            raise LLMProviderError(
                f"Failed to create Azure OpenAI client: {str(e)}",
                provider_name="azure_openai"
            ) from e


class ClaudeProvider(LLMProvider):
    """Claude (Anthropic) 提供商实现"""
    
    def create_client(self) -> BaseChatModel:
        """创建 Claude 客户端"""
        try:
            params = self._get_common_params()
            params.update({
                'anthropic_api_key': self.config.api_key,
                'model': self.config.model,
            })
            
            # Claude 特定配置
            if self.config.base_url:
                params['anthropic_api_url'] = self.config.base_url
            
            # 移除 Claude 不支持的参数
            params.pop('max_tokens', None)  # Claude 使用 max_tokens_to_sample
            if self.config.max_tokens:
                params['max_tokens_to_sample'] = self.config.max_tokens
            
            return ChatAnthropic(**params)
            
        except Exception as e:
            raise LLMProviderError(
                f"Failed to create Claude client: {str(e)}",
                provider_name="claude"
            ) from e


class DeepSeekProvider(LLMProvider):
    """DeepSeek 提供商实现"""
    
    def create_client(self) -> BaseChatModel:
        """创建 DeepSeek 客户端"""
        try:
            # DeepSeek 使用 OpenAI 兼容的 API
            params = self._get_common_params()
            params.update({
                'openai_api_key': self.config.api_key,
                'openai_api_base': self.config.base_url or "https://api.deepseek.com/v1",
                'model': self.config.model,
            })
            
            # 添加 DeepSeek 特定参数
            if self.config.top_p is not None:
                params['top_p'] = self.config.top_p
            if self.config.frequency_penalty is not None:
                params['frequency_penalty'] = self.config.frequency_penalty
            if self.config.presence_penalty is not None:
                params['presence_penalty'] = self.config.presence_penalty
            
            return ChatOpenAI(**params)
            
        except Exception as e:
            raise LLMProviderError(
                f"Failed to create DeepSeek client: {str(e)}",
                provider_name="deepseek"
            ) from e


class OllamaProvider(LLMProvider):
    """Ollama 提供商实现"""
    
    def create_client(self) -> BaseChatModel:
        """创建 Ollama 客户端"""
        try:
            params = {
                'model': self.config.model,
                'base_url': self.config.base_url or "http://localhost:11434",
            }
            
            # Ollama 特定参数
            if self.config.temperature is not None:
                params['temperature'] = self.config.temperature
            if self.config.timeout is not None:
                params['timeout'] = self.config.timeout
            
            return Ollama(**params)
            
        except Exception as e:
            raise LLMProviderError(
                f"Failed to create Ollama client: {str(e)}",
                provider_name="ollama"
            ) from e


class CustomProvider(LLMProvider):
    """自定义提供商实现"""
    
    def create_client(self) -> BaseChatModel:
        """创建自定义客户端"""
        try:
            # 默认使用 OpenAI 兼容的接口
            params = self._get_common_params()
            params.update({
                'openai_api_key': self.config.api_key,
                'openai_api_base': self.config.base_url,
                'model': self.config.model,
            })
            
            return ChatOpenAI(**params)
            
        except Exception as e:
            raise LLMProviderError(
                f"Failed to create custom client: {str(e)}",
                provider_name="custom"
            ) from e


# 提供商注册表
PROVIDER_REGISTRY: Dict[LLMProviderType, type[LLMProvider]] = {
    LLMProviderType.OPENAI: OpenAIProvider,
    LLMProviderType.AZURE_OPENAI: AzureOpenAIProvider,
    LLMProviderType.CLAUDE: ClaudeProvider,
    LLMProviderType.DEEPSEEK: DeepSeekProvider,
    LLMProviderType.OLLAMA: OllamaProvider,
    LLMProviderType.CUSTOM: CustomProvider,
}


def create_provider(config: LLMConfig) -> LLMProvider:
    """
    根据配置创建相应的提供商实例
    
    Args:
        config: LLM 配置
        
    Returns:
        提供商实例
        
    Raises:
        LLMProviderError: 不支持的提供商类型
    """
    provider_class = PROVIDER_REGISTRY.get(config.provider)
    if not provider_class:
        raise LLMProviderError(
            f"Unsupported provider type: {config.provider}",
            provider_name=config.provider.value
        )
    
    return provider_class(config)


def register_provider(provider_type: LLMProviderType, provider_class: type[LLMProvider]):
    """
    注册新的提供商类型
    
    Args:
        provider_type: 提供商类型
        provider_class: 提供商类
    """
    PROVIDER_REGISTRY[provider_type] = provider_class


def get_available_providers() -> list[LLMProviderType]:
    """获取所有可用的提供商类型"""
    return list(PROVIDER_REGISTRY.keys()) 