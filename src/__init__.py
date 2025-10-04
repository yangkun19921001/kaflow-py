"""
KaFlow-Py SDK

一个轻量级的 Agent 开发框架，基于 LangGraph 构建。

主要特性：
- 🚀 简单易用的 Agent API
- 🔄 支持同步和异步执行
- 💬 内置会话管理
- 🛠️ 灵活的工具集成
- 📡 流式输出支持
- 🎯 ReAct 模式支持

Author: DevYK
微信公众号: DevYK
Email: yang1001yk@gmail.com
Github: https://github.com/yangkun19921001
"""

# 版本信息
__version__ = "1.0.0"
__author__ = "DevYK"
__email__ = "yang1001yk@gmail.com"

# 核心 Agent 类和函数
from .agents import (
    # 传统 Agent 创建
    create_agent,
    
    # 配置类
    AgentConfig,
    AgentType,
    create_simple_agent_config,
    create_react_agent_config,
    
    # 管理器
    AgentManager,
    
    # 异常
    AgentError,
    AgentConfigError,
    AgentCreationError,
    AgentToolError,
    AgentPromptError,
)

# LLM 配置
from .llms.config import LLMConfig

# 工具
from .tools import (
    calculator,
    current_time,
    system_info,
    file_reader,
    file_writer,
)

# 实用工具
from .utils.logger import get_logger

# 快速开始示例
def quick_start_example():
    """
    快速开始示例
    
    展示如何快速创建和使用 KAgent
    """
    print("KaFlow-Py 快速开始示例")
    print("=" * 40)
    
    # 1. 创建 LLM 配置
    llm_config = LLMConfig(
        provider="deepseek",
        model="deepseek-chat",
        api_key="your-api-key-here",  # 请替换为实际的 API Key
        base_url="https://api.deepseek.com"
    )
    
    # 2. 创建基础 Agent
    agent_config = AgentConfig(
        name="快速助手",
        llm_config=llm_config,
        system_prompt="你是一个友好的AI助手，请用中文回答问题。"
    )
    agent = create_kagent(agent_config)
    
    print(f"✅ 创建了 Agent: {agent.config.name}")
    print(f"📝 Agent 类型: {agent.config.agent_type}")
    
    # 3. 创建 ReAct Agent（带工具）
    react_config = AgentConfig(
        name="工具助手",
        agent_type=AgentType.REACT_AGENT,
        llm_config=llm_config,
        tools=[calculator, current_time],
        system_prompt="你是一个能使用工具的AI助手。"
    )
    react_agent = create_kagent(react_config)
    
    print(f"✅ 创建了 ReAct Agent: {react_agent.config.name}")
    print(f"🛠️ 可用工具: {len(react_agent.list_tools())} 个")
    
    print("\n💡 使用示例:")
    print("```python")
    print("# 基础对话")
    print('response = agent.run("你好，请介绍一下自己")')
    print("print(response.content)")
    print("")
    print("# 使用工具")
    print('response = react_agent.run("现在几点了？帮我计算 123 + 456")')
    print("print(response.content)")
    print("")
    print("# 流式输出")
    print('stream = agent.run("请详细介绍AI", stream=True)')
    print("for chunk in stream:")
    print("    print(chunk, end='', flush=True)")
    print("```")
    
    return agent, react_agent


# 导出所有公共 API
__all__ = [
    # 版本信息
    "__version__",
    "__author__",
    "__email__",
    
    # 核心 Agent 类
    "KAgent",
    "KAgentResult",
    
    # 便捷创建函数
    "create_kagent",
    
    # 图构建器
    "GraphBuilder",
    "TaskPlanningGraphBuilder",
    "GraphConfig",
    "ExecutionResult",
    "GraphExecutionMode",
    "create_graph_builder",
    "create_task_planning_graph",
    
    # 图节点
    "BaseNode",
    "GraphState",
    "NodeStatus",
    "NodeType",
    "StartNode",
    "TaskPlanningNode",
    "SubtaskExecutionNode",
    "CompletionNode",
    "create_start_node",
    "create_task_planning_node",
    "create_subtask_execution_node",
    "create_completion_node",
    
    # 传统 API
    "create_agent",
    
    # 配置
    "AgentConfig",
    "AgentType",
    "LLMConfig",
    "create_simple_agent_config",
    "create_react_agent_config",
    
    # 管理器
    "AgentManager",
    
    # 工具
    "calculator",
    "current_time", 
    "system_info",
    "file_reader",
    "file_writer",
    
    # 异常
    "AgentError",
    "AgentConfigError",
    "AgentCreationError",
    "AgentToolError",
    "AgentPromptError",
    
    # 实用工具
    "get_logger",
    
    # 示例
    "quick_start_example",
]


# 打印欢迎信息
def _print_welcome():
    """打印欢迎信息"""
    print(f"""
🚀 KaFlow-Py v{__version__} 
轻量级 Agent 开发框架

快速开始:
  from kaflow_py import KAgent, AgentConfig, LLMConfig
  
  llm_config = LLMConfig(provider="deepseek", model="deepseek-chat", api_key="your-key")
  config = AgentConfig(name="助手", llm_config=llm_config)
  agent = KAgent(config)
  response = agent.run("你好")

更多信息: https://github.com/yangkun19921001/kaflow-py
""")


# 当模块被直接导入时显示欢迎信息
if __name__ != "__main__":
    import os
    if os.getenv("KAFLOW_SHOW_WELCOME", "true").lower() == "true":
        _print_welcome() 