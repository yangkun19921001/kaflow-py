"""
KaFlow-Py 节点工厂

根据协议配置创建 LangGraph 节点函数

Author: DevYK
WeChat: DevYK
Email: yang1001yk@gmail.com
Github: https://github.com/yangkun19921001
"""

from typing import Dict, Any, List, Callable, TypedDict, Optional
from abc import ABC, abstractmethod

from langchain_core.messages import BaseMessage, HumanMessage, AIMessage
from langgraph.graph import END

from .protocol_parser import WorkflowNode, AgentInfo, ParsedProtocol
from ...agents import create_agent, AgentConfig, AgentType
from ...llms import LLMConfig, get_llm
from ...tools import file_reader, file_writer, system_info, calculator, current_time
from ...mcp import MCPClient, create_mcp_config
from ...utils.logger import get_logger

logger = get_logger(__name__)


class GraphState(TypedDict):
    """LangGraph 状态定义"""
    messages: List[BaseMessage]
    user_input: str
    current_step: str
    tool_results: Dict[str, Any]
    final_response: str
    context: Dict[str, Any]
    node_outputs: Dict[str, Any]  # 存储各个节点的输出


class NodeFunction:
    """节点函数包装器"""
    
    def __init__(self, func: Callable, name: str, node_type: str):
        self.func = func
        self.name = name
        self.node_type = node_type
    
    def __call__(self, state: GraphState) -> GraphState:
        import asyncio
        import inspect
        
        if inspect.iscoroutinefunction(self.func):
            # 如果是异步函数，在同步上下文中运行
            try:
                loop = asyncio.get_event_loop()
                if loop.is_running():
                    # 如果已经在事件循环中，创建任务
                    import concurrent.futures
                    with concurrent.futures.ThreadPoolExecutor() as executor:
                        future = executor.submit(asyncio.run, self.func(state))
                        return future.result()
                else:
                    return loop.run_until_complete(self.func(state))
            except RuntimeError:
                # 如果没有事件循环，创建新的
                return asyncio.run(self.func(state))
        else:
            return self.func(state)


class BaseNodeBuilder(ABC):
    """节点构建器基类"""
    
    def __init__(self, protocol: ParsedProtocol):
        self.protocol = protocol
        self.logger = get_logger(self.__class__.__name__)
    
    @abstractmethod
    def can_build(self, node: WorkflowNode) -> bool:
        """检查是否可以构建此类型的节点"""
        pass
    
    @abstractmethod
    def build(self, node: WorkflowNode) -> NodeFunction:
        """构建节点函数"""
        pass


class StartNodeBuilder(BaseNodeBuilder):
    """开始节点构建器"""
    
    def can_build(self, node: WorkflowNode) -> bool:
        return node.type == 'start'
    
    def build(self, node: WorkflowNode) -> NodeFunction:
        def start_node(state: GraphState) -> GraphState:
            self.logger.info(f"执行开始节点: {node.name}")
            
            # 初始化状态
            if not state.get("messages") and state.get("user_input"):
                state["messages"] = [HumanMessage(content=state["user_input"])]
            
            state["current_step"] = f"started:{node.name}"
            state["node_outputs"][node.name] = {
                "status": "completed",
                "outputs": {"user_input": state.get("user_input", "")}
            }
            
            self.logger.debug(f"开始节点 {node.name} 执行完成")
            return state
        
        return NodeFunction(start_node, node.name, node.type)


class EndNodeBuilder(BaseNodeBuilder):
    """结束节点构建器"""
    
    def can_build(self, node: WorkflowNode) -> bool:
        return node.type == 'end'
    
    def build(self, node: WorkflowNode) -> NodeFunction:
        def end_node(state: GraphState) -> GraphState:
            self.logger.info(f"执行结束节点: {node.name}")
            
            state["current_step"] = f"completed:{node.name}"
            
            # 收集最终结果
            final_result = {
                "final_response": state.get("final_response", ""),
                "tool_results": state.get("tool_results", {}),
                "node_outputs": state.get("node_outputs", {})
            }
            
            state["node_outputs"][node.name] = {
                "status": "completed",
                "outputs": final_result
            }
            
            self.logger.info(f"结束节点 {node.name} 执行完成")
            return state
        
        return NodeFunction(end_node, node.name, node.type)


class AgentNodeBuilder(BaseNodeBuilder):
    """Agent 节点构建器"""
    
    def can_build(self, node: WorkflowNode) -> bool:
        return node.type == 'agent'
    
    def build(self, node: WorkflowNode) -> NodeFunction:
        # 获取 Agent 配置
        if not node.agent_ref or node.agent_ref not in self.protocol.agents:
            raise ValueError(f"节点 {node.name} 缺少有效的 agent_ref")
        
        agent_info = self.protocol.agents[node.agent_ref]
        
        async def agent_node(state: GraphState) -> GraphState:
            self.logger.info(f"执行 Agent 节点: {node.name} (Agent: {agent_info.name})")
            
            try:
                # 构建 LLM 配置
                llm_config_data = self._build_llm_config(agent_info)
                llm_config = LLMConfig(**llm_config_data)
                
                # 构建工具列表
                tools = self._build_tools(agent_info.tools)
                
                # 构建 MCP 工具
                mcp_tools = await self._build_mcp_tools(agent_info.mcp_servers)
                tools.extend(mcp_tools)
                
                self.logger.info(f"总工具数量: {len(tools)}, 其中 MCP 工具: {len(mcp_tools)}")
                
                # 确定 Agent 类型
                agent_type = self._map_agent_type(agent_info.type)
                
                # 构建 Agent 配置
                agent_config = AgentConfig(
                    name=agent_info.name,
                    agent_type=agent_type,
                    llm_config=llm_config,
                    system_prompt=agent_info.system_prompt or "",
                    tools=tools
                )
                
                # 打印工具信息用于调试
                if tools:
                    self.logger.info(f"传递给 Agent 的工具:")
                    for i, tool in enumerate(tools):
                        tool_name = getattr(tool, 'name', 'unknown')
                        tool_desc = getattr(tool, 'description', 'no description')
                        self.logger.info(f"  {i+1}. {tool_name}: {tool_desc}")
                else:
                    self.logger.warning("没有工具传递给 Agent")
                
                # 创建 Agent
                agent = create_agent(agent_config)
                self.logger.debug(f"Agent {agent_info.name} 创建成功: {type(agent)}")
                
                # 准备输入
                input_text = self._extract_input_text(state, node)
                
                # 执行 Agent - 使用异步调用以支持 MCP 工具
                if agent_type == AgentType.REACT_AGENT:
                    # ReAct Agent 使用消息格式
                    if not state.get("messages"):
                        state["messages"] = [HumanMessage(content=input_text)]
                    
                    # 使用异步调用以支持 MCP 工具
                    self.logger.debug("🔧 使用异步调用执行 ReAct Agent")
                    response = await agent.ainvoke({"messages": state["messages"]})
                    
                    # 处理响应
                    if isinstance(response, dict) and 'messages' in response:
                        state["messages"] = response['messages']
                        final_response = self._extract_final_response(response['messages'])
                    else:
                        final_response = str(response)
                    
                else:
                    # 普通 Agent - 使用异步调用
                    self.logger.debug("🔧 使用异步调用执行普通 Agent")
                    response = await agent.ainvoke(input_text)
                    
                    if hasattr(response, 'content'):
                        final_response = response.content
                    else:
                        final_response = str(response)
                    
                    # 更新消息历史
                    if not state.get("messages"):
                        state["messages"] = []
                    
                    state["messages"].extend([
                        HumanMessage(content=input_text),
                        AIMessage(content=final_response)
                    ])
                
                # 更新状态
                state["final_response"] = final_response
                state["current_step"] = f"agent_completed:{node.name}"
                
                # 存储节点输出
                state["node_outputs"][node.name] = {
                    "status": "completed",
                    "outputs": {
                        "response": final_response,
                        "agent_name": agent_info.name,
                        "agent_type": agent_info.type
                    }
                }
                
                self.logger.info(f"Agent 节点 {node.name} 执行完成，响应长度: {len(final_response)}")
                
            except Exception as e:
                self.logger.error(f"Agent 节点 {node.name} 执行失败: {e}")
                error_message = f"Agent 执行出错: {str(e)}"
                
                state["final_response"] = error_message
                state["current_step"] = f"agent_failed:{node.name}"
                state["node_outputs"][node.name] = {
                    "status": "failed",
                    "error": str(e),
                    "outputs": {"response": error_message}
                }
                
                # 添加错误消息
                if not state.get("messages"):
                    state["messages"] = []
                state["messages"].append(AIMessage(content=error_message))
            
            return state
        
        return NodeFunction(agent_node, node.name, node.type)
    
    def _build_llm_config(self, agent_info: AgentInfo) -> Dict[str, Any]:
        """构建 LLM 配置"""
        llm_config = {}
        
        # 优先使用 Agent 专用配置
        if agent_info.llm:
            llm_config = agent_info.llm.copy()
        elif self.protocol.llm_config:
            llm_config = self.protocol.llm_config.copy()
        
        # 确保必要字段存在
        if 'provider' not in llm_config:
            llm_config['provider'] = 'deepseek'
        if 'max_retries' not in llm_config:
            llm_config['max_retries'] = 3
        if 'verify_ssl' not in llm_config:
            llm_config['verify_ssl'] = True
        
        return llm_config
    
    def _build_tools(self, tools_config: List[Dict[str, Any]]) -> List[Callable]:
        """构建工具列表"""
        tools = []
        tool_mapping = {
            "file_reader": file_reader,
            "file_writer": file_writer,
            "system_info": system_info,
            "calculator": calculator,
            "current_time": current_time
        }
        
        for tool_config in tools_config:
            tool_name = tool_config.get("name") if isinstance(tool_config, dict) else tool_config
            if tool_name in tool_mapping:
                tools.append(tool_mapping[tool_name])
                self.logger.debug(f"加载工具: {tool_name}")
            else:
                self.logger.warning(f"未知工具: {tool_name}")
        
        return tools
    
    async def _build_mcp_tools(self, mcp_servers_config: List[Dict[str, Any]]) -> List[Callable]:
        """构建 MCP 工具列表 - 使用 langchain_mcp_adapters"""
        mcp_tools = []
        
        if not mcp_servers_config:
            return mcp_tools
        
        try:
            # 导入 langchain_mcp_adapters
            from langchain_mcp_adapters.client import MultiServerMCPClient
            self.logger.info("✅ 成功导入 langchain_mcp_adapters，使用新的 MCP 实现")
            
            # 构建服务器配置
            mcp_servers = {}
            for server_config in mcp_servers_config:
                if not server_config.get('enabled', True):
                    continue
                
                server_name = server_config.get('name', 'unknown')
                self.logger.info(f"连接 MCP 服务器: {server_name}")
                
                # 转换配置格式为 langchain_mcp_adapters 兼容格式
                if server_config.get('transport') == 'sse':
                    mcp_servers[server_name] = {
                        "transport": "sse",
                        "url": server_config.get('url')
                    }
                elif server_config.get('transport') == 'stdio':
                    mcp_servers[server_name] = {
                        "transport": "stdio",
                        "command": server_config.get('command'),
                        "args": server_config.get('args', [])
                    }
            
            if not mcp_servers:
                self.logger.warning("没有有效的 MCP 服务器配置")
                return mcp_tools
            
            # 创建 MCP 客户端并获取工具
            client = MultiServerMCPClient(mcp_servers)
            available_tools = await client.get_tools()
            
            if available_tools:
                self.logger.info(f"从 MCP 服务器加载了 {len(available_tools)} 个工具")
                
                # 为异步 MCP 工具创建同步包装器
                for tool in available_tools:
                    tool_name = getattr(tool, 'name', 'unknown')
                    self.logger.debug(f"加载 MCP 工具: {tool_name}")
                    
                    # MCP 工具虽然有 invoke 方法但实际不支持同步调用
                    # LangGraph ReAct Agent 能够正确处理异步工具，所以直接使用
                    self.logger.debug(f"加载 MCP 工具 {tool_name}，LangGraph 将自动处理异步调用")
                    mcp_tools.append(tool)
            else:
                self.logger.warning("MCP 服务器没有提供工具")
                
        except ImportError as import_error:
            self.logger.error(f"❌ 缺少 langchain_mcp_adapters 依赖: {import_error}，回退到原始实现")
            # 回退到原来的实现
            return await self._build_mcp_tools_fallback(mcp_servers_config)
        except Exception as e:
            self.logger.error(f"连接 MCP 服务器失败: {e}")
            # 继续处理，不中断整个流程
        
        return mcp_tools
    
    def _create_sync_wrapper_for_async_tool(self, async_tool) -> Callable:
        """为异步 MCP 工具创建同步包装器"""
        from langchain_core.tools import tool
        import asyncio
        
        # 获取工具信息
        tool_name = getattr(async_tool, 'name', 'unknown_tool')
        tool_description = getattr(async_tool, 'description', f'Sync wrapper for {tool_name}')
        
        @tool(name=tool_name, description=tool_description)
        def sync_mcp_tool(**kwargs) -> str:
            """同步 MCP 工具包装器"""
            try:
                self.logger.debug(f"🔧 同步调用异步工具: {tool_name}, 参数: {kwargs}")
                
                # 在同步环境中安全运行异步代码
                try:
                    # 检查是否已经在事件循环中
                    loop = asyncio.get_event_loop()
                    if loop.is_running():
                        # 如果已经在事件循环中，使用 ThreadPoolExecutor
                        import concurrent.futures
                        with concurrent.futures.ThreadPoolExecutor() as executor:
                            future = executor.submit(asyncio.run, async_tool.ainvoke(kwargs))
                            result = future.result(timeout=60)  # 60秒超时
                    else:
                        # 如果没有运行的事件循环，直接使用 run_until_complete
                        result = loop.run_until_complete(async_tool.ainvoke(kwargs))
                except RuntimeError:
                    # 如果没有事件循环，创建新的
                    result = asyncio.run(async_tool.ainvoke(kwargs))
                
                self.logger.debug(f"✅ 工具 {tool_name} 执行成功: {str(result)[:200]}...")
                
                # 处理返回结果
                if isinstance(result, dict):
                    return str(result)
                elif isinstance(result, (list, tuple)):
                    return str(result)
                else:
                    return str(result)
                    
            except Exception as e:
                error_msg = f"MCP 工具 {tool_name} 调用失败: {str(e)}"
                self.logger.error(error_msg)
                return error_msg
        
        return sync_mcp_tool
    
    async def _build_mcp_tools_fallback(self, mcp_servers_config: List[Dict[str, Any]]) -> List[Callable]:
        """原始 MCP 工具构建方法（回退用）"""
        mcp_tools = []
        
        for server_config in mcp_servers_config:
            if not server_config.get('enabled', True):
                continue
                
            try:
                self.logger.info(f"连接 MCP 服务器: {server_config.get('name', 'unknown')}")
                
                # 创建 MCP 客户端配置
                mcp_config = create_mcp_config(
                    transport=server_config.get('transport', 'sse'),
                    url=server_config.get('url'),
                    timeout_seconds=server_config.get('timeout_seconds', 30)
                )
                
                # 创建 MCP 客户端
                client = MCPClient(mcp_config)
                
                # 获取服务器工具
                metadata = await client.get_server_metadata()
                
                if metadata and metadata.tools:
                    self.logger.info(f"从 MCP 服务器 {server_config.get('name')} 加载了 {len(metadata.tools)} 个工具")
                    
                    # 为每个 MCP 工具创建包装函数
                    for tool_info in metadata.tools:
                        tool_name = tool_info.get('name')
                        if tool_name:
                            # 使用 LangChain 的 @tool 装饰器创建工具
                            from langchain_core.tools import tool
                            
                            def create_mcp_tool(client_ref, tool_name_ref, tool_description, tool_schema):
                                @tool(description=tool_description)
                                def mcp_tool_wrapper(**kwargs) -> str:
                                    """MCP 工具包装函数"""
                                    try:
                                        # 同步调用异步函数
                                        import asyncio
                                        try:
                                            loop = asyncio.get_event_loop()
                                            if loop.is_running():
                                                # 如果已经在事件循环中，使用 run_in_executor
                                                import concurrent.futures
                                                with concurrent.futures.ThreadPoolExecutor() as executor:
                                                    future = executor.submit(asyncio.run, client_ref.call_tool(tool_name_ref, kwargs))
                                                    result = future.result()
                                            else:
                                                result = loop.run_until_complete(client_ref.call_tool(tool_name_ref, kwargs))
                                        except RuntimeError:
                                            # 如果没有事件循环，创建新的
                                            result = asyncio.run(client_ref.call_tool(tool_name_ref, kwargs))
                                        
                                        # 处理返回结果
                                        if isinstance(result, dict):
                                            return str(result)
                                        else:
                                            return str(result)
                                    except Exception as e:
                                        return f"MCP 工具调用失败: {str(e)}"
                                
                                return mcp_tool_wrapper
                            
                            tool_description = tool_info.get('description', f'MCP工具: {tool_name}')
                            tool_schema = tool_info.get('input_schema', {})
                            
                            mcp_tool = create_mcp_tool(client, tool_name, tool_description, tool_schema)
                            # 手动设置工具名称
                            mcp_tool.name = tool_name
                            mcp_tools.append(mcp_tool)
                            self.logger.debug(f"加载 MCP 工具: {tool_name}")
                else:
                    self.logger.warning(f"MCP 服务器 {server_config.get('name')} 没有提供工具")
                    
            except Exception as e:
                self.logger.error(f"连接 MCP 服务器失败: {server_config.get('name')}, 错误: {e}")
                # 继续处理其他服务器，不中断整个流程
                continue
        
        return mcp_tools
    
    def _map_agent_type(self, agent_type_str: str) -> AgentType:
        """映射 Agent 类型"""
        type_mapping = {
            "agent": AgentType.AGENT,
            "react_agent": AgentType.REACT_AGENT,
        }
        
        mapped_type = type_mapping.get(agent_type_str.lower(), AgentType.AGENT)
        self.logger.debug(f"映射 Agent 类型: {agent_type_str} -> {mapped_type}")
        return mapped_type
    
    def _extract_input_text(self, state: GraphState, node: WorkflowNode) -> str:
        """提取输入文本"""
        # 优先使用 user_input
        if state.get("user_input"):
            return state["user_input"]
        
        # 从消息历史中提取
        if state.get("messages"):
            last_human_msg = None
            for msg in reversed(state["messages"]):
                if isinstance(msg, HumanMessage):
                    last_human_msg = msg
                    break
            if last_human_msg:
                return last_human_msg.content
        
        # 从节点输入配置中提取
        for input_config in node.inputs:
            if input_config.get("source"):
                # TODO: 实现复杂的输入源解析
                pass
        
        return "请问有什么可以帮助您的吗？"
    
    def _extract_final_response(self, messages: List[BaseMessage]) -> str:
        """从消息列表中提取最终响应"""
        if not messages:
            return ""
        
        # 查找最后一个有内容的消息
        for msg in reversed(messages):
            if hasattr(msg, 'content') and msg.content and msg.content.strip():
                return msg.content
        
        # 如果没有找到，返回最后一个消息的字符串表示
        return str(messages[-1]) if messages else ""


class NodeFactory:
    """节点工厂"""
    
    def __init__(self, protocol: ParsedProtocol):
        self.protocol = protocol
        self.logger = get_logger(__name__)
        
        # 注册节点构建器
        self.builders = [
            StartNodeBuilder(protocol),
            EndNodeBuilder(protocol),
            AgentNodeBuilder(protocol),
        ]
    
    def create_node_function(self, node: WorkflowNode) -> NodeFunction:
        """
        创建节点函数
        
        Args:
            node: 工作流节点配置
            
        Returns:
            节点函数
        """
        self.logger.debug(f"创建节点函数: {node.name} (类型: {node.type})")
        
        for builder in self.builders:
            if builder.can_build(node):
                return builder.build(node)
        
        raise ValueError(f"不支持的节点类型: {node.type} (节点: {node.name})")
    
    def create_all_node_functions(self) -> Dict[str, NodeFunction]:
        """
        创建所有节点函数
        
        Returns:
            节点名称到节点函数的映射
        """
        node_functions = {}
        
        for node in self.protocol.workflow.nodes:
            node_func = self.create_node_function(node)
            node_functions[node.name] = node_func
        
        self.logger.info(f"创建了 {len(node_functions)} 个节点函数")
        return node_functions


__all__ = [
    "GraphState",
    "NodeFunction",
    "BaseNodeBuilder",
    "StartNodeBuilder",
    "EndNodeBuilder", 
    "AgentNodeBuilder",
    "NodeFactory"
] 