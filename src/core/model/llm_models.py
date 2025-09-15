"""
KaFlow-Py LLM 数据模型定义

基于协议标准定义的LLM配置模型，包括：
- LLMBaseConfig: LLM基础配置
- LLMSchema: LLM配置模式
- ModelEnum: 支持的模型枚举

Author: DevYK
WeChat: DevYK
Email: yang1001yk@gmail.com
Github: https://github.com/yangkun19921001
"""

from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field, validator
from enum import Enum
from .base_models import ValidationRule


class LLMModel(str, Enum):
    """支持的LLM模型枚举"""
    GPT_4O = "gpt-4o"
    GPT_4O_MINI = "gpt-4o-mini"
    GPT_3_5_TURBO = "gpt-3.5-turbo"
    CLAUDE_3_SONNET = "claude-3-sonnet"
    CLAUDE_3_HAIKU = "claude-3-haiku"


class LLMFieldConfig(BaseModel):
    """LLM字段配置基础模型"""
    type: str = Field(..., description="数据类型")
    required: bool = Field(..., description="是否必需")
    default: Optional[Any] = Field(None, description="默认值")
    description: Optional[str] = Field(None, description="描述")
    validation: Optional[ValidationRule] = Field(None, description="验证规则")
    sensitive: Optional[bool] = Field(None, description="敏感信息标记")
    enum: Optional[List[str]] = Field(None, description="枚举值")

    class Config:
        extra = "forbid"


class LLMBaseConfig(BaseModel):
    """LLM基础配置"""
    base_url: Optional[str] = Field(
        "https://api.openai.com/v1", 
        description="API基础URL"
    )
    api_key: str = Field(..., description="API密钥")
    model: LLMModel = Field(LLMModel.GPT_4O_MINI, description="LLM模型名称")
    temperature: Optional[float] = Field(
        0.7, 
        description="生成随机性控制", 
        ge=0.0, 
        le=2.0
    )
    max_tokens: Optional[int] = Field(
        1024, 
        description="最大生成token数", 
        ge=1, 
        le=32768
    )
    timeout: Optional[int] = Field(
        30, 
        description="请求超时时间(秒)", 
        ge=1, 
        le=300
    )

    @validator('api_key')
    def validate_api_key(cls, v):
        """验证API密钥长度"""
        if len(v) < 10:
            raise ValueError("api_key must be at least 10 characters long")
        return v

    class Config:
        extra = "forbid"


class LLMSchema(BaseModel):
    """LLM配置模式"""
    base_config: Dict[str, LLMFieldConfig] = Field(
        ..., 
        description="基础配置结构"
    )

    def __init__(self, **data):
        """初始化LLM配置模式"""
        if 'base_config' not in data:
            # 提供默认的基础配置结构
            data['base_config'] = {
                'base_url': LLMFieldConfig(
                    type="string",
                    required=False,
                    default="https://api.openai.com/v1",
                    description="LLM API基础URL"
                ),
                'api_key': LLMFieldConfig(
                    type="string",
                    required=True,
                    sensitive=True,
                    description="LLM API密钥",
                    validation=ValidationRule(min_length=10)
                ),
                'model': LLMFieldConfig(
                    type="string",
                    required=True,
                    default="gpt-4o-mini",
                    description="LLM模型名称",
                    enum=[model.value for model in LLMModel]
                ),
                'temperature': LLMFieldConfig(
                    type="number",
                    required=False,
                    default=0.7,
                    description="生成随机性控制",
                    validation=ValidationRule(min=0.0, max=2.0)
                ),
                'max_tokens': LLMFieldConfig(
                    type="integer",
                    required=False,
                    default=1024,
                    description="最大生成token数",
                    validation=ValidationRule(min=1, max=32768)
                ),
                'timeout': LLMFieldConfig(
                    type="integer",
                    required=False,
                    default=30,
                    description="请求超时时间(秒)",
                    validation=ValidationRule(min=1, max=300)
                )
            }
        super().__init__(**data)

    class Config:
        extra = "forbid"


class LLMConfigValidator:
    """LLM配置验证器"""
    
    @staticmethod
    def validate_config(config: Dict[str, Any], schema: LLMSchema) -> bool:
        """验证LLM配置是否符合模式定义"""
        for field_name, field_config in schema.base_config.items():
            if field_config.required and field_name not in config:
                raise ValueError(f"Required field '{field_name}' is missing")
            
            if field_name in config:
                value = config[field_name]
                
                # 类型验证
                if not LLMConfigValidator._validate_type(value, field_config.type):
                    raise ValueError(f"Field '{field_name}' has invalid type")
                
                # 枚举值验证
                if field_config.enum and value not in field_config.enum:
                    raise ValueError(f"Field '{field_name}' value must be one of {field_config.enum}")
                
                # 验证规则检查
                if field_config.validation:
                    LLMConfigValidator._validate_rules(value, field_config.validation, field_name)
        
        return True
    
    @staticmethod
    def _validate_type(value: Any, expected_type: str) -> bool:
        """验证值的类型"""
        type_mapping = {
            "string": str,
            "integer": int,
            "number": (int, float),
            "boolean": bool,
            "object": dict,
            "array": list
        }
        
        expected_python_type = type_mapping.get(expected_type)
        if expected_python_type is None:
            return True  # 未知类型跳过验证
        
        return isinstance(value, expected_python_type)
    
    @staticmethod
    def _validate_rules(value: Any, rules: ValidationRule, field_name: str):
        """验证规则检查"""
        if isinstance(value, str):
            if rules.min_length is not None and len(value) < rules.min_length:
                raise ValueError(f"Field '{field_name}' is too short")
            if rules.max_length is not None and len(value) > rules.max_length:
                raise ValueError(f"Field '{field_name}' is too long")
        
        if isinstance(value, (int, float)):
            if rules.min is not None and value < rules.min:
                raise ValueError(f"Field '{field_name}' is below minimum value")
            if rules.max is not None and value > rules.max:
                raise ValueError(f"Field '{field_name}' is above maximum value")
        
        if rules.pattern is not None:
            import re
            if isinstance(value, str) and not re.match(rules.pattern, value):
                raise ValueError(f"Field '{field_name}' does not match required pattern") 