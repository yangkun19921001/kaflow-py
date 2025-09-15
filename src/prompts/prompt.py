"""
KaFlow-Py Prompts 模块

提供提示词函数封装，用于 Agent 创建时的 prompt 参数。

Author: DevYK
WeChat: DevYK
Email: yang1001yk@gmail.com
Github: https://github.com/yangkun19921001
"""

from langgraph.prebuilt.chat_agent_executor import AgentState

def apply_prompt_template(
    prompt: str, state: AgentState
) -> list:
    """
    Apply template variables to a prompt template and return formatted messages.

    Args:
        prompt_name: Name of the prompt template to use
        state: Current agent state containing variables to substitute

    Returns:
        List of messages with the system prompt as the first message
    """

    return [{"role": "system", "content": prompt}] + state["messages"]
