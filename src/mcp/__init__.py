"""
KaFlow-Py MCP 模块

基于 MCP (Model Context Protocol) 的工具加载和管理模块，支持：
- stdio 和 sse 两种连接方式
- 异步工具加载和管理
- 多服务器支持
- 统一的配置和错误处理

Author: DevYK
WeChat: DevYK
Email: yang1001yk@gmail.com
Github: https://github.com/yangkun19921001
"""

from .mcp import (
    MCPServerConfig,
    MCPServerMetadata,
    MCPToolInfo,
    MCPClient,
    MCPManager,
    load_mcp_tools,
    create_mcp_config,
    get_mcp_manager
)

__version__ = "1.0.0"

__all__ = [
    # 配置模型
    "MCPServerConfig",
    "MCPServerMetadata",
    "MCPToolInfo",
    
    # 核心类
    "MCPClient",
    "MCPManager",
    
    # 便捷函数
    "load_mcp_tools",
    "create_mcp_config",
    "get_mcp_manager"
] 