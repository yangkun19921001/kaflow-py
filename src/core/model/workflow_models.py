"""
KaFlow-Py 工作流数据模型定义

基于协议标准定义的工作流配置模型，包括：
- NodeBaseStructure: 节点基础结构
- NodeSchema: 节点配置模式
- EdgeBaseStructure: 边基础结构
- EdgeSchema: 边配置模式
- IOSchema: 输入输出配置模式
- Position: 节点位置信息

Author: DevYK
WeChat: DevYK
Email: yang1001yk@gmail.com
Github: https://github.com/yangkun19921001
"""

from typing import Optional, List, Dict, Any, Union
from pydantic import BaseModel, Field, validator
from enum import Enum
from .base_models import ValidationRule


class NodeType(str, Enum):
    """节点类型枚举"""
    START = "start"
    END = "end"
    AGENT = "agent"
    CONDITION = "condition"
    TOOL = "tool"



class DataType(str, Enum):
    """数据类型枚举"""
    STRING = "string"
    NUMBER = "number"
    INTEGER = "integer"
    BOOLEAN = "boolean"
    OBJECT = "object"
    ARRAY = "array"
    FILE = "file"
    BINARY = "binary"


class Position(BaseModel):
    """节点位置信息"""
    x: float = Field(..., description="X坐标")
    y: float = Field(..., description="Y坐标")

    class Config:
        extra = "forbid"


class IOInputConfig(BaseModel):
    """输入配置"""
    name: str = Field(..., description="输入参数名称")
    thread_id: Optional[str] = Field(None, description="线程ID")
    type: DataType = Field(..., description="输入数据类型")
    required: bool = Field(..., description="是否为必需参数")
    source: Optional[str] = Field(None, description="数据来源: 节点名.输出名")
    default: Optional[Any] = Field(None, description="默认值")
    description: Optional[str] = Field(None, description="输入参数描述")
    validation: Optional[ValidationRule] = Field(None, description="输入验证规则")

    @validator('name')
    def validate_name(cls, v):
        """验证输入名称格式"""
        import re
        if not re.match(r'^[a-zA-Z][a-zA-Z0-9_]*$', v):
            raise ValueError("name must start with a letter and contain only letters, numbers, and underscores")
        return v

    @validator('thread_id')
    def validate_thread_id(cls, v):
        """验证线程ID格式"""
        if v is not None:
            import re
            if not re.match(r'^[a-zA-Z0-9]{32}$', v):
                raise ValueError("thread_id must be a 32-character alphanumeric string")
        return v

    @validator('source')
    def validate_source(cls, v):
        """验证数据来源格式"""
        if v is not None:
            import re
            if not re.match(r'^[a-zA-Z][a-zA-Z0-9_]*\.[a-zA-Z][a-zA-Z0-9_]*$', v):
                raise ValueError("source must be in format 'node_name.output_name'")
        return v

    @validator('description')
    def validate_description(cls, v):
        """验证描述长度"""
        if v is not None and len(v) > 200:
            raise ValueError("description must not exceed 200 characters")
        return v

    class Config:
        extra = "forbid"


class IOOutputConfig(BaseModel):
    """输出配置"""
    name: str = Field(..., description="输出参数名称")
    type: DataType = Field(..., description="输出数据类型")
    description: Optional[str] = Field(None, description="输出参数描述")

    @validator('name')
    def validate_name(cls, v):
        """验证输出名称格式"""
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


class IOFieldConfig(BaseModel):
    """IO字段配置"""
    type: str = Field(..., description="数据类型")
    required: bool = Field(..., description="是否必需")
    description: Optional[str] = Field(None, description="描述")
    validation: Optional[ValidationRule] = Field(None, description="验证规则")
    enum: Optional[List[str]] = Field(None, description="枚举值")

    class Config:
        extra = "forbid"


class IOSchema(BaseModel):
    """输入输出配置模式"""
    input_config: Dict[str, IOFieldConfig] = Field(..., description="输入配置")
    output_config: Dict[str, IOFieldConfig] = Field(..., description="输出配置")

    def __init__(self, **data):
        """初始化IO配置模式"""
        if 'input_config' not in data:
            data['input_config'] = {
                'name': IOFieldConfig(
                    type="string",
                    required=True,
                    description="输入参数名称",
                    validation=ValidationRule(pattern=r'^[a-zA-Z][a-zA-Z0-9_]*$')
                ),
                'thread_id': IOFieldConfig(
                    type="string",
                    required=False,
                    description="线程ID",
                    validation=ValidationRule(pattern=r'^[a-zA-Z0-9]{32}$')
                ),
                'type': IOFieldConfig(
                    type="string",
                    required=True,
                    description="输入数据类型",
                    enum=[data_type.value for data_type in DataType]
                ),
                'required': IOFieldConfig(
                    type="boolean",
                    required=True,
                    description="是否为必需参数"
                ),
                'source': IOFieldConfig(
                    type="string",
                    required=False,
                    description="数据来源: 节点名.输出名",
                    validation=ValidationRule(pattern=r'^[a-zA-Z][a-zA-Z0-9_]*\.[a-zA-Z][a-zA-Z0-9_]*$')
                ),
                'default': IOFieldConfig(
                    type="any",
                    required=False,
                    description="默认值"
                ),
                'description': IOFieldConfig(
                    type="string",
                    required=False,
                    description="输入参数描述",
                    validation=ValidationRule(max_length=200)
                ),
                'validation': IOFieldConfig(
                    type="object",
                    required=False,
                    description="输入验证规则"
                )
            }

        if 'output_config' not in data:
            data['output_config'] = {
                'name': IOFieldConfig(
                    type="string",
                    required=True,
                    description="输出参数名称",
                    validation=ValidationRule(pattern=r'^[a-zA-Z][a-zA-Z0-9_]*$')
                ),
                'type': IOFieldConfig(
                    type="string",
                    required=True,
                    description="输出数据类型",
                    enum=[data_type.value for data_type in DataType]
                ),
                'description': IOFieldConfig(
                    type="string",
                    required=False,
                    description="输出参数描述",
                    validation=ValidationRule(max_length=200)
                )
            }

        super().__init__(**data)

    class Config:
        extra = "forbid"


class NodeBaseStructure(BaseModel):
    """节点基础结构"""
    name: str = Field(..., description="节点唯一标识名称")
    type: NodeType = Field(..., description="节点类型")
    description: Optional[str] = Field(None, description="节点功能描述")
    agent_ref: Optional[str] = Field(None, description="引用agents配置段中的Agent名称")
    position: Optional[Position] = Field(None, description="节点在画布中的位置")
    inputs: Optional[List[IOInputConfig]] = Field(None, description="节点输入定义")
    outputs: Optional[List[IOOutputConfig]] = Field(None, description="节点输出定义")
    config: Optional[Dict[str, Any]] = Field(None, description="节点特定配置")

    @validator('name')
    def validate_name(cls, v):
        """验证节点名称格式"""
        import re
        if not re.match(r'^[a-zA-Z][a-zA-Z0-9_]*$', v):
            raise ValueError("name must start with a letter and contain only letters, numbers, and underscores")
        if len(v) < 3 or len(v) > 50:
            raise ValueError("name must be between 3 and 50 characters")
        return v

    @validator('description')
    def validate_description(cls, v):
        """验证描述长度"""
        if v is not None and len(v) > 200:
            raise ValueError("description must not exceed 200 characters")
        return v

    @validator('agent_ref')
    def validate_agent_ref(cls, v, values):
        """验证Agent引用格式"""
        if v is not None:
            import re
            if not re.match(r'^[a-zA-Z][a-zA-Z0-9_]*$', v):
                raise ValueError("agent_ref must start with a letter and contain only letters, numbers, and underscores")
            
            # 当节点类型为agent时，agent_ref必须提供
            if values.get('type') == NodeType.AGENT and v is None:
                raise ValueError("agent_ref is required when node type is 'agent'")
        return v

    class Config:
        extra = "forbid"


class EdgeBaseStructure(BaseModel):
    """边基础结构"""
    from_node: str = Field(..., alias="from", description="源节点名称")
    to_node: str = Field(..., alias="to", description="目标节点名称")
    condition: Optional[str] = Field(None, description="边的执行条件表达式")
    description: Optional[str] = Field(None, description="边的功能描述")
    weight: Optional[float] = Field(1.0, description="边的权重或优先级", ge=0.0, le=10.0)

    @validator('from_node', 'to_node')
    def validate_node_names(cls, v):
        """验证节点名称格式"""
        import re
        if not re.match(r'^[a-zA-Z][a-zA-Z0-9_]*$', v):
            raise ValueError("node name must start with a letter and contain only letters, numbers, and underscores")
        return v

    @validator('description')
    def validate_description(cls, v):
        """验证描述长度"""
        if v is not None and len(v) > 100:
            raise ValueError("description must not exceed 100 characters")
        return v

    class Config:
        extra = "forbid"
        allow_population_by_field_name = True


class NodeFieldConfig(BaseModel):
    """节点字段配置"""
    type: str = Field(..., description="数据类型")
    required: bool = Field(..., description="是否必需")
    default: Optional[Any] = Field(None, description="默认值")
    description: Optional[str] = Field(None, description="描述")
    validation: Optional[ValidationRule] = Field(None, description="验证规则")
    schema: Optional[str] = Field(None, description="引用的配置模式")
    enum: Optional[List[str]] = Field(None, description="枚举值")

    class Config:
        extra = "forbid"


class EdgeFieldConfig(BaseModel):
    """边字段配置"""
    type: str = Field(..., description="数据类型")
    required: bool = Field(..., description="是否必需")
    default: Optional[Any] = Field(None, description="默认值")
    description: Optional[str] = Field(None, description="描述")
    validation: Optional[ValidationRule] = Field(None, description="验证规则")

    class Config:
        extra = "forbid"


class NodeSchema(BaseModel):
    """节点配置模式"""
    base_structure: Dict[str, NodeFieldConfig] = Field(..., description="节点基础结构")

    def __init__(self, **data):
        """初始化节点配置模式"""
        if 'base_structure' not in data:
            data['base_structure'] = {
                'name': NodeFieldConfig(
                    type="string",
                    required=True,
                    description="节点唯一标识名称",
                    validation=ValidationRule(
                        pattern=r'^[a-zA-Z][a-zA-Z0-9_]*$',
                        min_length=3,
                        max_length=50
                    )
                ),
                'type': NodeFieldConfig(
                    type="string",
                    required=True,
                    description="节点类型",
                    enum=[node_type.value for node_type in NodeType]
                ),
                'description': NodeFieldConfig(
                    type="string",
                    required=False,
                    description="节点功能描述",
                    validation=ValidationRule(max_length=200)
                ),
                'agent_ref': NodeFieldConfig(
                    type="string",
                    required=False,
                    description="引用agents配置段中的Agent名称",
                    validation=ValidationRule(pattern=r'^[a-zA-Z][a-zA-Z0-9_]*$')
                ),
                'position': NodeFieldConfig(
                    type="object",
                    required=False,
                    description="节点在画布中的位置"
                ),
                'inputs': NodeFieldConfig(
                    type="array",
                    required=False,
                    description="节点输入定义",
                    schema="io_schema.input_config"
                ),
                'outputs': NodeFieldConfig(
                    type="array",
                    required=False,
                    description="节点输出定义",
                    schema="io_schema.output_config"
                ),
                'config': NodeFieldConfig(
                    type="object",
                    required=False,
                    description="节点特定配置"
                )
            }
        super().__init__(**data)

    class Config:
        extra = "forbid"


class EdgeSchema(BaseModel):
    """边配置模式"""
    base_structure: Dict[str, EdgeFieldConfig] = Field(..., description="边基础结构")

    def __init__(self, **data):
        """初始化边配置模式"""
        if 'base_structure' not in data:
            data['base_structure'] = {
                'from': EdgeFieldConfig(
                    type="string",
                    required=True,
                    description="源节点名称",
                    validation=ValidationRule(pattern=r'^[a-zA-Z][a-zA-Z0-9_]*$')
                ),
                'to': EdgeFieldConfig(
                    type="string",
                    required=True,
                    description="目标节点名称",
                    validation=ValidationRule(pattern=r'^[a-zA-Z][a-zA-Z0-9_]*$')
                ),
                'condition': EdgeFieldConfig(
                    type="string",
                    required=False,
                    description="边的执行条件表达式"
                ),
                'description': EdgeFieldConfig(
                    type="string",
                    required=False,
                    description="边的功能描述",
                    validation=ValidationRule(max_length=100)
                ),
                'weight': EdgeFieldConfig(
                    type="number",
                    required=False,
                    default=1.0,
                    description="边的权重或优先级",
                    validation=ValidationRule(min=0.0, max=10.0)
                )
            }
        super().__init__(**data)

    class Config:
        extra = "forbid" 