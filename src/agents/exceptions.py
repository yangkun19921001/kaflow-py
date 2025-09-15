"""
KaFlow-Py Agents 异常处理模块

定义 Agent 相关的异常类。

Author: DevYK
WeChat: DevYK
Email: yang1001yk@gmail.com
Github: https://github.com/yangkun19921001
"""


class AgentError(Exception):
    """Agent 基础异常类"""
    
    def __init__(self, message: str, agent_name: str = None):
        self.message = message
        self.agent_name = agent_name
        super().__init__(self.message)


class AgentConfigError(AgentError):
    """Agent 配置错误"""
    
    def __init__(self, message: str, config_key: str = None, agent_name: str = None):
        self.config_key = config_key
        super().__init__(message, agent_name)


class AgentCreationError(AgentError):
    """Agent 创建错误"""
    
    def __init__(self, message: str, agent_type: str = None, agent_name: str = None):
        self.agent_type = agent_type
        super().__init__(message, agent_name)


class AgentToolError(AgentError):
    """Agent 工具错误"""
    
    def __init__(self, message: str, tool_name: str = None, agent_name: str = None):
        self.tool_name = tool_name
        super().__init__(message, agent_name)


class AgentPromptError(AgentError):
    """Agent 提示词错误"""
    
    def __init__(self, message: str, prompt_template: str = None, agent_name: str = None):
        self.prompt_template = prompt_template
        super().__init__(message, agent_name) 