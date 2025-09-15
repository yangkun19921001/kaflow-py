"""
KaFlow-Py 工具数据模型定义

基于协议标准定义的工具配置模型，包括：
- ToolConfig: 工具配置
- ToolSchema: 工具配置模式
- ToolType: 工具类型枚举

Author: DevYK
WeChat: DevYK
Email: yang1001yk@gmail.com
Github: https://github.com/yangkun19921001
"""

from typing import Optional, Dict, Any
from pydantic import BaseModel, Field, validator
from enum import Enum
from .base_models import ValidationRule


class ToolType(str, Enum):
    """工具类型枚举"""
    BUILTIN = "builtin"  # 内置工具
    CUSTOM = "custom"    # 自定义工具
    API = "api"          # API工具
    FUNCTION = "function"  # 函数工具


class ToolConfig(BaseModel):
    """工具配置"""
    name: str = Field(..., description="工具名称")
    description: Optional[str] = Field(None, description="工具功能描述")
    type: Optional[ToolType] = Field(None, description="工具类型")
    config: Optional[Dict[str, Any]] = Field(None, description="工具特定配置")
    timeout: Optional[int] = Field(60, description="工具执行超时时间(秒)", ge=1, le=300)

    @validator('name')
    def validate_name(cls, v):
        """验证工具名称格式"""
        import re
        if not re.match(r'^[a-zA-Z][a-zA-Z0-9_]*$', v):
            raise ValueError("name must start with a letter and contain only letters, numbers, and underscores")
        return v

    @validator('description')
    def validate_description(cls, v):
        """验证描述长度"""
        if v is not None and len(v) > 200:
            raise ValueError("description must not exceed 200 characters")
        return v

    class Config:
        extra = "forbid"


class ToolFieldConfig(BaseModel):
    """工具字段配置"""
    type: str = Field(..., description="数据类型")
    required: bool = Field(..., description="是否必需")
    default: Optional[Any] = Field(None, description="默认值")
    description: Optional[str] = Field(None, description="描述")
    validation: Optional[ValidationRule] = Field(None, description="验证规则")
    enum: Optional[list] = Field(None, description="枚举值")

    class Config:
        extra = "forbid"


class ToolSchema(BaseModel):
    """工具配置模式"""
    tool_config: Dict[str, ToolFieldConfig] = Field(..., description="工具配置")

    def __init__(self, **data):
        """初始化工具配置模式"""
        if 'tool_config' not in data:
            data['tool_config'] = {
                'name': ToolFieldConfig(
                    type="string",
                    required=True,
                    description="工具名称",
                    validation=ValidationRule(pattern=r'^[a-zA-Z][a-zA-Z0-9_]*$')
                ),
                'description': ToolFieldConfig(
                    type="string",
                    required=False,
                    description="工具功能描述",
                    validation=ValidationRule(max_length=200)
                ),
                'type': ToolFieldConfig(
                    type="string",
                    required=False,
                    description="工具类型",
                    enum=[tool_type.value for tool_type in ToolType]
                ),
                'config': ToolFieldConfig(
                    type="object",
                    required=False,
                    description="工具特定配置"
                ),
                'timeout': ToolFieldConfig(
                    type="integer",
                    required=False,
                    default=60,
                    description="工具执行超时时间(秒)",
                    validation=ValidationRule(min=1, max=300)
                )
            }
        super().__init__(**data)

    class Config:
        extra = "forbid" 