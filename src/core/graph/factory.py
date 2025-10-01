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
import asyncio

from langchain_core.messages import BaseMessage, HumanMessage, AIMessage
from langgraph.graph import END

from .parser import WorkflowNode, AgentInfo, ParsedProtocol
from .io_resolver import get_io_resolver
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
    _goto_node: Optional[str]  # 动态跳转目标节点（内部使用）


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
    
    def __init__(self, protocol: ParsedProtocol):
        super().__init__(protocol)
        self.io_resolver = get_io_resolver()
    
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

                # 获取 Loop 配置
                loop_config = agent_info.loop
                
                # 构建工具列表
                tools = self._build_tools(agent_info.tools)
                
                # 构建 MCP 工具
                mcp_tools = await self._build_mcp_tools(agent_info.mcp_servers)
                tools.extend(mcp_tools)
                
                self.logger.info(f"总工具数量: {len(tools)}, 其中 MCP 工具: {len(mcp_tools)}")
                
                # 确定 Agent 类型
                agent_type = self._map_agent_type(agent_info.type)
                
                # 构建 Agent 配置 - 转换 LoopInfo 为 LoopConfig
                from ...agents.config import LoopConfig as AgentLoopConfig
                agent_loop_config = AgentLoopConfig(
                    enable=loop_config.enable,
                    max_iterations=loop_config.max_iterations,
                    loop_delay=loop_config.loop_delay,
                    force_exit_keywords=loop_config.force_exit_keywords
                )
                
                agent_config = AgentConfig(
                    name=agent_info.name,
                    agent_type=agent_type,
                    llm_config=llm_config,
                    system_prompt=agent_info.system_prompt or "",
                    tools=tools,
                    loop_config=agent_loop_config 
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
                
                # 使用 IO 解析器准备输入
                resolved_inputs = self.io_resolver.resolve_inputs(node, state)
                input_text = self.io_resolver.build_agent_input(node, state, resolved_inputs)
                
                self.logger.info(f"解析了 {len(resolved_inputs)} 个输入字段: {list(resolved_inputs.keys())}")
                
                # 检查是否启用循环
                if loop_config.enable:
                    self.logger.info(f"🔄 启用循环执行，最大迭代次数: {loop_config.max_iterations}")
                    final_response, loop_count = await self._execute_agent_loop(
                        agent, agent_type, input_text, state, loop_config
                    )
                    
                    # 使用 IO 解析器存储输出
                    self.io_resolver.store_outputs(node, state, final_response)
                    
                    # 添加额外的元数据
                    if node.name in state["node_outputs"]:
                        state["node_outputs"][node.name]["status"] = "completed"
                        state["node_outputs"][node.name]["loop_count"] = loop_count
                        state["node_outputs"][node.name]["max_iterations"] = loop_config.max_iterations
                else:
                    # 单次执行 Agent
                    final_response = await self._execute_agent_single(
                        agent, agent_type, input_text, state
                    )
                    
                    # 使用 IO 解析器存储输出
                    self.io_resolver.store_outputs(node, state, final_response)
                    if node.name in state["node_outputs"]:
                        state["node_outputs"][node.name]["status"] = "completed"
                
                # 更新状态
                state["final_response"] = final_response
                state["current_step"] = f"agent_completed:{node.name}"
                
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

    async def _execute_agent_loop(self, agent, agent_type: AgentType, input_text: str, state: GraphState, loop_config) -> tuple[str, int]:
        """执行 Agent 循环
        
        Args:
            agent: Agent 实例
            agent_type: Agent 类型
            input_text: 输入文本
            state: 图状态
            loop_config: 循环配置
            
        Returns:
            tuple[final_response, loop_count]: 最终响应和循环次数
        """
        import asyncio
        
        self.logger.info("🔄 开始循环执行...")
        
        # 初始化消息历史
        if not state.get("messages"):
            state["messages"] = [HumanMessage(content=input_text)]
        
        messages = state["messages"]
        max_iterations = loop_config.max_iterations
        loop_count = 0
        
        while loop_count < max_iterations:
            loop_count += 1
            self.logger.info(f"🎯 执行循环 {loop_count}/{max_iterations}")
            
            try:
                # 执行一次 Agent 调用
                if agent_type == AgentType.REACT_AGENT:
                    # ReAct Agent 使用消息格式
                    response = await agent.ainvoke(
                        {"messages": messages}, 
                        config={"recursion_limit": max_iterations}
                    )
                    
                    if isinstance(response, dict) and 'messages' in response:
                        messages = response['messages']
                        latest_message = messages[-1] if messages else None
                    else:
                        # 如果响应格式不符合预期，创建 AI 消息
                        ai_message = AIMessage(content=str(response))
                        messages.append(ai_message)
                        latest_message = ai_message
                else:
                    # 普通 Agent
                    response = await agent.ainvoke(input_text)
                    
                    if hasattr(response, 'content'):
                        response_content = response.content
                    else:
                        response_content = str(response)
                    
                    # 更新消息历史
                    ai_message = AIMessage(content=response_content)
                    messages.append(ai_message)
                    latest_message = ai_message
                
                # 更新状态中的消息
                state["messages"] = messages
                
                # 第一次迭代：检查是否有工具调用
                if loop_count == 1 and loop_config.no_tool_goto:
                    has_tool_calls = self._check_has_tool_calls(messages)
                    if not has_tool_calls:
                        self.logger.info(f"🔀 第一次迭代无工具调用，跳转到节点: {loop_config.no_tool_goto}")
                        # 设置跳转标记到 state
                        state["_goto_node"] = loop_config.no_tool_goto
                        # 提取最终响应
                        final_response = self._extract_final_response(messages) if messages else "无工具调用"
                        return final_response, loop_count
                
                # 检查是否完成
                if latest_message and hasattr(latest_message, 'content'):
                    response_content = latest_message.content
                    
                    # 检查完成条件
                    if self._is_task_completed(response_content, loop_config.force_exit_keywords):
                        self.logger.info(f"🎉 检测到完成标志，循环在第 {loop_count} 次迭代后结束")
                        return response_content, loop_count
                
                self.logger.debug(f"✅ 循环 {loop_count} 执行成功")
                
                # 循环间隔（防止过快请求）
                if loop_count < max_iterations and loop_config.loop_delay and loop_config.loop_delay > 0:
                    await asyncio.sleep(loop_config.loop_delay)
                elif loop_count < max_iterations:
                    await asyncio.sleep(1)  # 默认间隔 1 秒
                
            except Exception as e:
                self.logger.error(f"❌ 循环 {loop_count} 执行失败: {e}")
                error_message = f"循环执行失败: {str(e)}"
                return error_message, loop_count
        
        # 达到最大循环次数
        self.logger.warning(f"⚠️ 达到最大循环次数 {max_iterations}")
        final_response = self._extract_final_response(messages) if messages else "达到最大循环次数"
        return final_response, loop_count
    
    async def _execute_agent_single(self, agent, agent_type: AgentType, input_text: str, state: GraphState) -> str:
        """单次执行 Agent
        
        Args:
            agent: Agent 实例
            agent_type: Agent 类型
            input_text: 输入文本
            state: 图状态
            
        Returns:
            str: Agent 响应
        """
        if agent_type == AgentType.REACT_AGENT:
            # ReAct Agent 使用消息格式
            if not state.get("messages"):
                state["messages"] = [HumanMessage(content=input_text)]
            
            self.logger.debug("🔧 使用异步调用执行 ReAct Agent")
            response = await agent.ainvoke({"messages": state["messages"]}, config={"recursion_limit": 50})
            
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
        
        return final_response
    
    def _check_has_tool_calls(self, messages: List) -> bool:
        """检查消息历史中是否有工具调用
        
        Args:
            messages: 消息历史列表
            
        Returns:
            bool: 是否有工具调用
        """
        for msg in messages:
            # 检查是否是 ToolMessage
            if msg.__class__.__name__ == 'ToolMessage':
                self.logger.debug(f"✅ 发现 ToolMessage: {msg}")
                return True
            
            # 检查 AIMessage 的 tool_calls 属性
            if hasattr(msg, 'tool_calls') and msg.tool_calls:
                self.logger.debug(f"✅ 发现 tool_calls: {msg.tool_calls}")
                return True
        
        self.logger.debug("❌ 未发现任何工具调用")
        return False
    
    def _is_task_completed(self, response_content: str, force_exit_keywords: List[str] = None) -> bool:
        """检查任务是否完成
        
        Args:
            response_content: AI 响应内容
            force_exit_keywords: 强制退出关键词列表
            
        Returns:
            bool: 是否完成
        """
        if not response_content:
            return False
        
        response_lower = response_content.lower()
        
        # 检查自定义退出关键词
        if force_exit_keywords:
            for keyword in force_exit_keywords:
                if keyword.lower() in response_lower:
                    self.logger.info(f"🎯 检测到自定义退出关键词: {keyword}")
                    return True
        
        # 明确的完成标志
        completion_indicators = [
            # 中文完成标志
            "【最终答案】", "【分析完成】", "【排查完成】", "【总结报告】",
            "最终答案：", "分析完成：", "排查完成：", "诊断结束：", "结论：",
            "## 最终答案", "## 分析完成", "## 排查完成", "## 总结报告",
            "任务完成", "排查结束", "分析结束", "诊断完成",
            
            # 英文完成标志
            "【final answer】", "【analysis complete】", "【diagnosis complete】",
            "final answer:", "analysis complete:", "diagnosis complete:", "conclusion:",
            "## final answer", "## analysis complete", "## conclusion",
            "task completed", "analysis finished", "diagnosis finished"
        ]
        
        # 检查明确标志
        for indicator in completion_indicators:
            if indicator in response_lower:
                self.logger.info(f"🎯 检测到完成标志: {indicator}")
                return True
        
        # 检查上下文完成标志
        return self._check_contextual_completion(response_lower)
    
    def _check_contextual_completion(self, response_lower: str) -> bool:
        """检查上下文完成标志"""
        if any(word in response_lower for word in ["完成", "结束", "finished", "completed"]):
            # 排除误报情况
            false_positives = [
                "未完成", "没有完成", "不完成", "未结束", "没有结束",
                "not completed", "not finished", "incomplete", "unfinished"
            ]
            
            if not any(fp in response_lower for fp in false_positives):
                # 检查上下文
                context_words = [
                    "排查完成", "分析完成", "诊断完成", "检查完成", "任务完成",
                    "已完成", "顺利完成", "成功完成",
                    "排查结束", "分析结束", "诊断结束",
                    "analysis completed", "diagnosis completed", "task completed",
                    "successfully completed", "check completed"
                ]
                
                if any(ctx in response_lower for ctx in context_words):
                    self.logger.info("🎯 检测到上下文完成标志")
                    return True
        
        return False

    def _parse_agent_output(self, output_text: str) -> Dict[str, Any]:
        """尝试解析 JSON 输出，如果成功则返回字典，否则返回空字典"""
        try:
            import json
            return json.loads(output_text)
        except json.JSONDecodeError:
            self.logger.warning(f"JSON 解析失败: {output_text}")
            return {}
        except Exception as e:
            self.logger.error(f"解析 JSON 输出失败: {e}")
            return {}


class ConditionNodeBuilder(BaseNodeBuilder):
    """条件节点构建器"""
    
    def can_build(self, node: WorkflowNode) -> bool:
        return node.type == "condition"
    
    def build(self, node: WorkflowNode) -> NodeFunction:
        """构建条件节点函数"""
        
        async def condition_node(state: GraphState) -> GraphState:
            """条件节点执行函数"""
            self.logger.debug(f"执行条件节点: {node.name}")
            
            # 获取条件配置
            conditions = getattr(node, 'conditions', {})
            if not conditions:
                self.logger.warning(f"条件节点 {node.name} 没有配置条件")
                return state
            
            # 评估每个条件
            condition_results = {}
            for condition_name, condition_expr in conditions.items():
                try:
                    # 简单的条件评估 - 支持基本的比较和逻辑操作
                    result = self._evaluate_condition(condition_expr, state)
                    condition_results[condition_name] = result
                    self.logger.debug(f"条件 {condition_name}: {condition_expr} -> {result}")
                except Exception as e:
                    self.logger.error(f"评估条件失败 {condition_name}: {e}")
                    condition_results[condition_name] = False
            
            # 将条件结果存储到状态中
            state["node_outputs"][node.name] = {
                "condition_results": condition_results,
                "node_type": "condition"
            }
            
            # 更新当前步骤
            state["current_step"] = node.name
            
            return state
        
        return NodeFunction(condition_node, node.name, node.type)
    
    def _evaluate_condition(self, condition_expr: str, state: GraphState) -> bool:
        """评估条件表达式"""
        try:
            # 获取上下文数据
            context = {
                'state': state,
                'node_outputs': state.get('node_outputs', {}),
                'context': state.get('context', {})
            }
            
            # 解析简单的条件表达式
            # 支持格式如: "intent_result.is_device_troubleshooting == true"
            if '==' in condition_expr:
                left, right = condition_expr.split('==', 1)
                left = left.strip()
                right = right.strip()
                
                # 获取左侧值
                left_value = self._get_value_from_path(left, state)
                
                # 解析右侧值
                if right.lower() == 'true':
                    right_value = True
                elif right.lower() == 'false':
                    right_value = False
                elif right.startswith('"') and right.endswith('"'):
                    right_value = right[1:-1]  # 字符串
                elif right.isdigit():
                    right_value = int(right)  # 整数
                else:
                    right_value = right  # 原始值
                
                return left_value == right_value
            
            elif '!=' in condition_expr:
                left, right = condition_expr.split('!=', 1)
                left = left.strip()
                right = right.strip()
                
                left_value = self._get_value_from_path(left, state)
                
                if right.lower() == 'true':
                    right_value = True
                elif right.lower() == 'false':
                    right_value = False
                elif right.startswith('"') and right.endswith('"'):
                    right_value = right[1:-1]
                else:
                    right_value = right
                
                return left_value != right_value
            
            # 支持 not 操作
            elif condition_expr.startswith('not '):
                inner_expr = condition_expr[4:].strip()
                return not self._evaluate_condition(inner_expr, state)
            
            # 直接布尔值路径
            else:
                return bool(self._get_value_from_path(condition_expr, state))
                
        except Exception as e:
            self.logger.error(f"条件评估失败: {condition_expr}, 错误: {e}")
            return False
    
    def _get_value_from_path(self, path: str, state: GraphState):
        """从路径获取值，如 'intent_result.is_device_troubleshooting'"""
        try:
            parts = path.split('.')
            
            # 从node_outputs中查找
            if len(parts) >= 2:
                node_name = parts[0]
                if node_name in state.get('node_outputs', {}):
                    value = state['node_outputs'][node_name]
                    
                    # 遍历剩余路径
                    for part in parts[1:]:
                        if isinstance(value, dict) and part in value:
                            value = value[part]
                        else:
                            return None
                    return value
            
            # 从context中查找
            if path in state.get('context', {}):
                return state['context'][path]
            
            # 从顶层状态中查找
            if path in state:
                return state[path]
            
            return None
            
        except Exception as e:
            self.logger.error(f"获取路径值失败: {path}, 错误: {e}")
            return None


class LoopNodeBuilder(BaseNodeBuilder):
    """循环节点构建器"""
    
    def can_build(self, node: WorkflowNode) -> bool:
        return node.type == "loop"
    
    def build(self, node: WorkflowNode) -> NodeFunction:
        """构建循环节点函数"""
        
        async def loop_node(state: GraphState) -> GraphState:
            """循环节点执行函数"""
            self.logger.debug(f"执行循环节点: {node.name}")
            
            # 获取循环配置
            loop_config = getattr(node, 'loop_config', {})
            items_path = loop_config.get('items', '')
            max_iterations = loop_config.get('max_iterations', 10)
            
            # 获取要循环的项目
            items = self._get_value_from_path(items_path, state) if items_path else []
            if not isinstance(items, list):
                items = []
            
            # 初始化循环状态
            loop_state = {
                "items": items,
                "current_index": 0,
                "max_iterations": max_iterations,
                "completed": False,
                "results": []
            }
            
            # 将循环状态存储到节点输出中
            state["node_outputs"][node.name] = {
                "loop_state": loop_state,
                "node_type": "loop"
            }
            
            state["current_step"] = node.name
            
            return state
        
        return NodeFunction(loop_node, node.name, node.type)
    
    def _get_value_from_path(self, path: str, state: GraphState):
        """从路径获取值"""
        try:
            parts = path.split('.')
            
            if len(parts) >= 2:
                node_name = parts[0]
                if node_name in state.get('node_outputs', {}):
                    value = state['node_outputs'][node_name]
                    
                    for part in parts[1:]:
                        if isinstance(value, dict) and part in value:
                            value = value[part]
                        else:
                            return None
                    return value
            
            if path in state.get('context', {}):
                return state['context'][path]
            
            if path in state:
                return state[path]
            
            return None
            
        except Exception as e:
            self.logger.error(f"获取路径值失败: {path}, 错误: {e}")
            return None


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
            ConditionNodeBuilder(protocol),
            LoopNodeBuilder(protocol),
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
    "ConditionNodeBuilder",
    "LoopNodeBuilder",
    "NodeFactory"
] 