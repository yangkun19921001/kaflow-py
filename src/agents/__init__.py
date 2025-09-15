"""
KaFlow-Py Agents 模块

基于 LangGraph 的 Agent 封装，支持：
- 通用 Agent 创建
- ReAct Agent（推理->执行->思考）
- 外部传参配置

Author: DevYK
WeChat: DevYK
Email: yang1001yk@gmail.com
Github: https://github.com/yangkun19921001
"""

# 核心 Agent 创建函数
from .agents import create_agent

# Agent 配置
from .config import (
    AgentConfig,
    AgentType,
    create_simple_agent_config,
    create_react_agent_config
)

# Agent 管理器
from .manager import AgentManager

# 异常处理
from .exceptions import (
    AgentError,
    AgentConfigError,
    AgentCreationError,
    AgentToolError,
    AgentPromptError
)

__version__ = "1.0.0"

__all__ = [
    # 核心函数
    "create_agent",
    
    # 配置
    "AgentConfig",
    "AgentType",
    "create_simple_agent_config",
    "create_react_agent_config",
    
    # 管理器
    "AgentManager",
    
    # 异常
    "AgentError",
    "AgentConfigError",
    "AgentCreationError",
    "AgentToolError",
    "AgentPromptError",
] 