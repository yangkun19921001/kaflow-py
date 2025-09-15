"""
KaFlow-Py 循环数据模型定义

基于协议标准定义的循环配置模型，包括：
- LoopBaseConfig: 循环基础配置
- LoopSchema: 循环配置模式
- LoopType: 循环类型枚举

Author: DevYK
WeChat: DevYK
Email: yang1001yk@gmail.com
Github: https://github.com/yangkun19921001
"""

from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field, validator
from enum import Enum
from .base_models import ValidationRule


class LoopType(str, Enum):
    """循环类型枚举"""
    WHILE = "while"      # while循环
    FOR = "for"          # for循环
    FOREACH = "foreach"  # foreach循环
    UNTIL = "until"      # until循环


class LoopBaseConfig(BaseModel):
    """循环基础配置"""
    type: LoopType = Field(..., description="循环类型")
    condition: Optional[str] = Field(None, description="循环条件表达式")
    max_iterations: Optional[int] = Field(100, description="最大迭代次数", ge=1, le=10000)
    timeout: Optional[int] = Field(300, description="循环超时时间(秒)", ge=1, le=3600)
    body: List[Dict[str, Any]] = Field(..., description="循环体节点列表")
    init: Optional[List[Dict[str, Any]]] = Field(None, description="循环初始化变量")
    update: Optional[List[Dict[str, Any]]] = Field(None, description="循环变量更新操作")

    @validator('body')
    def validate_body(cls, v):
        """验证循环体不为空"""
        if not v or len(v) == 0:
            raise ValueError("loop body cannot be empty")
        return v

    class Config:
        extra = "forbid"


class LoopFieldConfig(BaseModel):
    """循环字段配置"""
    type: str = Field(..., description="数据类型")
    required: bool = Field(..., description="是否必需")
    default: Optional[Any] = Field(None, description="默认值")
    description: Optional[str] = Field(None, description="描述")
    validation: Optional[ValidationRule] = Field(None, description="验证规则")
    enum: Optional[list] = Field(None, description="枚举值")
    schema: Optional[str] = Field(None, description="引用的配置模式")

    class Config:
        extra = "forbid"


class LoopSchema(BaseModel):
    """循环配置模式"""
    base_config: Dict[str, LoopFieldConfig] = Field(..., description="循环基础配置")

    def __init__(self, **data):
        """初始化循环配置模式"""
        if 'base_config' not in data:
            data['base_config'] = {
                'type': LoopFieldConfig(
                    type="string",
                    required=True,
                    description="循环类型",
                    enum=[loop_type.value for loop_type in LoopType]
                ),
                'condition': LoopFieldConfig(
                    type="string",
                    required=False,
                    description="循环条件表达式"
                ),
                'max_iterations': LoopFieldConfig(
                    type="integer",
                    required=False,
                    default=100,
                    description="最大迭代次数",
                    validation=ValidationRule(min=1, max=10000)
                ),
                'timeout': LoopFieldConfig(
                    type="integer",
                    required=False,
                    default=300,
                    description="循环超时时间(秒)",
                    validation=ValidationRule(min=1, max=3600)
                ),
                'body': LoopFieldConfig(
                    type="array",
                    required=True,
                    description="循环体节点列表",
                    schema="node_schema.base_structure"
                ),
                'init': LoopFieldConfig(
                    type="array",
                    required=False,
                    description="循环初始化变量"
                ),
                'update': LoopFieldConfig(
                    type="array",
                    required=False,
                    description="循环变量更新操作"
                )
            }
        super().__init__(**data)

    class Config:
        extra = "forbid" 