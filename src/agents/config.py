"""
KaFlow-Py Agents 配置模块

定义 Agent 相关的配置类和枚举。

Author: DevYK
WeChat: DevYK
Email: yang1001yk@gmail.com
Github: https://github.com/yangkun19921001
"""

from typing import Optional, List, Dict, Any, Union, Callable
from enum import Enum
from pydantic import BaseModel, Field

from ..llms.config import LLMConfig


class AgentType(str, Enum):
    """Agent 类型"""
    AGENT = "agent"                # 通用 Agent
    REACT_AGENT = "react_agent"       # ReAct Agent (推理->执行->思考)


class AgentConfig(BaseModel):
    """Agent 基础配置"""
    
    # 基础信息
    name: str = Field(..., description="Agent 名称")
    agent_type: AgentType = Field(AgentType.AGENT, description="Agent 类型")
    description: Optional[str] = Field(None, description="Agent 描述")
    
    # LLM 配置
    llm_config: Optional[Union[LLMConfig, Dict[str, Any]]] = Field(None, description="LLM 配置")
    
    # 工具配置
    tools: Optional[List[Any]] = Field(None, description="可用工具列表")
    tool_choice: Optional[str] = Field("auto", description="工具选择策略")
    
    # 提示词配置
    system_prompt: Optional[str] = Field(None, description="系统提示词")
    prompt_template: Optional[str] = Field(None, description="提示词模板")
    
    # 执行配置
    max_iterations: Optional[int] = Field(10, description="最大迭代次数", ge=1, le=100)
    timeout: Optional[int] = Field(300, description="超时时间(秒)", ge=1, le=3600)
    
    # 高级配置
    memory_enabled: Optional[bool] = Field(False, description="是否启用记忆")
    streaming: Optional[bool] = Field(False, description="是否启用流式输出")
    debug: Optional[bool] = Field(False, description="是否启用调试模式")
    
    # 元数据
    metadata: Optional[Dict[str, Any]] = Field(None, description="额外元数据")
    
    class Config:
        extra = "forbid"


# 便捷配置创建函数
def create_simple_agent_config(
    name: str,
    llm_config: LLMConfig,
    system_prompt: Optional[str] = None,
    tools: Optional[List[Any]] = None,
    **kwargs
) -> AgentConfig:
    """创建简单 Agent 配置"""
    return AgentConfig(
        name=name,
        agent_type=AgentType.AGENT,
        llm_config=llm_config,
        system_prompt=system_prompt,
        tools=tools,
        **kwargs
    )


def create_react_agent_config(
    name: str,
    llm_config: LLMConfig,
    tools: List[Any],
    system_prompt: Optional[str] = None,
    **kwargs
) -> AgentConfig:
    """创建 ReAct Agent 配置"""
    return AgentConfig(
        name=name,
        agent_type=AgentType.REACT_AGENT,
        llm_config=llm_config,
        tools=tools,
        system_prompt=system_prompt or "You are a helpful assistant that uses tools to solve problems step by step.",
        **kwargs
    )

