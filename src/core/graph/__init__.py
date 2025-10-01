"""
KaFlow-Py 图管理模块

基于 LangGraph API 的自动图构建系统，支持从协议模板自动生成工作流图。

Author: DevYK
WeChat: DevYK
Email: yang1001yk@gmail.com
Github: https://github.com/yangkun19921001
"""

# 导入协议解析器
from .parser import (
    ProtocolInfo,
    GlobalConfig,
    AgentInfo,
    WorkflowNode,
    WorkflowEdge,
    WorkflowInfo,
    ParsedProtocol,
    ProtocolParser
)

# 导入节点工厂
from .factory import (
    GraphState,
    NodeFunction,
    BaseNodeBuilder,
    StartNodeBuilder,
    EndNodeBuilder,
    AgentNodeBuilder,
    NodeFactory
)

# 导入输入输出解析器
from .io_resolver import (
    InputField,
    OutputField,
    InputOutputResolver,
    get_io_resolver
)

# 导入自动构建器
from .builder import (
    LangGraphAutoBuilder,
    GraphExecutionResult
)

# 导入图管理器
from .graph import (
    GraphRegistry,
    GraphManager,
    get_graph_manager
)

# 保留旧的模型以兼容性（标记为废弃）
from .models import (
    NodeType,
    EdgeType,
    NodeStatus,
    NodeConfig,
    EdgeConfig,
    GraphConfig,
    NodeExecution,
    GraphExecution,
    GraphValidationResult
)

__version__ = "2.0.0"

__all__ = [
    # 协议解析
    "ProtocolInfo",
    "GlobalConfig",
    "AgentInfo",
    "WorkflowNode",
    "WorkflowEdge",
    "WorkflowInfo",
    "ParsedProtocol",
    "ProtocolParser",
    
    # 节点工厂
    "GraphState",
    "NodeFunction",
    "BaseNodeBuilder",
    "StartNodeBuilder",
    "EndNodeBuilder",
    "AgentNodeBuilder",
    "NodeFactory",
    
    # 输入输出解析器
    "InputField",
    "OutputField",
    "InputOutputResolver",
    "get_io_resolver",
    
    # 自动构建器
    "LangGraphAutoBuilder",
    "GraphExecutionResult",
    
    # 图管理器
    "GraphRegistry",
    "GraphManager",
    "get_graph_manager",
    
    # 旧模型（兼容性）
    "NodeType",
    "EdgeType", 
    "NodeStatus",
    "NodeConfig",
    "EdgeConfig",
    "GraphConfig",
    "NodeExecution",
    "GraphExecution",
    "GraphValidationResult"
] 