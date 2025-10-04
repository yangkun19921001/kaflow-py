"""
KaFlow-Py LangGraph 自动构建器

使用真正的 LangGraph API (add_node, add_edge, compile) 自动构建图结构

Author: DevYK
微信公众号: DevYK
Email: yang1001yk@gmail.com
Github: https://github.com/yangkun19921001
"""

from typing import Dict, Any, List, Optional, Union
from pathlib import Path

from langgraph.graph import StateGraph, END
from langgraph.graph.state import CompiledStateGraph
from langgraph.checkpoint.memory import MemorySaver

from .parser import ProtocolParser, ParsedProtocol, WorkflowEdge
from .factory import NodeFactory, GraphState, NodeFunction
from ...utils.logger import get_logger

logger = get_logger(__name__)


class LangGraphAutoBuilder:
    """LangGraph 自动构建器"""
    
    def __init__(self):
        self.logger = get_logger(__name__)
        self.parser = ProtocolParser()
        self._conditional_paths = {}  # 存储条件路径映射
    
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
        
        # 重置条件路径映射
        self._conditional_paths = {}
        
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
        
        # 创建 checkpointer（如果配置了内存记忆）
        checkpointer = self._create_checkpointer(protocol)
        
        # 编译图
        if checkpointer:
            compiled_graph = graph.compile(checkpointer=checkpointer)
            self.logger.info(f"LangGraph 编译完成（已启用内存记忆）: {protocol.protocol.name}")
        else:
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
        
        # 收集所有节点名称，用于动态路由
        all_nodes = set()
        for edge in edges:
            all_nodes.add(edge.from_node)
            if edge.to_node not in ['end_node', 'end', END]:
                all_nodes.add(edge.to_node)
        
        for edge in edges:
            if edge.to_node == 'end_node' or edge.to_node.endswith('_end'):
                # 连接到 END - 使用条件边支持动态跳转
                self._add_dynamic_edge(graph, edge.from_node, END, all_nodes)
            else:
                # 普通边
                if edge.condition:
                    # 条件边
                    self._add_conditional_edge(graph, edge)
                else:
                    # 普通边 - 使用条件边支持动态跳转
                    self._add_dynamic_edge(graph, edge.from_node, edge.to_node, all_nodes)
    
    def _add_dynamic_edge(self, graph: StateGraph, from_node: str, default_to_node: str, all_nodes: set) -> None:
        """添加支持动态跳转的边
        
        Args:
            graph: StateGraph 实例
            from_node: 源节点
            default_to_node: 默认目标节点
            all_nodes: 所有可用节点集合
        """
        def routing_func(state: GraphState) -> str:
            """路由函数：检查是否需要动态跳转"""
            # 检查是否有跳转标记
            goto_node = state.get("_goto_node")
            if goto_node:
                self.logger.info(f"🔀 检测到动态跳转标记: {from_node} -> {goto_node}")
                # 清除跳转标记
                state["_goto_node"] = None
                
                # 验证目标节点是否存在
                if goto_node == "end":
                    return END
                elif goto_node in all_nodes:
                    return goto_node
                else:
                    self.logger.warning(f"⚠️ 跳转目标节点不存在: {goto_node}, 使用默认路由")
                    return default_to_node if default_to_node != END else END
            
            # 默认路由
            return default_to_node if default_to_node != END else END
        
        # 构建路径映射
        path_map = {default_to_node if default_to_node != END else END: default_to_node if default_to_node != END else END}
        
        # 添加所有可能的跳转目标
        for node in all_nodes:
            if node != from_node:  # 避免自循环
                path_map[node] = node
        path_map[END] = END
        
        # 添加条件边
        graph.add_conditional_edges(
            from_node,
            routing_func,
            path_map
        )
        self.logger.debug(f"添加动态边: {from_node} -> {default_to_node} (支持动态跳转)")
    
    def _add_conditional_edge(self, graph: StateGraph, edge: WorkflowEdge) -> None:
        """添加条件边"""
        self.logger.debug(f"添加条件边: {edge.from_node} -> {edge.to_node} (条件: {edge.condition})")
        
        # 为每个条件边创建唯一的条件函数
        condition_name = f"{edge.from_node}_to_{edge.to_node}_condition"
        
        def create_condition_func(condition_expr: str, target_node: str):
            """创建条件函数的工厂方法"""
            def condition_func(state: GraphState) -> str:
                """条件函数"""
                try:
                    # 从条件节点的输出中获取条件结果
                    node_outputs = state.get("node_outputs", {})
                    
                    # 如果源节点是条件节点，检查其条件结果
                    if edge.from_node in node_outputs:
                        node_output = node_outputs[edge.from_node]
                        if node_output.get("node_type") == "condition":
                            condition_results = node_output.get("condition_results", {})
                            
                            # 检查特定条件是否为真
                            if condition_expr in condition_results:
                                if condition_results[condition_expr]:
                                    self.logger.debug(f"条件 {condition_expr} 为真，路由到 {target_node}")
                                    return target_node
                                else:
                                    self.logger.debug(f"条件 {condition_expr} 为假，跳过")
                                    return "__skip__"  # 特殊值表示不走这条路径
                    
                    # 传统的条件判断（向后兼容）
                    if condition_expr == "success":
                        return target_node if state.get("current_step", "").endswith("completed") else "__skip__"
                    elif condition_expr == "failure":
                        return target_node if state.get("current_step", "").endswith("failed") else "__skip__"
                    else:
                        # 默认情况 - 总是路由到目标节点
                        return target_node
                        
                except Exception as e:
                    self.logger.error(f"条件评估失败: {e}")
                    return "__skip__"
            
            return condition_func
        
        # 创建条件函数
        condition_func = create_condition_func(edge.condition, edge.to_node)
        
        # 检查是否已经为这个源节点添加过条件边
        # 如果是，需要合并条件
        source_node = edge.from_node
        
        # 创建或更新路径映射
        if not hasattr(self, '_conditional_paths'):
            self._conditional_paths = {}
        
        if source_node not in self._conditional_paths:
            self._conditional_paths[source_node] = {}
        
        # 添加这个条件的路径
        self._conditional_paths[source_node][edge.condition] = edge.to_node
        
        # 创建综合的条件函数
        def master_condition_func(state: GraphState) -> str:
            """主条件函数，处理多个条件分支"""
            try:
                node_outputs = state.get("node_outputs", {})
                
                if source_node in node_outputs:
                    node_output = node_outputs[source_node]
                    if node_output.get("node_type") == "condition":
                        condition_results = node_output.get("condition_results", {})
                        
                        # 检查每个条件，返回第一个为真的条件对应的目标节点
                        for condition_name, target_node in self._conditional_paths[source_node].items():
                            if condition_name in condition_results and condition_results[condition_name]:
                                self.logger.debug(f"条件 {condition_name} 为真，路由到 {target_node}")
                                return target_node
                
                # 如果没有条件为真，返回END
                self.logger.debug(f"没有条件为真，从 {source_node} 结束")
                return END
                
            except Exception as e:
                self.logger.error(f"主条件函数评估失败: {e}")
                return END
        
        # 构建完整的路径映射
        path_map = {}
        for condition_name, target_node in self._conditional_paths[source_node].items():
            path_map[target_node] = target_node
        path_map[END] = END
        path_map["__skip__"] = END  # 处理跳过的情况
        
        # 只在第一次为这个源节点添加条件边时调用add_conditional_edges
        if len(self._conditional_paths[source_node]) == 1:
            graph.add_conditional_edges(
                source_node,
                master_condition_func,
                path_map
            )
        else:
            # 如果已经添加过，更新路径映射
            # 注意：LangGraph不支持动态更新条件边，所以我们需要重新构建
            self.logger.debug(f"更新节点 {source_node} 的条件路径映射")
            # 这里可能需要重新构建图，但为了简化，我们假设所有条件边在初始构建时就定义好了
    
    def _create_checkpointer(self, protocol: ParsedProtocol) -> Optional[MemorySaver]:
        """
        根据配置创建 checkpointer
        
        Args:
            protocol: 解析后的协议
            
        Returns:
            MemorySaver 实例或 None
        """
        # 检查是否有 global_config 和 memory 配置
        if not protocol.global_config or not protocol.global_config.memory:
            self.logger.debug("未配置内存记忆")
            return None
        
        memory_config = protocol.global_config.memory
        
        # 检查是否启用
        enabled = memory_config.get("enabled", False)
        if not enabled:
            self.logger.debug("内存记忆未启用")
            return None
        
        # 获取 provider 类型
        provider = memory_config.get("provider", "memory")
        
        # 根据 provider 类型创建对应的 checkpointer
        if provider == "memory":
            self.logger.info("✅ 启用内存记忆存储 (InMemorySaver)")
            return MemorySaver()
        else:
            # 其他类型的 provider 暂不支持
            self.logger.warning(
                f"⚠️ 不支持的记忆存储类型: {provider}。"
                f"当前仅支持 'memory' (InMemorySaver)。"
                f"支持的类型: memory | redis | postgresql | mongodb | sqlite (即将支持)"
            )
            return None
    
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