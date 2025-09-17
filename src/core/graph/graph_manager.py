"""
KaFlow-Py 图管理器

统一管理 LangGraph 的构建、注册和执行

Author: DevYK
WeChat: DevYK
Email: yang1001yk@gmail.com
Github: https://github.com/yangkun19921001
"""

import asyncio
from typing import Dict, Any, List, Optional, Union
from pathlib import Path

from langgraph.graph.state import CompiledStateGraph

from .auto_builder import LangGraphAutoBuilder, GraphExecutionResult, GraphStreamEvent
from .node_factory import GraphState
from .protocol_parser import ProtocolParser, ParsedProtocol
from ...utils.logger import get_logger

logger = get_logger(__name__)


class GraphRegistry:
    """图注册表"""
    
    def __init__(self):
        self._graphs: Dict[str, CompiledStateGraph] = {}
        self._protocols: Dict[str, ParsedProtocol] = {}
        self._metadata: Dict[str, Dict[str, Any]] = {}
    
    def register(self, 
                 graph_id: str, 
                 compiled_graph: CompiledStateGraph, 
                 protocol: ParsedProtocol,
                 metadata: Optional[Dict[str, Any]] = None) -> None:
        """注册图"""
        self._graphs[graph_id] = compiled_graph
        self._protocols[graph_id] = protocol
        self._metadata[graph_id] = metadata or {}
    
    def get_graph(self, graph_id: str) -> Optional[CompiledStateGraph]:
        """获取图"""
        return self._graphs.get(graph_id)
    
    def get_protocol(self, graph_id: str) -> Optional[ParsedProtocol]:
        """获取协议"""
        return self._protocols.get(graph_id)
    
    def get_metadata(self, graph_id: str) -> Optional[Dict[str, Any]]:
        """获取元数据"""
        return self._metadata.get(graph_id)
    
    def list_graphs(self) -> List[str]:
        """列出所有图ID"""
        return list(self._graphs.keys())
    
    def remove(self, graph_id: str) -> bool:
        """移除图"""
        if graph_id in self._graphs:
            del self._graphs[graph_id]
            del self._protocols[graph_id]
            del self._metadata[graph_id]
            return True
        return False
    
    def clear(self) -> None:
        """清空注册表"""
        self._graphs.clear()
        self._protocols.clear()
        self._metadata.clear()


class GraphManager:
    """图管理器"""
    
    def __init__(self):
        self.logger = get_logger(__name__)
        self.builder = LangGraphAutoBuilder()
        self.registry = GraphRegistry()
    
    def register_graph_from_file(self, 
                                 file_path: Union[str, Path], 
                                 graph_id: Optional[str] = None) -> str:
        """
        从文件注册图
        
        Args:
            file_path: 协议文件路径
            graph_id: 图ID（可选，默认使用文件名）
            
        Returns:
            图ID
        """
        file_path = Path(file_path)
        if not graph_id:
            graph_id = file_path.stem
        
        self.logger.info(f"从文件注册图: {file_path} -> {graph_id}")
        
        # 解析协议
        protocol = self.builder.parser.parse_from_file(file_path)
        
        # 构建图
        compiled_graph = self.builder.build_from_protocol(protocol)
        
        # 获取图信息
        graph_info = self.builder.get_graph_info(protocol)
        
        # 注册图
        self.registry.register(
            graph_id=graph_id,
            compiled_graph=compiled_graph,
            protocol=protocol,
            metadata={
                "source_file": str(file_path),
                "graph_info": graph_info,
                "created_at": self._get_current_time()
            }
        )
        
        self.logger.info(f"图注册成功: {graph_id}")
        return graph_id
    
    def register_graph_from_content(self, 
                                    content: str, 
                                    graph_id: str) -> str:
        """
        从内容注册图
        
        Args:
            content: 协议内容
            graph_id: 图ID
            
        Returns:
            图ID
        """
        self.logger.info(f"从内容注册图: {graph_id}")
        
        # 解析协议
        protocol = self.builder.parser.parse_from_content(content)
        
        # 构建图
        compiled_graph = self.builder.build_from_protocol(protocol)
        
        # 获取图信息
        graph_info = self.builder.get_graph_info(protocol)
        
        # 注册图
        self.registry.register(
            graph_id=graph_id,
            compiled_graph=compiled_graph,
            protocol=protocol,
            metadata={
                "source_type": "content",
                "graph_info": graph_info,
                "created_at": self._get_current_time()
            }
        )
        
        self.logger.info(f"图注册成功: {graph_id}")
        return graph_id
    
    async def execute_graph(self, 
                           graph_id: str, 
                           user_input: str,
                           **kwargs) -> GraphExecutionResult:
        """
        执行图
        
        Args:
            graph_id: 图ID
            user_input: 用户输入
            **kwargs: 其他参数
            
        Returns:
            执行结果
        """
        self.logger.info(f"执行图: {graph_id}")
        self.logger.debug(f"用户输入: {user_input}")
        
        # 获取图
        compiled_graph = self.registry.get_graph(graph_id)
        if not compiled_graph:
            error_msg = f"图不存在: {graph_id}. 可用图: {self.registry.list_graphs()}"
            self.logger.error(error_msg)
            return GraphExecutionResult(
                status="failed",
                error=error_msg,
                final_response=f"图不存在: {graph_id}"
            )
        
        # 构建初始状态
        initial_state: GraphState = {
            "user_input": user_input,
            "messages": [],
            "current_step": "init",
            "tool_results": {},
            "final_response": "",
            "context": kwargs,
            "node_outputs": {}
        }
        
        try:
            # 执行图 - 使用异步调用以支持 MCP 工具
            self.logger.debug("开始执行图（异步模式）")
            
            # 检查是否有异步节点，如果有则使用异步调用
            result = await compiled_graph.ainvoke(initial_state)
            
            self.logger.info(f"图执行完成: {graph_id}")
            
            # 构建执行结果
            execution_result = GraphExecutionResult(
                status="completed",
                final_response=result.get("final_response", ""),
                messages=result.get("messages", []),
                current_step=result.get("current_step", ""),
                tool_results=result.get("tool_results", {}),
                context=result.get("context", {}),
                node_outputs=result.get("node_outputs", {})
            )
            
            self.logger.debug(f"执行结果状态: {execution_result.status}")
            return execution_result
            
        except Exception as e:
            self.logger.error(f"图执行失败: {graph_id}, 错误: {e}")
            return GraphExecutionResult(
                status="failed",
                error=str(e),
                final_response=f"执行失败: {str(e)}",
                context=kwargs
            )
    
    async def execute_graph_stream(self, 
                                  graph_id: str, 
                                  user_input: str,
                                  **kwargs):
        """
        流式执行图，返回实时流数据
        
        Args:
            graph_id: 图ID
            user_input: 用户输入
            **kwargs: 其他参数
            
        Yields:
            GraphStreamEvent: 流式执行事件
        """
        self.logger.info(f"流式执行图: {graph_id}")
        self.logger.debug(f"用户输入: {user_input}")
        
        # 获取图
        compiled_graph = self.registry.get_graph(graph_id)
        if not compiled_graph:
            error_msg = f"图不存在: {graph_id}. 可用图: {self.registry.list_graphs()}"
            self.logger.error(error_msg)
            yield GraphStreamEvent(
                event_type="error",
                data={"error": error_msg, "final_response": f"图不存在: {graph_id}"}
            )
            return
        
        # 构建初始状态
        initial_state: GraphState = {
            "user_input": user_input,
            "messages": [],
            "current_step": "init",
            "tool_results": {},
            "final_response": "",
            "context": kwargs,
            "node_outputs": {}
        }
        
        try:
            # 发送开始事件
            yield GraphStreamEvent(
                event_type="graph_start",
                data={"graph_id": graph_id, "user_input": user_input}
            )
            
            # 流式执行图
            self.logger.debug("开始流式执行图（异步模式）")
            
            # 使用 astream 进行流式执行
            async for chunk in compiled_graph.astream(initial_state):
                self.logger.debug(f"收到流式数据块: {type(chunk)} - {repr(chunk)[:200]}...")
                
                # 处理不同格式的流式数据块
                if isinstance(chunk, dict):
                    # 标准字典格式
                    for node_name, node_data in chunk.items():
                        self.logger.debug(f"流式数据: 节点 {node_name}, 数据: {type(node_data)}")
                        
                        # 发送节点更新事件
                        yield GraphStreamEvent(
                            event_type="node_update",
                            node_name=node_name,
                            data={
                                "node_data": self._serialize_node_data(node_data),
                                "current_step": node_data.get("current_step", ""),
                                "messages_count": len(node_data.get("messages", [])),
                                "has_final_response": bool(node_data.get("final_response", ""))
                            }
                        )
                        
                        # 如果有最终响应，发送消息事件
                        if node_data.get("final_response"):
                            yield GraphStreamEvent(
                                event_type="message",
                                node_name=node_name,
                                data={
                                    "content": node_data["final_response"],
                                    "message_type": "final_response"
                                }
                            )
                        
                        # 如果有工具调用结果，发送工具事件
                        if node_data.get("tool_results"):
                            yield GraphStreamEvent(
                                event_type="tool_call",
                                node_name=node_name,
                                data={"tool_results": node_data["tool_results"]}
                            )
                        
                elif isinstance(chunk, tuple):
                    # 元组格式 (node_name, node_data)
                    if len(chunk) == 2:
                        node_name, node_data = chunk
                        self.logger.debug(f"流式数据(tuple): 节点 {node_name}, 数据: {type(node_data)}")
                        
                        # 处理元组格式的数据（与字典格式相同的逻辑）
                        yield GraphStreamEvent(
                            event_type="node_update",
                            node_name=node_name,
                            data={
                                "node_data": self._serialize_node_data(node_data),
                                "current_step": node_data.get("current_step", "") if isinstance(node_data, dict) else "",
                                "messages_count": len(node_data.get("messages", [])) if isinstance(node_data, dict) else 0,
                                "has_final_response": bool(node_data.get("final_response", "")) if isinstance(node_data, dict) else False
                            }
                        )
                        
                        if isinstance(node_data, dict) and node_data.get("final_response"):
                            yield GraphStreamEvent(
                                event_type="message",
                                node_name=node_name,
                                data={
                                    "content": node_data["final_response"],
                                    "message_type": "final_response"
                                }
                            )
                    else:
                        self.logger.warning(f"未知的元组格式: {chunk}")
                        
                else:
                    self.logger.warning(f"未知的流式数据格式: {type(chunk)} - {chunk}")
            
            # 发送完成事件
            yield GraphStreamEvent(
                event_type="graph_end",
                data={"status": "completed", "graph_id": graph_id}
            )
            
            self.logger.info(f"流式图执行完成: {graph_id}")
            
        except Exception as e:
            self.logger.error(f"流式图执行失败: {graph_id}, 错误: {e}")
            yield GraphStreamEvent(
                event_type="error",
                data={
                    "error": str(e),
                    "final_response": f"执行失败: {str(e)}",
                    "context": kwargs
                }
            )
    
    def _serialize_node_data(self, node_data: Dict[str, Any]) -> Dict[str, Any]:
        """序列化节点数据，处理不可序列化的对象"""
        serialized = {}
        
        for key, value in node_data.items():
            try:
                if key == "messages":
                    # 序列化消息列表
                    serialized[key] = [str(msg) for msg in value] if value else []
                elif isinstance(value, (str, int, float, bool, type(None))):
                    serialized[key] = value
                elif isinstance(value, (list, tuple)):
                    serialized[key] = [str(item) for item in value]
                elif isinstance(value, dict):
                    serialized[key] = {k: str(v) for k, v in value.items()}
                else:
                    serialized[key] = str(value)
            except Exception as e:
                self.logger.debug(f"序列化节点数据时出错，键: {key}, 错误: {e}")
                serialized[key] = f"<无法序列化: {type(value).__name__}>"
        
        return serialized
    
    def get_graph_info(self, graph_id: str) -> Optional[Dict[str, Any]]:
        """
        获取图信息
        
        Args:
            graph_id: 图ID
            
        Returns:
            图信息
        """
        metadata = self.registry.get_metadata(graph_id)
        if metadata and "graph_info" in metadata:
            return metadata["graph_info"]
        return None
    
    def list_graphs(self) -> Dict[str, Dict[str, Any]]:
        """
        列出所有图
        
        Returns:
            图列表信息
        """
        graphs_info = {}
        
        for graph_id in self.registry.list_graphs():
            protocol = self.registry.get_protocol(graph_id)
            metadata = self.registry.get_metadata(graph_id)
            
            graph_info = {
                "id": graph_id,
                "status": "registered"
            }
            
            if protocol:
                graph_info.update({
                    "name": protocol.protocol.name,
                    "version": protocol.protocol.version,
                    "description": protocol.protocol.description,
                    "workflow_name": protocol.workflow.name,
                    "nodes_count": len(protocol.workflow.nodes),
                    "edges_count": len(protocol.workflow.edges),
                    "agents_count": len(protocol.agents)
                })
            
            if metadata:
                graph_info.update({
                    "created_at": metadata.get("created_at"),
                    "source_file": metadata.get("source_file"),
                    "source_type": metadata.get("source_type", "file")
                })
            
            graphs_info[graph_id] = graph_info
        
        return graphs_info
    
    def remove_graph(self, graph_id: str) -> bool:
        """
        移除图
        
        Args:
            graph_id: 图ID
            
        Returns:
            是否成功移除
        """
        self.logger.info(f"移除图: {graph_id}")
        success = self.registry.remove(graph_id)
        
        if success:
            self.logger.info(f"图移除成功: {graph_id}")
        else:
            self.logger.warning(f"图不存在，无法移除: {graph_id}")
        
        return success
    
    def clear_graphs(self) -> None:
        """清空所有图"""
        self.logger.info("清空所有图")
        self.registry.clear()
    
    def validate_protocol_file(self, file_path: Union[str, Path]) -> List[str]:
        """
        验证协议文件
        
        Args:
            file_path: 协议文件路径
            
        Returns:
            验证错误列表（空列表表示验证通过）
        """
        try:
            protocol = self.builder.parser.parse_from_file(file_path)
            return self.builder.parser.validate_protocol(protocol)
        except Exception as e:
            return [f"协议解析失败: {str(e)}"]
    
    def _get_current_time(self) -> str:
        """获取当前时间"""
        import datetime
        return datetime.datetime.now().isoformat()


# 全局管理器实例
_global_manager: Optional[GraphManager] = None


def get_graph_manager() -> GraphManager:
    """获取全局图管理器实例"""
    global _global_manager
    if _global_manager is None:
        _global_manager = GraphManager()
    return _global_manager


__all__ = [
    "GraphRegistry",
    "GraphManager",
    "get_graph_manager"
] 