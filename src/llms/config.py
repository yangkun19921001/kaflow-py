# -*- coding: utf-8 -*-
"""
KaFlow-Py LLM 配置模块

简化的配置系统，只支持参数传入，不依赖文件或环境变量。

Author: DevYK
WeChat: DevYK
Email: yang1001yk@gmail.com
Github: https://github.com/yangkun19921001
"""

from typing import Optional, Dict, Any, Union
from enum import Enum
from pydantic import BaseModel, Field
import os


class LLMProviderType(str, Enum):
    """LLM 提供商类型"""
    OPENAI = "openai"
    AZURE_OPENAI = "azure_openai"
    CLAUDE = "claude"
    DEEPSEEK = "deepseek"
    OLLAMA = "ollama"
    CUSTOM = "custom"


class LLMConfig(BaseModel):
    """LLM 配置模型"""
    
    # 基础配置
    provider: LLMProviderType = Field(LLMProviderType.OPENAI, description="LLM 提供商")
    api_key: str = Field(..., description="API 密钥")
    base_url: Optional[str] = Field(None, description="API 基础 URL")
    model: str = Field("gpt-4o-mini", description="模型名称")
    
    # 生成参数
    temperature: Optional[float] = Field(0.7, description="温度参数", ge=0.0, le=2.0)
    max_tokens: Optional[int] = Field(1024, description="最大 token 数", ge=1, le=32768)
    top_p: Optional[float] = Field(1.0, description="核采样参数", ge=0.0, le=1.0)
    frequency_penalty: Optional[float] = Field(0.0, description="频率惩罚", ge=-2.0, le=2.0)
    presence_penalty: Optional[float] = Field(0.0, description="存在惩罚", ge=-2.0, le=2.0)
    
    # 连接配置
    timeout: Optional[int] = Field(30, description="超时时间(秒)", ge=1, le=300)
    max_retries: Optional[int] = Field(3, description="最大重试次数", ge=0, le=10)
    verify_ssl: Optional[bool] = Field(True, description="验证 SSL")
    proxy: Optional[str] = Field(None, description="代理设置")
    headers: Optional[Dict[str, str]] = Field(None, description="自定义请求头")
    
    # Azure OpenAI 特定配置
    azure_endpoint: Optional[str] = Field(None, description="Azure 端点")
    api_version: Optional[str] = Field("2024-02-15-preview", description="API 版本")
    azure_deployment: Optional[str] = Field(None, description="Azure 部署名称")
    
    # Ollama 特定配置
    ollama_host: Optional[str] = Field("http://localhost:11434", description="Ollama 主机地址")
    
    class Config:
        extra = "forbid"
    
