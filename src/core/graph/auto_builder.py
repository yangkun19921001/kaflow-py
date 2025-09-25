"""
KaFlow-Py LangGraph 自动构建器

使用真正的 LangGraph API (add_node, add_edge, compile) 自动构建图结构

Author: DevYK
WeChat: DevYK
Email: yang1001yk@gmail.com
Github: https://github.com/yangkun19921001
"""

from typing import Dict, Any, List, Optional, Union
from pathlib import Path

from langgraph.graph import StateGraph, END
from langgraph.graph.state import CompiledStateGraph

from .protocol_parser import ProtocolParser, ParsedProtocol, WorkflowEdge
from .node_factory import NodeFactory, GraphState, NodeFunction
from ...utils.logger import get_logger

logger = get_logger(__name__)


class LangGraphAutoBuilder:
    """LangGraph 自动构建器"""
    
    def __init__(self):
        self.logger = get_logger(__name__)
        self.parser = ProtocolParser()
    
    def build_from_file(self, file_path: Union[str, Path]) -> CompiledStateGraph:
        """
        从协议文件构建 LangGraph
        
        Args:
            file_path: 协议文件路径
            
        Returns:
            编译后的 LangGraph
        """
        self.logger.info(f"从文件构建 LangGraph: {file_path}")
        
        # 解析协议
        protocol = self.parser.parse_from_file(file_path)
        
        # 验证协议
        errors = self.parser.validate_protocol(protocol)
        if errors:
            raise ValueError(f"协议验证失败: {errors}")
        
        return self.build_from_protocol(protocol)
    
    def build_from_content(self, content: str) -> CompiledStateGraph:
        """
        从协议内容构建 LangGraph
        
        Args:
            content: 协议内容
            
        Returns:
            编译后的 LangGraph
        """
        self.logger.info("从内容构建 LangGraph")
        
        # 解析协议
        protocol = self.parser.parse_from_content(content)
        
        # 验证协议
        errors = self.parser.validate_protocol(protocol)
        if errors:
            raise ValueError(f"协议验证失败: {errors}")
        
        return self.build_from_protocol(protocol)
    
    def build_from_protocol(self, protocol: ParsedProtocol) -> CompiledStateGraph:
        """
        从解析后的协议构建 LangGraph
        
        Args:
            protocol: 解析后的协议
            
        Returns:
            编译后的 LangGraph
        """
        self.logger.info(f"构建 LangGraph: {protocol.protocol.name}")
        
        # 创建状态图
        graph = StateGraph(GraphState)
        
        # 创建节点工厂
        node_factory = NodeFactory(protocol)
        
        # 创建所有节点函数
        node_functions = node_factory.create_all_node_functions()
        
        # 添加节点到图
        self._add_nodes(graph, node_functions)
        
        # 添加边到图
        self._add_edges(graph, protocol.workflow.edges)
        
        # 设置入口点
        entry_point = self._find_entry_point(protocol)
        graph.set_entry_point(entry_point)
        self.logger.debug(f"设置入口点: {entry_point}")
        
        # 编译图
        compiled_graph = graph.compile()
        self.logger.info(f"LangGraph 编译完成: {protocol.protocol.name}")
        
        return compiled_graph
    
    def _add_nodes(self, graph: StateGraph, node_functions: Dict[str, NodeFunction]) -> None:
        """添加节点到图"""
        self.logger.debug("添加节点到图")
        
        for node_name, node_func in node_functions.items():
            graph.add_node(node_name, node_func)
            self.logger.debug(f"添加节点: {node_name} (类型: {node_func.node_type})")
    
    def _add_edges(self, graph: StateGraph, edges: List[WorkflowEdge]) -> None:
        """添加边到图"""
        self.logger.debug("添加边到图")
        
        for edge in edges:
            if edge.to_node == 'end_node' or edge.to_node.endswith('_end'):
                # 连接到 END
                graph.add_edge(edge.from_node, END)
                self.logger.debug(f"添加边: {edge.from_node} -> END")
            else:
                # 普通边
                if edge.condition:
                    # 条件边
                    self._add_conditional_edge(graph, edge)
                else:
                    # 普通边
                    graph.add_edge(edge.from_node, edge.to_node)
                    self.logger.debug(f"添加边: {edge.from_node} -> {edge.to_node}")
    
    def _add_conditional_edge(self, graph: StateGraph, edge: WorkflowEdge) -> None:
        """添加条件边"""
        self.logger.debug(f"添加条件边: {edge.from_node} -> {edge.to_node} (条件: {edge.condition})")
        
        # 创建条件函数
        def condition_func(state: GraphState) -> str:
            """条件函数"""
            # 简单的条件判断实现
            # TODO: 实现更复杂的条件逻辑
            if edge.condition == "success":
                return edge.to_node if state.get("current_step", "").endswith("completed") else END
            elif edge.condition == "failure":
                return edge.to_node if state.get("current_step", "").endswith("failed") else END
            else:
                # 默认情况
                return edge.to_node
        
        # 创建路径映射
        path_map = {
            edge.to_node: edge.to_node,
            END: END
        }
        
        graph.add_conditional_edges(
            edge.from_node,
            condition_func,
            path_map
        )
    
    def _find_entry_point(self, protocol: ParsedProtocol) -> str:
        """查找入口点"""
        # 查找 start 类型的节点
        for node in protocol.workflow.nodes:
            if node.type == 'start':
                return node.name
        
        # 如果没有 start 节点，返回第一个节点
        if protocol.workflow.nodes:
            return protocol.workflow.nodes[0].name
        
        raise ValueError("未找到入口点节点")
    
    def get_graph_info(self, protocol: ParsedProtocol) -> Dict[str, Any]:
        """
        获取图结构信息
        
        Args:
            protocol: 解析后的协议
            
        Returns:
            图结构信息
        """
        nodes_info = []
        for node in protocol.workflow.nodes:
            node_info = {
                "name": node.name,
                "type": node.type,
                "description": node.description
            }
            if node.agent_ref:
                node_info["agent_ref"] = node.agent_ref
            nodes_info.append(node_info)
        
        edges_info = []
        for edge in protocol.workflow.edges:
            edge_info = {
                "from": edge.from_node,
                "to": edge.to_node,
                "description": edge.description
            }
            if edge.condition:
                edge_info["condition"] = edge.condition
            edges_info.append(edge_info)
        
        return {
            "id": protocol.id,  # 包含配置ID
            "protocol": {
                "name": protocol.protocol.name,
                "version": protocol.protocol.version,
                "description": protocol.protocol.description
            },
            "workflow": {
                "name": protocol.workflow.name,
                "description": protocol.workflow.description
            },
            "nodes": nodes_info,
            "edges": edges_info,
            "agents": {name: {
                "type": agent.type,
                "description": agent.description,
                "tools_count": len(agent.tools)
            } for name, agent in protocol.agents.items()}
        }


class GraphExecutionResult:
    """图执行结果"""
    
    def __init__(self, 
                 status: str,
                 final_response: str = "",
                 messages: List = None,
                 current_step: str = "",
                 tool_results: Dict[str, Any] = None,
                 context: Dict[str, Any] = None,
                 node_outputs: Dict[str, Any] = None,
                 error: Optional[str] = None):
        self.status = status
        self.final_response = final_response
        self.messages = messages or []
        self.current_step = current_step
        self.tool_results = tool_results or {}
        self.context = context or {}
        self.node_outputs = node_outputs or {}
        self.error = error


class GraphStreamEvent:
    """图流式执行事件"""
    
    def __init__(self,
                 event_type: str,
                 node_name: str = "",
                 data: Dict[str, Any] = None,
                 timestamp: Optional[str] = None):
        self.event_type = event_type  # 'node_start', 'node_end', 'node_update', 'tool_call', 'message', 'error'
        self.node_name = node_name
        self.data = data or {}
        self.timestamp = timestamp or self._get_current_time()
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "event_type": self.event_type,
            "node_name": self.node_name,
            "data": self.data,
            "timestamp": self.timestamp
        }
    
    def _get_current_time(self) -> str:
        """获取当前时间"""
        import datetime
        return datetime.datetime.now().isoformat()
    
    def is_success(self) -> bool:
        """是否成功"""
        return self.status == "completed" and not self.error
    
    def is_failed(self) -> bool:
        """是否失败"""
        return self.status == "failed" or self.error is not None


__all__ = [
    "LangGraphAutoBuilder",
    "GraphExecutionResult",
    "GraphStreamEvent"
] 