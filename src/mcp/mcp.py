"""
KaFlow-Py MCP 模块

基于 MCP (Model Context Protocol) 的工具加载和管理模块，支持：
- stdio 和 sse 两种连接方式
- 异步工具加载
- 超时控制和错误处理
- 统一的请求响应模型

Author: DevYK
微信公众号: DevYK
Email: yang1001yk@gmail.com
Github: https://github.com/yangkun19921001
"""

import logging
from datetime import timedelta
from typing import Any, Dict, List, Optional, Union

from pydantic import BaseModel, Field
from fastapi import HTTPException
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client
from mcp.client.sse import sse_client

logger = logging.getLogger(__name__)


class MCPServerConfig(BaseModel):
    """MCP 服务器配置模型"""
    
    transport: str = Field(
        ..., description="MCP 服务器连接类型 (stdio 或 sse)"
    )
    command: Optional[str] = Field(
        None, description="执行命令 (stdio 类型必需)"
    )
    args: Optional[List[str]] = Field(
        None, description="命令参数 (stdio 类型)"
    )
    url: Optional[str] = Field(
        None, description="SSE 服务器 URL (sse 类型必需)"
    )
    env: Optional[Dict[str, str]] = Field(
        None, description="环境变量"
    )
    timeout_seconds: Optional[int] = Field(
        60, description="操作超时时间（秒）"
    )


class MCPServerMetadata(BaseModel):
    """MCP 服务器元数据响应模型"""
    
    transport: str = Field(
        ..., description="MCP 服务器连接类型"
    )
    command: Optional[str] = Field(
        None, description="执行命令"
    )
    args: Optional[List[str]] = Field(
        None, description="命令参数"
    )
    url: Optional[str] = Field(
        None, description="SSE 服务器 URL"
    )
    env: Optional[Dict[str, str]] = Field(
        None, description="环境变量"
    )
    tools: List[Dict[str, Any]] = Field(
        default_factory=list, description="可用工具列表"
    )
    status: str = Field(
        "unknown", description="服务器状态"
    )


class MCPToolInfo(BaseModel):
    """MCP 工具信息模型"""
    
    name: str = Field(..., description="工具名称")
    description: Optional[str] = Field(None, description="工具描述")
    input_schema: Optional[Dict[str, Any]] = Field(None, description="输入参数模式")
    
    
class MCPClient:
    """MCP 客户端封装类"""
    
    def __init__(self, config: MCPServerConfig):
        """
        初始化 MCP 客户端
        
        Args:
            config: MCP 服务器配置
        """
        self.config = config
        self._validate_config()
    
    def _validate_config(self) -> None:
        """验证配置参数"""
        if self.config.transport == "stdio" and not self.config.command:
            raise ValueError("stdio 类型需要提供 command 参数")
        
        if self.config.transport == "sse" and not self.config.url:
            raise ValueError("sse 类型需要提供 url 参数")
        
        if self.config.transport not in ["stdio", "sse"]:
            raise ValueError(f"不支持的传输类型: {self.config.transport}")
    
    async def _get_tools_from_session(
        self, 
        client_context_manager: Any, 
        timeout_seconds: int = 10
    ) -> List[Dict[str, Any]]:
        """
        从客户端会话获取工具列表
        
        Args:
            client_context_manager: 客户端上下文管理器
            timeout_seconds: 读取超时时间
            
        Returns:
            工具列表
            
        Raises:
            Exception: 处理过程中的错误
        """
        try:
            async with client_context_manager as (read, write):
                async with ClientSession(
                    read, write, 
                    read_timeout_seconds=timedelta(seconds=timeout_seconds)
                ) as session:
                    # 初始化连接
                    await session.initialize()
                    
                    # 获取可用工具
                    listed_tools = await session.list_tools()
                    
                    # 转换工具格式
                    tools = []
                    for tool in listed_tools.tools:
                        # 处理 input_schema，可能是字典或对象
                        input_schema = None
                        if tool.inputSchema:
                            if hasattr(tool.inputSchema, 'model_dump'):
                                input_schema = tool.inputSchema.model_dump()
                            elif isinstance(tool.inputSchema, dict):
                                input_schema = tool.inputSchema
                            else:
                                input_schema = dict(tool.inputSchema) if tool.inputSchema else None
                        
                        tool_info = {
                            "name": tool.name,
                            "description": tool.description,
                            "input_schema": input_schema
                        }
                        tools.append(tool_info)
                    
                    return tools
                    
        except Exception as e:
            logger.error(f"获取工具列表失败: {str(e)}")
            raise
    
    async def load_tools(self) -> List[Dict[str, Any]]:
        """
        加载 MCP 服务器工具
        
        Returns:
            工具列表
            
        Raises:
            HTTPException: 加载工具时的错误
        """
        try:
            timeout_seconds = self.config.timeout_seconds or 60
            
            if self.config.transport == "stdio":
                server_params = StdioServerParameters(
                    command=self.config.command,
                    args=self.config.args or [],
                    env=self.config.env or {}
                )
                
                return await self._get_tools_from_session(
                    stdio_client(server_params), 
                    timeout_seconds
                )
            
            elif self.config.transport == "sse":
                return await self._get_tools_from_session(
                    sse_client(url=self.config.url), 
                    timeout_seconds
                )
            
        except Exception as e:
            if isinstance(e, HTTPException):
                raise
            
            logger.exception(f"加载 MCP 工具失败: {str(e)}")
            raise HTTPException(
                status_code=500, 
                detail=f"加载 MCP 工具失败: {str(e)}"
            )
    
    async def call_tool(
        self, 
        tool_name: str, 
        arguments: Dict[str, Any]
    ) -> Any:
        """
        调用 MCP 工具
        
        Args:
            tool_name: 工具名称
            arguments: 工具参数
            
        Returns:
            工具执行结果
            
        Raises:
            Exception: 工具调用失败
        """
        try:
            timeout_seconds = self.config.timeout_seconds or 60
            
            if self.config.transport == "stdio":
                server_params = StdioServerParameters(
                    command=self.config.command,
                    args=self.config.args or [],
                    env=self.config.env or {}
                )
                
                return await self._call_tool_from_session(
                    stdio_client(server_params), 
                    tool_name,
                    arguments,
                    timeout_seconds
                )
            
            elif self.config.transport == "sse":
                return await self._call_tool_from_session(
                    sse_client(url=self.config.url), 
                    tool_name,
                    arguments,
                    timeout_seconds
                )
            
        except Exception as e:
            logger.exception(f"调用工具 {tool_name} 失败: {str(e)}")
            raise HTTPException(
                status_code=500, 
                detail=f"调用工具 {tool_name} 失败: {str(e)}"
            )
    
    async def _call_tool_from_session(
        self, 
        client_context_manager: Any, 
        tool_name: str,
        arguments: Dict[str, Any],
        timeout_seconds: int = 10
    ) -> Any:
        """
        从客户端会话调用工具
        
        Args:
            client_context_manager: 客户端上下文管理器
            tool_name: 工具名称
            arguments: 工具参数
            timeout_seconds: 超时时间
            
        Returns:
            工具执行结果
            
        Raises:
            Exception: 调用过程中的错误
        """
        try:
            async with client_context_manager as (read, write):
                async with ClientSession(
                    read, write, 
                    read_timeout_seconds=timedelta(seconds=timeout_seconds)
                ) as session:
                    # 初始化连接
                    await session.initialize()
                    
                    # 调用工具
                    result = await session.call_tool(tool_name, arguments)
                    
                    # 处理结果
                    if hasattr(result, 'content'):
                        # 如果结果有 content 属性
                        if hasattr(result.content, 'model_dump'):
                            return result.content.model_dump()
                        elif isinstance(result.content, list):
                            # 处理内容列表
                            content_list = []
                            for item in result.content:
                                if hasattr(item, 'model_dump'):
                                    content_list.append(item.model_dump())
                                elif hasattr(item, 'text'):
                                    content_list.append(item.text)
                                else:
                                    content_list.append(str(item))
                            return content_list
                        else:
                            return result.content
                    else:
                        # 直接返回结果
                        if hasattr(result, 'model_dump'):
                            return result.model_dump()
                        else:
                            return str(result)
                    
        except Exception as e:
            logger.error(f"调用工具 {tool_name} 失败: {str(e)}")
            raise

    async def get_server_metadata(self) -> MCPServerMetadata:
        """
        获取服务器元数据
        
        Returns:
            服务器元数据
        """
        try:
            tools = await self.load_tools()
            
            return MCPServerMetadata(
                transport=self.config.transport,
                command=self.config.command,
                args=self.config.args,
                url=self.config.url,
                env=self.config.env,
                tools=tools,
                status="connected"
            )
            
        except Exception as e:
            logger.error(f"获取服务器元数据失败: {str(e)}")
            
            return MCPServerMetadata(
                transport=self.config.transport,
                command=self.config.command,
                args=self.config.args,
                url=self.config.url,
                env=self.config.env,
                tools=[],
                status="error"
            )


class MCPManager:
    """MCP 管理器"""
    
    def __init__(self):
        """初始化 MCP 管理器"""
        self._clients: Dict[str, MCPClient] = {}
    
    def add_server(self, name: str, config: MCPServerConfig) -> None:
        """
        添加 MCP 服务器
        
        Args:
            name: 服务器名称
            config: 服务器配置
        """
        self._clients[name] = MCPClient(config)
    
    def remove_server(self, name: str) -> bool:
        """
        移除 MCP 服务器
        
        Args:
            name: 服务器名称
            
        Returns:
            是否成功移除
        """
        if name in self._clients:
            del self._clients[name]
            return True
        return False
    
    def get_client(self, name: str) -> Optional[MCPClient]:
        """
        获取 MCP 客户端
        
        Args:
            name: 服务器名称
            
        Returns:
            MCP 客户端实例
        """
        return self._clients.get(name)
    
    def list_servers(self) -> List[str]:
        """
        获取所有服务器名称
        
        Returns:
            服务器名称列表
        """
        return list(self._clients.keys())
    
    async def load_all_tools(self) -> Dict[str, List[Dict[str, Any]]]:
        """
        加载所有服务器的工具
        
        Returns:
            服务器名称到工具列表的映射
        """
        results = {}
        
        for name, client in self._clients.items():
            try:
                tools = await client.load_tools()
                results[name] = tools
            except Exception as e:
                logger.error(f"加载服务器 {name} 的工具失败: {str(e)}")
                results[name] = []
        
        return results
    
    async def get_all_metadata(self) -> Dict[str, MCPServerMetadata]:
        """
        获取所有服务器的元数据
        
        Returns:
            服务器名称到元数据的映射
        """
        results = {}
        
        for name, client in self._clients.items():
            try:
                metadata = await client.get_server_metadata()
                results[name] = metadata
            except Exception as e:
                logger.error(f"获取服务器 {name} 的元数据失败: {str(e)}")
                results[name] = MCPServerMetadata(
                    transport="unknown",
                    tools=[],
                    status="error"
                )
        
        return results


# 便捷函数
async def load_mcp_tools(
    server_type: str,
    command: Optional[str] = None,
    args: Optional[List[str]] = None,
    url: Optional[str] = None,
    env: Optional[Dict[str, str]] = None,
    timeout_seconds: int = 60
) -> List[Dict[str, Any]]:
    """
    便捷函数：加载 MCP 服务器工具
    
    Args:
        server_type: 服务器类型 (stdio 或 sse)
        command: 执行命令 (stdio 类型)
        args: 命令参数 (stdio 类型)
        url: SSE 服务器 URL (sse 类型)
        env: 环境变量
        timeout_seconds: 超时时间
        
    Returns:
        工具列表
        
    Raises:
        HTTPException: 加载失败时的错误
    """
    config = MCPServerConfig(
        transport=server_type,
        command=command,
        args=args,
        url=url,
        env=env,
        timeout_seconds=timeout_seconds
    )
    
    client = MCPClient(config)
    return await client.load_tools()


def create_mcp_config(
    transport: str,
    command: Optional[str] = None,
    args: Optional[List[str]] = None,
    url: Optional[str] = None,
    env: Optional[Dict[str, str]] = None,
    timeout_seconds: int = 60
) -> MCPServerConfig:
    """
    便捷函数：创建 MCP 服务器配置
    
    Args:
        transport: 传输类型
        command: 执行命令
        args: 命令参数
        url: SSE 服务器 URL
        env: 环境变量
        timeout_seconds: 超时时间
        
    Returns:
        MCP 服务器配置
    """
    return MCPServerConfig(
        transport=transport,
        command=command,
        args=args,
        url=url,
        env=env,
        timeout_seconds=timeout_seconds
    )


# 全局 MCP 管理器实例
_global_mcp_manager = None


def get_mcp_manager() -> MCPManager:
    """
    获取全局 MCP 管理器实例
    
    Returns:
        MCP 管理器实例
    """
    global _global_mcp_manager
    if _global_mcp_manager is None:
        _global_mcp_manager = MCPManager()
    return _global_mcp_manager


__all__ = [
    "MCPServerConfig",
    "MCPServerMetadata", 
    "MCPToolInfo",
    "MCPClient",
    "MCPManager",
    "load_mcp_tools",
    "create_mcp_config",
    "get_mcp_manager"
] 