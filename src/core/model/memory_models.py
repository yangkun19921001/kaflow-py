"""
KaFlow-Py 记忆存储数据模型定义

基于协议标准定义的记忆存储配置模型，包括：
- MemoryBaseConfig: 记忆存储基础配置
- MemoryTypes: 记忆类型配置
- CleanupConfig: 清理策略配置
- MemorySchema: 记忆存储配置模式

Author: DevYK
WeChat: DevYK
Email: yang1001yk@gmail.com
Github: https://github.com/yangkun19921001
"""

from typing import Optional, Dict, Any
from pydantic import BaseModel, Field, validator
from enum import Enum
from .base_models import ValidationRule, MemoryProvider, MemoryConnectionConfig


class CleanupStrategy(str, Enum):
    """清理策略枚举"""
    LRU = "lru"  # 最近最少使用
    LFU = "lfu"  # 最不经常使用
    TTL = "ttl"  # 基于过期时间
    SIZE = "size"  # 基于大小限制
    CUSTOM = "custom"  # 自定义策略


class ConversationMemory(BaseModel):
    """对话记忆配置"""
    enabled: Optional[bool] = Field(True, description="是否启用")
    ttl: Optional[int] = Field(7200, description="过期时间(秒)", ge=60)
    max_messages: Optional[int] = Field(100, description="最大消息数", ge=1)

    class Config:
        extra = "forbid"


class WorkflowStateMemory(BaseModel):
    """工作流状态记忆配置"""
    enabled: Optional[bool] = Field(True, description="是否启用")
    ttl: Optional[int] = Field(3600, description="过期时间(秒)", ge=60)
    checkpoint_interval: Optional[int] = Field(60, description="检查点间隔(秒)", ge=1)

    class Config:
        extra = "forbid"


class AgentContextMemory(BaseModel):
    """Agent上下文记忆配置"""
    enabled: Optional[bool] = Field(True, description="是否启用")
    ttl: Optional[int] = Field(1800, description="过期时间(秒)", ge=60)
    max_context_size: Optional[int] = Field(4096, description="最大上下文大小(tokens)", ge=1)

    class Config:
        extra = "forbid"


class ToolCacheMemory(BaseModel):
    """工具缓存记忆配置"""
    enabled: Optional[bool] = Field(True, description="是否启用")
    ttl: Optional[int] = Field(900, description="过期时间(秒)", ge=60)
    max_cache_size: Optional[str] = Field("50MB", description="最大缓存大小")

    @validator('max_cache_size')
    def validate_max_cache_size(cls, v):
        """验证缓存大小格式"""
        if not v.endswith(('B', 'KB', 'MB', 'GB', 'TB')):
            raise ValueError("max_cache_size must end with B, KB, MB, GB, or TB")
        return v

    class Config:
        extra = "forbid"


class KnowledgeCacheMemory(BaseModel):
    """知识缓存记忆配置"""
    enabled: Optional[bool] = Field(True, description="是否启用")
    ttl: Optional[int] = Field(86400, description="过期时间(秒)", ge=60)
    max_entries: Optional[int] = Field(1000, description="最大条目数", ge=1)

    class Config:
        extra = "forbid"


class MemoryTypes(BaseModel):
    """记忆类型配置"""
    conversation: Optional[ConversationMemory] = Field(None, description="对话记忆")
    workflow_state: Optional[WorkflowStateMemory] = Field(None, description="工作流状态记忆")
    agent_context: Optional[AgentContextMemory] = Field(None, description="Agent上下文记忆")
    tool_cache: Optional[ToolCacheMemory] = Field(None, description="工具缓存记忆")
    knowledge_cache: Optional[KnowledgeCacheMemory] = Field(None, description="知识缓存记忆")

    class Config:
        extra = "forbid"


class CleanupConfig(BaseModel):
    """清理策略配置"""
    enabled: Optional[bool] = Field(True, description="是否启用清理")
    strategy: Optional[CleanupStrategy] = Field(CleanupStrategy.LRU, description="清理策略类型")
    interval: Optional[int] = Field(3600, description="清理执行间隔(秒)", ge=60, le=86400)
    batch_size: Optional[int] = Field(100, description="单次清理批次大小", ge=1, le=1000)

    class Config:
        extra = "forbid"


class MemoryBaseConfig(BaseModel):
    """记忆存储基础配置"""
    enabled: Optional[bool] = Field(True, description="是否启用记忆存储")
    provider: MemoryProvider = Field(..., description="记忆存储提供商")
    ttl: Optional[int] = Field(3600, description="默认记忆过期时间(秒)", ge=60, le=2592000)
    max_size: Optional[str] = Field("100MB", description="最大存储大小限制")
    connection: Optional[MemoryConnectionConfig] = Field(None, description="存储连接配置")
    memory_types: Optional[MemoryTypes] = Field(None, description="不同类型记忆的配置")
    cleanup: Optional[CleanupConfig] = Field(None, description="记忆清理策略配置")

    @validator('max_size')
    def validate_max_size(cls, v):
        """验证存储大小格式"""
        import re
        if not re.match(r'^\d+[KMGT]?B$', v):
            raise ValueError("max_size must match pattern like '100MB', '1GB', etc.")
        return v

    class Config:
        extra = "forbid"


class MemoryFieldConfig(BaseModel):
    """记忆字段配置"""
    type: str = Field(..., description="数据类型")
    required: bool = Field(..., description="是否必需")
    default: Optional[Any] = Field(None, description="默认值")
    description: Optional[str] = Field(None, description="描述")
    validation: Optional[ValidationRule] = Field(None, description="验证规则")
    enum: Optional[list] = Field(None, description="枚举值")

    class Config:
        extra = "forbid"


class MemorySchema(BaseModel):
    """记忆存储配置模式"""
    base_config: Dict[str, MemoryFieldConfig] = Field(..., description="记忆存储基础配置")

    def __init__(self, **data):
        """初始化记忆存储配置模式"""
        if 'base_config' not in data:
            data['base_config'] = {
                'enabled': MemoryFieldConfig(
                    type="boolean",
                    required=False,
                    default=True,
                    description="是否启用记忆存储"
                ),
                'provider': MemoryFieldConfig(
                    type="string",
                    required=True,
                    description="记忆存储提供商",
                    enum=[provider.value for provider in MemoryProvider]
                ),
                'ttl': MemoryFieldConfig(
                    type="integer",
                    required=False,
                    default=3600,
                    description="默认记忆过期时间(秒)",
                    validation=ValidationRule(min=60, max=2592000)
                ),
                'max_size': MemoryFieldConfig(
                    type="string",
                    required=False,
                    default="100MB",
                    description="最大存储大小限制",
                    validation=ValidationRule(pattern=r'^\d+[KMGT]?B$')
                ),
                'connection': MemoryFieldConfig(
                    type="object",
                    required=False,
                    description="存储连接配置"
                ),
                'memory_types': MemoryFieldConfig(
                    type="object",
                    required=False,
                    description="不同类型记忆的配置"
                ),
                'cleanup': MemoryFieldConfig(
                    type="object",
                    required=False,
                    description="记忆清理策略配置"
                )
            }
        super().__init__(**data)

    class Config:
        extra = "forbid" 