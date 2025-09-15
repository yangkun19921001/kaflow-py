"""
KaFlow-Py 工作流模式数据模型定义

基于协议标准定义的工作流模式配置模型，包括：
- WorkflowBaseConfig: 工作流基础配置
- WorkflowSettings: 工作流设置
- WorkflowSchemaModel: 工作流模式模型

Author: DevYK
WeChat: DevYK
Email: yang1001yk@gmail.com
Github: https://github.com/yangkun19921001
"""

from typing import Optional, Dict, Any
from pydantic import BaseModel, Field, validator
from .base_models import RuntimeConfig


class WorkflowSettings(BaseModel):
    """工作流级别设置"""
    timeout: Optional[int] = Field(300, description="工作流超时时间(秒)", ge=1)
    max_retries: Optional[int] = Field(3, description="最大重试次数", ge=0)
    parallel_limit: Optional[int] = Field(5, description="并发限制", ge=1)
    debug_mode: Optional[bool] = Field(False, description="调试模式")
    trace_enabled: Optional[bool] = Field(True, description="链路追踪")
    checkpoint_enabled: Optional[bool] = Field(True, description="检查点保存")

    class Config:
        extra = "forbid"


class WorkflowBaseConfig(BaseModel):
    """工作流基础配置"""
    name: str = Field(..., description="工作流名称")
    version: str = Field(..., description="工作流版本")
    description: Optional[str] = Field(None, description="工作流功能描述")
    author: Optional[str] = Field(None, description="工作流作者")
    schema_version: str = Field(..., description="配置模式版本")
    settings: Optional[WorkflowSettings] = Field(None, description="工作流级别设置")

    @validator('name')
    def validate_name(cls, v):
        """验证工作流名称格式"""
        import re
        if not re.match(r'^[a-zA-Z][a-zA-Z0-9_\-\s]*$', v):
            raise ValueError("name must start with a letter and contain only letters, numbers, underscores, hyphens, and spaces")
        if len(v) < 3 or len(v) > 100:
            raise ValueError("name must be between 3 and 100 characters")
        return v

    @validator('version')
    def validate_version(cls, v):
        """验证版本格式"""
        import re
        if not re.match(r'^\d+\.\d+\.\d+$', v):
            raise ValueError("version must be in format 'x.y.z' (semantic versioning)")
        return v

    @validator('description')
    def validate_description(cls, v):
        """验证描述长度"""
        if v is not None and len(v) > 1000:
            raise ValueError("description must not exceed 1000 characters")
        return v

    class Config:
        extra = "forbid"


class WorkflowFieldConfig(BaseModel):
    """工作流字段配置"""
    type: str = Field(..., description="数据类型")
    required: bool = Field(..., description="是否必需")
    default: Optional[Any] = Field(None, description="默认值")
    description: Optional[str] = Field(None, description="描述")
    validation: Optional[Dict[str, Any]] = Field(None, description="验证规则")
    schema: Optional[str] = Field(None, description="引用的配置模式")

    class Config:
        extra = "forbid"


class WorkflowSchemaModel(BaseModel):
    """工作流模式模型"""
    base_config: Dict[str, WorkflowFieldConfig] = Field(..., description="工作流基础配置")

    def __init__(self, **data):
        """初始化工作流模式配置"""
        if 'base_config' not in data:
            data['base_config'] = {
                'name': WorkflowFieldConfig(
                    type="string",
                    required=True,
                    description="工作流名称",
                    validation={
                        'pattern': r'^[a-zA-Z][a-zA-Z0-9_\-\s]*$',
                        'min_length': 3,
                        'max_length': 100
                    }
                ),
                'version': WorkflowFieldConfig(
                    type="string",
                    required=True,
                    description="工作流版本",
                    validation={
                        'pattern': r'^\d+\.\d+\.\d+$'
                    }
                ),
                'description': WorkflowFieldConfig(
                    type="string",
                    required=False,
                    description="工作流功能描述",
                    validation={
                        'max_length': 1000
                    }
                ),
                'author': WorkflowFieldConfig(
                    type="string",
                    required=False,
                    description="工作流作者"
                ),
                'schema_version': WorkflowFieldConfig(
                    type="string",
                    required=True,
                    description="配置模式版本"
                ),
                'settings': WorkflowFieldConfig(
                    type="object",
                    required=False,
                    description="工作流级别设置",
                    schema="global_config.runtime"
                )
            }
        super().__init__(**data)

    class Config:
        extra = "forbid" 