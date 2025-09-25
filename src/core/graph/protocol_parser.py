"""
KaFlow-Py 协议解析器

解析 KaFlow 协议模板，提取工作流、Agent 和 LLM 配置

Author: DevYK
WeChat: DevYK
Email: yang1001yk@gmail.com
Github: https://github.com/yangkun19921001
"""

import os
import yaml
import re
from typing import Dict, Any, List, Optional, Union
from pathlib import Path
from pydantic import BaseModel, Field

from ...utils.logger import get_logger

logger = get_logger(__name__)


class ProtocolInfo(BaseModel):
    """协议信息"""
    name: str
    version: str
    schema_version: str
    description: Optional[str] = None
    author: Optional[str] = None
    license: Optional[str] = None


class GlobalConfig(BaseModel):
    """全局配置"""
    logging: Optional[Dict[str, Any]] = None
    memory: Optional[Dict[str, Any]] = None
    runtime: Optional[Dict[str, Any]] = None


class AgentInfo(BaseModel):
    """Agent 信息"""
    name: str
    type: str
    description: Optional[str] = None
    enabled: bool = True
    system_prompt: Optional[str] = None
    llm: Optional[Dict[str, Any]] = None
    tools: List[Dict[str, Any]] = Field(default_factory=list)
    mcp_servers: List[Dict[str, Any]] = Field(default_factory=list)


class WorkflowNode(BaseModel):
    """工作流节点"""
    name: str
    type: str
    description: Optional[str] = None
    agent_ref: Optional[str] = None
    position: Optional[Dict[str, Any]] = None
    inputs: List[Dict[str, Any]] = Field(default_factory=list)
    outputs: List[Dict[str, Any]] = Field(default_factory=list)
    conditions: Optional[Dict[str, Any]] = None


class WorkflowEdge(BaseModel):
    """工作流边"""
    from_node: str = Field(alias="from")
    to_node: str = Field(alias="to")
    description: Optional[str] = None
    condition: Optional[str] = None
    condition_type: Optional[str] = None


class WorkflowInfo(BaseModel):
    """工作流信息"""
    name: str
    version: str
    description: Optional[str] = None
    author: Optional[str] = None
    schema_version: Optional[str] = None
    settings: Optional[Dict[str, Any]] = None
    nodes: List[WorkflowNode] = Field(default_factory=list)
    edges: List[WorkflowEdge] = Field(default_factory=list)


class ParsedProtocol(BaseModel):
    """解析后的协议"""
    id: Optional[str] = None  # 添加配置ID字段
    protocol: ProtocolInfo
    global_config: Optional[GlobalConfig] = None
    llm_config: Optional[Dict[str, Any]] = None
    agents: Dict[str, AgentInfo] = Field(default_factory=dict)
    workflow: WorkflowInfo
    raw_data: Dict[str, Any] = Field(default_factory=dict)


class ProtocolParser:
    """协议解析器"""
    
    def __init__(self):
        self.logger = get_logger(__name__)
    
    def parse_from_file(self, file_path: Union[str, Path]) -> ParsedProtocol:
        """
        从文件解析协议
        
        Args:
            file_path: 协议文件路径
            
        Returns:
            解析后的协议对象
        """
        file_path = Path(file_path)
        self.logger.info(f"解析协议文件: {file_path}")
        
        if not file_path.exists():
            raise FileNotFoundError(f"协议文件不存在: {file_path}")
        
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        return self.parse_from_content(content)
    
    def parse_from_content(self, content: str) -> ParsedProtocol:
        """
        从内容解析协议
        
        Args:
            content: YAML 内容
            
        Returns:
            解析后的协议对象
        """
        self.logger.debug("解析协议内容")
        
        # 解析环境变量
        content = self._resolve_env_vars(content)
        
        # 解析 YAML
        try:
            data = yaml.safe_load(content)
        except yaml.YAMLError as e:
            raise ValueError(f"YAML 解析失败: {e}")
        
        return self._parse_protocol_data(data)
    
    def _resolve_env_vars(self, content: str) -> str:
        """解析环境变量"""
        def replace_env_var(match):
            var_name = match.group(1)
            default_value = match.group(2) if match.group(2) else ""
            return os.getenv(var_name, default_value)
        
        # 支持 ${VAR_NAME} 和 ${VAR_NAME:default} 格式
        pattern = r'\$\{([^}:]+)(?::([^}]*))?\}'
        return re.sub(pattern, replace_env_var, content)
    
    def _parse_protocol_data(self, data: Dict[str, Any]) -> ParsedProtocol:
        """解析协议数据"""
        self.logger.debug("解析协议数据结构")
        
        # 解析协议信息
        protocol_data = data.get('protocol', {})
        protocol = ProtocolInfo(**protocol_data)
        
        # 解析全局配置
        global_config = None
        if 'global_config' in data:
            global_config = GlobalConfig(**data['global_config'])
        
        # 解析 LLM 配置
        llm_config = data.get('llm_config')
        
        # 解析 Agent 配置
        agents = {}
        agents_data = data.get('agents', {})
        for agent_name, agent_data in agents_data.items():
            # 确保 agent_data 是字典并且不包含 name 字段冲突
            if isinstance(agent_data, dict):
                agent_data_copy = agent_data.copy()
                # 如果 agent_data 中已经有 name，使用它；否则使用 key 名称
                if 'name' not in agent_data_copy:
                    agent_data_copy['name'] = agent_name
                agent_info = AgentInfo(**agent_data_copy)
            else:
                agent_info = AgentInfo(name=agent_name)
            agents[agent_name] = agent_info
        
        # 解析工作流
        workflow_data = data.get('workflow', {})
        
        # 解析节点
        nodes = []
        for node_data in workflow_data.get('nodes', []):
            node = WorkflowNode(**node_data)
            nodes.append(node)
        
        # 解析边
        edges = []
        for edge_data in workflow_data.get('edges', []):
            edge = WorkflowEdge(**edge_data)
            edges.append(edge)
        
        # 构建工作流信息
        workflow = WorkflowInfo(
            nodes=nodes,
            edges=edges,
            **{k: v for k, v in workflow_data.items() if k not in ['nodes', 'edges']}
        )
        
        return ParsedProtocol(
            id=str(data.get('id')) if data.get('id') is not None else None,  # 提取ID并转换为字符串
            protocol=protocol,
            global_config=global_config,
            llm_config=llm_config,
            agents=agents,
            workflow=workflow,
            raw_data=data
        )
    
    def validate_protocol(self, parsed: ParsedProtocol) -> List[str]:
        """
        验证协议完整性
        
        Args:
            parsed: 解析后的协议
            
        Returns:
            验证错误列表（空列表表示验证通过）
        """
        errors = []
        
        # 验证基础信息
        if not parsed.protocol.name:
            errors.append("协议名称不能为空")
        
        if not parsed.protocol.version:
            errors.append("协议版本不能为空")
        
        # 验证工作流
        if not parsed.workflow.nodes:
            errors.append("工作流必须包含至少一个节点")
        
        # 验证节点引用
        node_names = {node.name for node in parsed.workflow.nodes}
        
        for edge in parsed.workflow.edges:
            if edge.from_node not in node_names:
                errors.append(f"边引用了不存在的源节点: {edge.from_node}")
            if edge.to_node not in node_names:
                errors.append(f"边引用了不存在的目标节点: {edge.to_node}")
        
        # 验证 Agent 引用
        for node in parsed.workflow.nodes:
            if node.type == 'agent' and node.agent_ref:
                if node.agent_ref not in parsed.agents:
                    errors.append(f"节点 {node.name} 引用了不存在的 Agent: {node.agent_ref}")
        
        # 验证工作流结构
        start_nodes = [node for node in parsed.workflow.nodes if node.type == 'start']
        if not start_nodes:
            errors.append("工作流必须包含至少一个开始节点")
        elif len(start_nodes) > 1:
            errors.append("工作流只能包含一个开始节点")
        
        end_nodes = [node for node in parsed.workflow.nodes if node.type == 'end']
        if not end_nodes:
            errors.append("工作流必须包含至少一个结束节点")
        
        return errors


__all__ = [
    "ProtocolInfo",
    "GlobalConfig", 
    "AgentInfo",
    "WorkflowNode",
    "WorkflowEdge",
    "WorkflowInfo",
    "ParsedProtocol",
    "ProtocolParser"
] 