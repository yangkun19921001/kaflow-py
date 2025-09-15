"""
KaFlow-Py Agent 数据模型定义

基于协议标准定义的Agent配置模型，包括：
- AgentBaseStructure: Agent基础结构
- AgentSchema: Agent配置模式
- MCPServerConfig: MCP服务器配置
- MCPSchema: MCP配置模式

Author: DevYK
WeChat: DevYK
Email: yang1001yk@gmail.com
Github: https://github.com/yangkun19921001
"""

from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field, validator
from enum import Enum
from .base_models import ValidationRule
from .llm_models import LLMBaseConfig


class AgentType(str, Enum):
    """Agent类型枚举"""
    AGENT = "agent"
    REACT_AGENT = "react_agent"


class MCPProtocol(str, Enum):
    """MCP通信协议枚举"""
    SSE = "sse"
    STDIO = "stdio"
    WEBSOCKET = "websocket"


class MCPServerConfig(BaseModel):
    """MCP服务器配置"""
    name: str = Field(..., description="MCP服务器名称")
    url: str = Field(..., description="MCP服务器地址")
    protocol: Optional[MCPProtocol] = Field(MCPProtocol.SSE, description="通信协议类型")
    timeout: Optional[int] = Field(30, description="连接超时时间(秒)", ge=1, le=120)
    retry_count: Optional[int] = Field(3, description="连接重试次数", ge=0, le=10)

    @validator('name')
    def validate_name(cls, v):
        """验证服务器名称格式"""
        import re
        if not re.match(r'^[a-zA-Z][a-zA-Z0-9_]*$', v):
            raise ValueError("name must start with a letter and contain only letters, numbers, and underscores")
        return v

    @validator('url')
    def validate_url(cls, v):
        """验证URL格式"""
        import re
        if not re.match(r'^https?://.*$', v):
            raise ValueError("url must be a valid HTTP or HTTPS URL")
        return v

    class Config:
        extra = "forbid"


class MCPFieldConfig(BaseModel):
    """MCP字段配置"""
    type: str = Field(..., description="数据类型")
    required: bool = Field(..., description="是否必需")
    default: Optional[Any] = Field(None, description="默认值")
    description: Optional[str] = Field(None, description="描述")
    validation: Optional[ValidationRule] = Field(None, description="验证规则")
    enum: Optional[List[str]] = Field(None, description="枚举值")

    class Config:
        extra = "forbid"


class MCPSchema(BaseModel):
    """MCP配置模式"""
    server_config: Dict[str, MCPFieldConfig] = Field(..., description="MCP服务器配置")

    def __init__(self, **data):
        """初始化MCP配置模式"""
        if 'server_config' not in data:
            # 提供默认的服务器配置结构
            data['server_config'] = {
                'name': MCPFieldConfig(
                    type="string",
                    required=True,
                    description="MCP服务器名称",
                    validation=ValidationRule(pattern=r'^[a-zA-Z][a-zA-Z0-9_]*$')
                ),
                'url': MCPFieldConfig(
                    type="string",
                    required=True,
                    description="MCP服务器地址",
                    validation=ValidationRule(pattern=r'^https?://.*$')
                ),
                'protocol': MCPFieldConfig(
                    type="string",
                    required=False,
                    default="sse",
                    description="通信协议类型",
                    enum=[protocol.value for protocol in MCPProtocol]
                ),
                'timeout': MCPFieldConfig(
                    type="integer",
                    required=False,
                    default=30,
                    description="连接超时时间(秒)",
                    validation=ValidationRule(min=1, max=120)
                ),
                'retry_count': MCPFieldConfig(
                    type="integer",
                    required=False,
                    default=3,
                    description="连接重试次数",
                    validation=ValidationRule(min=0, max=10)
                )
            }
        super().__init__(**data)

    class Config:
        extra = "forbid"


class ToolConfig(BaseModel):
    """工具配置基础模型"""
    name: str = Field(..., description="工具名称")
    description: Optional[str] = Field(None, description="工具功能描述")
    type: Optional[str] = Field(None, description="工具类型")
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


class AgentBaseStructure(BaseModel):
    """Agent基础结构"""
    name: str = Field(..., description="Agent唯一标识名称")
    type: AgentType = Field(..., description="Agent类型")
    description: Optional[str] = Field(None, description="Agent功能描述")
    enabled: Optional[bool] = Field(True, description="是否启用此Agent")
    system_prompt: str = Field(..., description="Agent系统提示词")
    llm: LLMBaseConfig = Field(..., description="Agent使用的LLM配置")
    mcp_servers: Optional[List[MCPServerConfig]] = Field(None, description="MCP服务器列表")
    tools: Optional[List[ToolConfig]] = Field(None, description="Agent可用工具列表")

    @validator('name')
    def validate_name(cls, v):
        """验证Agent名称格式"""
        import re
        if not re.match(r'^[a-zA-Z][a-zA-Z0-9_]*$', v):
            raise ValueError("name must start with a letter and contain only letters, numbers, and underscores")
        if len(v) < 3 or len(v) > 50:
            raise ValueError("name must be between 3 and 50 characters")
        return v

    @validator('description')
    def validate_description(cls, v):
        """验证描述长度"""
        if v is not None and len(v) > 500:
            raise ValueError("description must not exceed 500 characters")
        return v

    @validator('system_prompt')
    def validate_system_prompt(cls, v):
        """验证系统提示词长度"""
        if len(v) < 10:
            raise ValueError("system_prompt must be at least 10 characters long")
        if len(v) > 8192:
            raise ValueError("system_prompt must not exceed 8192 characters")
        return v

    class Config:
        extra = "forbid"


class AgentFieldConfig(BaseModel):
    """Agent字段配置"""
    type: str = Field(..., description="数据类型")
    required: bool = Field(..., description="是否必需")
    default: Optional[Any] = Field(None, description="默认值")
    description: Optional[str] = Field(None, description="描述")
    validation: Optional[ValidationRule] = Field(None, description="验证规则")
    schema: Optional[str] = Field(None, description="引用的配置模式")
    enum: Optional[List[str]] = Field(None, description="枚举值")

    class Config:
        extra = "forbid"


class AgentSchema(BaseModel):
    """Agent配置模式"""
    base_structure: Dict[str, AgentFieldConfig] = Field(..., description="Agent基础结构")

    def __init__(self, **data):
        """初始化Agent配置模式"""
        if 'base_structure' not in data:
            # 提供默认的基础结构
            data['base_structure'] = {
                'name': AgentFieldConfig(
                    type="string",
                    required=True,
                    description="Agent唯一标识名称",
                    validation=ValidationRule(
                        pattern=r'^[a-zA-Z][a-zA-Z0-9_]*$',
                        min_length=3,
                        max_length=50
                    )
                ),
                'type': AgentFieldConfig(
                    type="string",
                    required=True,
                    description="Agent类型",
                    enum=[agent_type.value for agent_type in AgentType]
                ),
                'description': AgentFieldConfig(
                    type="string",
                    required=False,
                    description="Agent功能描述",
                    validation=ValidationRule(max_length=500)
                ),
                'enabled': AgentFieldConfig(
                    type="boolean",
                    required=False,
                    default=True,
                    description="是否启用此Agent"
                ),
                'system_prompt': AgentFieldConfig(
                    type="string",
                    required=True,
                    description="Agent系统提示词",
                    validation=ValidationRule(min_length=10, max_length=8192)
                ),
                'llm': AgentFieldConfig(
                    type="object",
                    required=True,
                    description="Agent使用的LLM配置",
                    schema="llm_schema.base_config"
                ),
                'mcp_servers': AgentFieldConfig(
                    type="array",
                    required=False,
                    description="MCP服务器列表",
                    schema="mcp_schema.server_config"
                ),
                'tools': AgentFieldConfig(
                    type="array",
                    required=False,
                    description="Agent可用工具列表",
                    schema="tool_schema.tool_config"
                )
            }
        super().__init__(**data)

    class Config:
        extra = "forbid"


class AgentConfigValidator:
    """Agent配置验证器"""
    
    @staticmethod
    def validate_config(config: Dict[str, Any], schema: AgentSchema) -> bool:
        """验证Agent配置是否符合模式定义"""
        for field_name, field_config in schema.base_structure.items():
            if field_config.required and field_name not in config:
                raise ValueError(f"Required field '{field_name}' is missing")
            
            if field_name in config:
                value = config[field_name]
                
                # 类型验证
                if not AgentConfigValidator._validate_type(value, field_config.type):
                    raise ValueError(f"Field '{field_name}' has invalid type")
                
                # 枚举值验证
                if field_config.enum and value not in field_config.enum:
                    raise ValueError(f"Field '{field_name}' value must be one of {field_config.enum}")
                
                # 验证规则检查
                if field_config.validation:
                    AgentConfigValidator._validate_rules(value, field_config.validation, field_name)
        
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