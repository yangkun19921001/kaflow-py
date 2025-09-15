"""
KaFlow-Py 基础数据模型定义

基于协议标准定义的基础配置模型，包括：
- Protocol: 协议版本与元信息
- GlobalConfig: 全局配置标准
- RuntimeConfig: 运行时配置
- LoggingConfig: 日志配置
- MemoryConnectionConfig: 记忆连接配置

Author: DevYK
WeChat: DevYK
Email: yang1001yk@gmail.com
Github: https://github.com/yangkun19921001
"""

from typing import Optional, Dict, Any, Union
from pydantic import BaseModel, Field, validator
from enum import Enum


class Protocol(BaseModel):
    """协议版本与元信息"""
    name: str = Field(..., description="协议名称")
    version: str = Field(..., description="协议版本")
    schema_version: str = Field(..., description="模式版本")
    description: Optional[str] = Field(None, description="协议描述")
    author: Optional[str] = Field(None, description="作者")
    license: Optional[str] = Field(None, description="许可证")

    class Config:
        extra = "forbid"


class RuntimeConfig(BaseModel):
    """运行时配置"""
    timeout: Optional[int] = Field(300, description="全局超时时间(秒)", ge=1)
    max_retries: Optional[int] = Field(3, description="最大重试次数", ge=0)
    parallel_limit: Optional[int] = Field(5, description="并发限制", ge=1)
    debug_mode: Optional[bool] = Field(False, description="调试模式")
    trace_enabled: Optional[bool] = Field(True, description="链路追踪")
    checkpoint_enabled: Optional[bool] = Field(True, description="检查点保存")

    class Config:
        extra = "forbid"


class LogLevel(str, Enum):
    """日志级别枚举"""
    DEBUG = "DEBUG"
    INFO = "INFO"
    WARN = "WARN"
    ERROR = "ERROR"


class LogFormat(str, Enum):
    """日志格式枚举"""
    JSON = "json"
    TEXT = "text"


class LogOutput(str, Enum):
    """日志输出目标枚举"""
    STDOUT = "stdout"
    FILE = "file"


class LoggingConfig(BaseModel):
    """日志配置"""
    level: Optional[LogLevel] = Field(LogLevel.INFO, description="日志级别")
    format: Optional[LogFormat] = Field(LogFormat.JSON, description="日志格式")
    output: Optional[LogOutput] = Field(LogOutput.STDOUT, description="输出目标")
    file_path: Optional[str] = Field("./logs/kaflow.log", description="日志文件路径")
    max_size: Optional[str] = Field("100MB", description="最大文件大小")
    max_files: Optional[int] = Field(10, description="最大文件数量", ge=1)

    @validator('max_size')
    def validate_max_size(cls, v):
        """验证文件大小格式"""
        if not v.endswith(('B', 'KB', 'MB', 'GB', 'TB')):
            raise ValueError("max_size must end with B, KB, MB, GB, or TB")
        return v

    class Config:
        extra = "forbid"


class MemoryProvider(str, Enum):
    """记忆存储提供商枚举"""
    MEMORY = "memory"
    REDIS = "redis"
    POSTGRESQL = "postgresql"
    MONGODB = "mongodb"
    SQLITE = "sqlite"


class MemoryConnectionConfig(BaseModel):
    """记忆存储连接配置"""
    host: Optional[str] = Field("localhost", description="主机地址")
    port: Optional[int] = Field(6379, description="端口号", ge=1, le=65535)
    database: Optional[Union[int, str]] = Field(0, description="数据库编号")
    username: Optional[str] = Field("", description="用户名")
    password: Optional[str] = Field("", description="密码")
    pool_size: Optional[int] = Field(10, description="连接池大小", ge=1, le=100)

    class Config:
        extra = "forbid"


class MemoryConfig(BaseModel):
    """记忆存储配置"""
    enabled: Optional[bool] = Field(True, description="启用记忆存储")
    provider: Optional[MemoryProvider] = Field(MemoryProvider.SQLITE, description="存储提供商")
    ttl: Optional[int] = Field(3600, description="默认过期时间(秒)", ge=60)
    max_size: Optional[str] = Field("100MB", description="最大存储大小")
    connection: Optional[MemoryConnectionConfig] = Field(None, description="连接配置")

    @validator('max_size')
    def validate_max_size(cls, v):
        """验证存储大小格式"""
        if not v.endswith(('B', 'KB', 'MB', 'GB', 'TB')):
            raise ValueError("max_size must end with B, KB, MB, GB, or TB")
        return v

    class Config:
        extra = "forbid"


class GlobalConfig(BaseModel):
    """全局配置标准"""
    runtime: Optional[RuntimeConfig] = Field(None, description="运行时设置")
    logging: Optional[LoggingConfig] = Field(None, description="日志配置")
    memory: Optional[MemoryConfig] = Field(None, description="记忆存储配置")

    class Config:
        extra = "forbid"


class ValidationRule(BaseModel):
    """验证规则基础模型"""
    min_length: Optional[int] = Field(None, description="最小长度", ge=0)
    max_length: Optional[int] = Field(None, description="最大长度", ge=0)
    min: Optional[Union[int, float]] = Field(None, description="最小值")
    max: Optional[Union[int, float]] = Field(None, description="最大值")
    pattern: Optional[str] = Field(None, description="正则表达式模式")

    @validator('max_length')
    def validate_max_length(cls, v, values):
        """验证最大长度不小于最小长度"""
        if v is not None and values.get('min_length') is not None:
            if v < values['min_length']:
                raise ValueError("max_length must be greater than or equal to min_length")
        return v

    @validator('max')
    def validate_max_value(cls, v, values):
        """验证最大值不小于最小值"""
        if v is not None and values.get('min') is not None:
            if v < values['min']:
                raise ValueError("max must be greater than or equal to min")
        return v

    class Config:
        extra = "forbid" 