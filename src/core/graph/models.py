"""
KaFlow-Py Graph 数据模型

定义图结构相关的数据模型，包括：
- 节点模型
- 边模型
- 图配置模型
- 执行状态模型

Author: DevYK
微信公众号: DevYK
Email: yang1001yk@gmail.com
Github: https://github.com/yangkun19921001
"""

from typing import Dict, List, Optional, Any, Union
from enum import Enum
from pydantic import BaseModel, Field
from datetime import datetime



class NodeType(str, Enum):
    """节点类型枚举"""
    START = "start"                    # 开始节点
    END = "end"                       # 结束节点
    AGENT = "agent"                   # Agent 节点
    TOOL = "tool"                     # 工具节点
    CONDITION = "condition"           # 条件判断节点
    PARALLEL = "parallel"             # 并行执行节点
    SEQUENTIAL = "sequential"         # 顺序执行节点
    HUMAN = "human"                   # 人工干预节点
    INTERRUPT = "interrupt"           # 中断节点


class EdgeType(str, Enum):
    """边类型枚举"""
    NORMAL = "normal"                 # 普通边
    CONDITIONAL = "conditional"       # 条件边
    DEFAULT = "default"               # 默认边
    ERROR = "error"                   # 错误处理边


class NodeStatus(str, Enum):
    """节点执行状态"""
    PENDING = "pending"               # 等待执行
    RUNNING = "running"               # 正在执行
    COMPLETED = "completed"           # 执行完成
    FAILED = "failed"                 # 执行失败
    SKIPPED = "skipped"               # 跳过执行


class NodeConfig(BaseModel):
    """节点配置模型"""
    
    # 基础信息
    id: str = Field(..., description="节点唯一标识")
    name: str = Field(..., description="节点名称")
    type: NodeType = Field(..., description="节点类型")
    description: Optional[str] = Field(None, description="节点描述")
    
    # 执行配置
    config: Dict[str, Any] = Field(default_factory=dict, description="节点特定配置")
    timeout: Optional[int] = Field(30, description="执行超时时间（秒）")
    retry_count: Optional[int] = Field(0, description="重试次数")
    
    # Agent 相关配置
    agent_type: Optional[str] = Field(None, description="Agent 类型")
    llm_config: Optional[Dict[str, Any]] = Field(None, description="LLM 配置")
    tools: Optional[List[str]] = Field(None, description="可用工具列表")
    system_prompt: Optional[str] = Field(None, description="系统提示词")
    
    # 工具相关配置
    tool_name: Optional[str] = Field(None, description="工具名称")
    tool_args: Optional[Dict[str, Any]] = Field(None, description="工具参数")
    
    # 条件判断配置
    condition: Optional[str] = Field(None, description="条件表达式")
    
    # 并行/顺序执行配置
    sub_nodes: Optional[List[str]] = Field(None, description="子节点列表")
    
    # 位置信息（用于可视化）
    position: Optional[Dict[str, float]] = Field(None, description="节点位置 {x, y}")


class EdgeConfig(BaseModel):
    """边配置模型"""
    
    # 基础信息
    id: str = Field(..., description="边唯一标识")
    source: str = Field(..., description="源节点ID")
    target: str = Field(..., description="目标节点ID")
    type: EdgeType = Field(EdgeType.NORMAL, description="边类型")
    
    # 条件配置
    condition: Optional[str] = Field(None, description="边的触发条件")
    priority: Optional[int] = Field(0, description="边的优先级")
    
    # 数据传输配置
    data_mapping: Optional[Dict[str, str]] = Field(None, description="数据映射规则")
    
    # 样式配置（用于可视化）
    style: Optional[Dict[str, Any]] = Field(None, description="边的样式配置")


class GraphConfig(BaseModel):
    """图配置模型"""
    
    # 基础信息
    id: str = Field(..., description="图唯一标识")
    name: str = Field(..., description="图名称")
    version: str = Field("1.0.0", description="图版本")
    description: Optional[str] = Field(None, description="图描述")
    
    # 图结构
    nodes: List[NodeConfig] = Field(..., description="节点列表")
    edges: List[EdgeConfig] = Field(..., description="边列表")
    
    # 执行配置
    start_node: str = Field(..., description="开始节点ID")
    end_nodes: List[str] = Field(default_factory=list, description="结束节点ID列表")
    
    # 全局配置
    global_config: Dict[str, Any] = Field(default_factory=dict, description="全局配置")
    variables: Dict[str, Any] = Field(default_factory=dict, description="全局变量")
    
    # 元数据
    created_at: Optional[datetime] = Field(None, description="创建时间")
    updated_at: Optional[datetime] = Field(None, description="更新时间")
    tags: List[str] = Field(default_factory=list, description="标签列表")


class NodeExecution(BaseModel):
    """节点执行状态"""
    
    node_id: str = Field(..., description="节点ID")
    status: NodeStatus = Field(NodeStatus.PENDING, description="执行状态")
    start_time: Optional[datetime] = Field(None, description="开始时间")
    end_time: Optional[datetime] = Field(None, description="结束时间")
    duration: Optional[float] = Field(None, description="执行时长（秒）")
    
    # 执行结果
    input_data: Optional[Dict[str, Any]] = Field(None, description="输入数据")
    output_data: Optional[Dict[str, Any]] = Field(None, description="输出数据")
    error_message: Optional[str] = Field(None, description="错误信息")
    
    # 重试信息
    retry_count: int = Field(0, description="已重试次数")
    max_retries: int = Field(0, description="最大重试次数")


class GraphExecution(BaseModel):
    """图执行状态"""
    
    graph_id: str = Field(..., description="图ID")
    execution_id: str = Field(..., description="执行ID")
    status: NodeStatus = Field(NodeStatus.PENDING, description="整体执行状态")
    
    # 时间信息
    start_time: Optional[datetime] = Field(None, description="开始时间")
    end_time: Optional[datetime] = Field(None, description="结束时间")
    duration: Optional[float] = Field(None, description="总执行时长（秒）")
    
    # 执行详情
    node_executions: List[NodeExecution] = Field(default_factory=list, description="节点执行状态列表")
    current_node: Optional[str] = Field(None, description="当前执行节点")
    
    # 全局状态
    global_variables: Dict[str, Any] = Field(default_factory=dict, description="全局变量")
    execution_context: Dict[str, Any] = Field(default_factory=dict, description="执行上下文")
    
    # 结果
    final_result: Optional[Dict[str, Any]] = Field(None, description="最终执行结果")
    error_message: Optional[str] = Field(None, description="错误信息")


class GraphValidationResult(BaseModel):
    """图验证结果"""
    
    is_valid: bool = Field(..., description="是否有效")
    errors: List[str] = Field(default_factory=list, description="错误列表")
    warnings: List[str] = Field(default_factory=list, description="警告列表")
    suggestions: List[str] = Field(default_factory=list, description="建议列表")


__all__ = [
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