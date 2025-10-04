"""
KaFlow-Py Agents 管理器

简化的 Agent 管理器，负责管理和创建 Agent 实例。

Author: DevYK
微信公众号: DevYK
Email: yang1001yk@gmail.com
Github: https://github.com/yangkun19921001
"""

import threading
import time
import asyncio
from typing import Dict, Optional, Any, List, Union
from contextlib import contextmanager

from .config import AgentConfig, AgentType
from .exceptions import AgentError, AgentConfigError
from ..llms import LLMManager, LLMConfig
from ..prompts.prompt import apply_prompt_template
from ..utils.logger import get_logger
from langgraph.prebuilt import create_react_agent


class AgentManager:
    """简化的 Agent 管理器"""
    
    def __init__(self):
        """
        初始化 Agent 管理器
        
        Args:
        """
        self.llm_manager = LLMManager()
        self._lock = threading.RLock()
        self.logger = get_logger("AgentManager")
    
    def create_agent(self, config: AgentConfig) -> Any:
        """
        创建 Agent 实例（带重试机制）
        
        Args:
            config: Agent 配置
            
        Returns:
            创建的 Agent 实例
        """
        # 参数验证
        self._validate_config(config)

        # 根据类型创建不同的 Agent
        if config.agent_type == AgentType.REACT_AGENT:
            return self._create_react_agent(config)
        else:
            return self._create_simple_agent(config)
                        

    def _validate_config(self, config: AgentConfig) -> None:
        """验证配置参数"""
        if not config.name or not config.name.strip():
            raise AgentConfigError("Agent name is required", config_key="name")
        
        if not config.llm_config:
            raise AgentConfigError(f"LLM config is required for agent {config.name}", config_key="llm_config", agent_name=config.name)
        
        # ReAct Agent 需要工具，但允许空列表（可以后续动态添加）
        if config.agent_type == AgentType.REACT_AGENT and config.tools is None:
            # 如果 tools 是 None，设置为空列表
            config.tools = []
   
    def _create_react_agent(self, config: AgentConfig) -> Any:
        """创建 ReAct Agent"""
        try:
            llm = self.llm_manager.get_llm(config.llm_config)
            # 修复 LangGraph API 调用
            return create_react_agent(
                model=llm,  
                tools=config.tools or [],
                prompt=lambda state: apply_prompt_template(config.system_prompt, state), 
            )
        except ImportError as e:
            raise AgentError(f"LangGraph is not installed. Please install it with: pip install langgraph", agent_name=config.name) from e
        except Exception as e:
            raise AgentError(f"Failed to create ReAct agent {config.name}: {str(e)}", agent_name=config.name) from e
    
    def _create_simple_agent(self, config: AgentConfig) -> Any:
        """创建通用 Agent"""
        try:
            llm = self.llm_manager.get_llm(config.llm_config)
            
            # 如果有工具，则绑定工具
            if config.tools:
                llm = llm.bind_tools(config.tools)
            
            return llm
        except Exception as e:
            raise AgentError(f"Failed to create simple agent {config.name}: {str(e)}", agent_name=config.name) from e

    @contextmanager
    def temporary_agent(self, config: AgentConfig):
        """
        临时 Agent 上下文管理器
        
        Args:
            config: Agent 配置
            
        Yields:
            临时 Agent 实例
        """
        agent = None
        try:
            agent = self.create_agent(config)
            yield agent
        finally:
            # 临时 Agent 清理（如果需要）
            pass