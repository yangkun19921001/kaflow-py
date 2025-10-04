"""
KaFlow-Py Agents 核心 API

基于 LangGraph 的 Agent 创建函数，支持函数重载和外部传参配置。
参考 deer-flow 的代码风格，提供简洁易用的 API。

Author: DevYK
微信公众号: DevYK
Email: yang1001yk@gmail.com
Github: https://github.com/yangkun19921001
"""

from typing import Any

from .config import AgentConfig
from .manager import AgentManager


# 全局 AgentManager 实例
_global_manager = None
_manager_lock = __import__('threading').RLock()


def _get_manager() -> AgentManager:
    """获取全局 AgentManager 实例"""
    global _global_manager
    with _manager_lock:
        if _global_manager is None:
            _global_manager = AgentManager()
        return _global_manager


# ============================================================================
# 单个 Agent 创建函数
# ============================================================================

def create_agent(config: AgentConfig) -> Any:
    """
    创建 Agent 实例
    
    Args:
        config: Agent 配置对象
        
    Returns:
        创建的 Agent 实例
        
    Examples:
        # 创建简单 Agent
        config = AgentConfig(
            name="my_agent",
            llm_config=LLMConfig(api_key="xxx", model="gpt-4")
        )
        agent = create_agent(config)
        
        # 创建 ReAct Agent
        config = AgentConfig(
            name="react_agent",
            agent_type=AgentType.REACT_AGENT,
            llm_config=LLMConfig(api_key="xxx", model="gpt-4"),
            tools=[tool1, tool2]
        )
        agent = create_agent(config)
    """
    manager = _get_manager()
    return manager.create_agent(config)
  
