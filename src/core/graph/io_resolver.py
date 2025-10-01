"""
KaFlow-Py 输入输出解析器

提供通用的节点输入输出解析功能，基于 YAML 配置自动处理数据流。

Author: DevYK
WeChat: DevYK
Email: yang1001yk@gmail.com
Github: https://github.com/yangkun19921001
"""

from typing import Dict, Any, List, Optional
from dataclasses import dataclass

from langchain_core.messages import BaseMessage, HumanMessage, AIMessage

from .parser import WorkflowNode
from ...utils.logger import get_logger


@dataclass
class InputField:
    """输入字段定义"""
    name: str
    type: str
    description: str
    source: Optional[str] = None  # 数据源引用，如 "node_name.output_field"
    required: bool = True


@dataclass
class OutputField:
    """输出字段定义"""
    name: str
    type: str
    description: str


class InputOutputResolver:
    """
    输入输出解析器
    
    负责：
    1. 解析节点的 inputs 配置，从 state 中提取数据
    2. 解析节点的 outputs 配置，将结果存储到 state
    3. 构建 agent 的输入提示词
    """
    
    def __init__(self):
        self.logger = get_logger(__name__)
    
    def resolve_inputs(self, node: WorkflowNode, state: Any) -> Dict[str, Any]:
        """
        解析节点的输入数据
        
        Args:
            node: 工作流节点
            state: 图状态
            
        Returns:
            Dict: 解析后的输入数据
        """
        resolved_inputs = {}
        
        # 解析每个输入字段
        for input_config in node.inputs:
            field_name = input_config.get("name")
            field_type = input_config.get("type", "string")
            source = input_config.get("source")
            
            if not field_name:
                continue
            
            # 如果指定了 source，从指定位置获取
            if source:
                value = self._resolve_source(source, state)
            else:
                # 否则尝试从常见位置获取
                value = self._auto_resolve_input(field_name, field_type, state)
            
            if value is not None:
                resolved_inputs[field_name] = value
                self.logger.debug(f"解析输入 {field_name}: {type(value).__name__}")
        
        return resolved_inputs
    
    def store_outputs(self, node: WorkflowNode, state: Any, result: Any) -> None:
        """
        存储节点的输出数据到 state
        
        Args:
            node: 工作流节点
            state: 图状态
            result: 节点执行结果
        """
        # 获取 node_outputs (兼容 dict 和对象)
        if isinstance(state, dict):
            if "node_outputs" not in state:
                state["node_outputs"] = {}
            node_outputs = state["node_outputs"]
        else:
            if not hasattr(state, "node_outputs"):
                state.node_outputs = {}
            node_outputs = state.node_outputs
        
        if node.name not in node_outputs:
            node_outputs[node.name] = {"outputs": {}}
        
        # 如果没有定义 outputs，使用默认存储
        if not node.outputs:
            node_outputs[node.name]["outputs"]["result"] = result
            return
        
        # 根据 outputs 配置存储数据
        for output_config in node.outputs:
            field_name = output_config.get("name")
            field_type = output_config.get("type", "string")
            
            if not field_name:
                continue
            
            # 从结果中提取对应的数据
            value = self._extract_output_value(field_name, field_type, result, state)
            
            if value is not None:
                node_outputs[node.name]["outputs"][field_name] = value
                self.logger.debug(f"存储输出 {field_name}: {type(value).__name__}")
    
    def build_agent_input(self, node: WorkflowNode, state: Any, resolved_inputs: Dict[str, Any]) -> str:
        """
        构建 agent 的输入文本
        
        Args:
            node: 工作流节点
            state: 图状态
            resolved_inputs: 已解析的输入数据
            
        Returns:
            str: 构建的输入文本
        """
        # 策略1: 如果有 user_input，优先使用
        if "user_input" in resolved_inputs:
            user_input = resolved_inputs["user_input"]
            
            # 如果还有其他输入（如历史消息），构建上下文
            if len(resolved_inputs) > 1:
                context_parts = [f"**用户请求**: {user_input}"]
                
                # 添加其他输入作为上下文
                for key, value in resolved_inputs.items():
                    if key == "user_input":
                        continue
                    
                    if key == "message" or key == "messages" or key == "conversation_history":
                        # 消息历史特殊处理
                        context_parts.append(self._format_message_history(value))
                    else:
                        context_parts.append(f"**{key}**: {self._format_value(value)}")
                
                return "\n\n".join(context_parts)
            
            return user_input
        
        # 策略2: 如果有 message/messages，构建基于消息的输入
        for key in ["message", "messages", "conversation_history"]:
            if key in resolved_inputs:
                return self._format_message_history(resolved_inputs[key])
        
        # 策略3: 使用所有输入构建上下文
        if resolved_inputs:
            context_parts = []
            for key, value in resolved_inputs.items():
                context_parts.append(f"**{key}**: {self._format_value(value)}")
            return "\n\n".join(context_parts)
        
        # 策略4: 兜底使用 state 中的 user_input
        if isinstance(state, dict):
            return state.get("user_input", "")
        return getattr(state, "user_input", "")
    
    def _resolve_source(self, source: str, state: Any) -> Any:
        """
        解析数据源引用
        
        支持格式:
        - "node_name.output_field" - 引用其他节点的输出
        - "state.field_name" - 引用 state 中的字段
        - "global.field_name" - 引用 global_context 中的字段
        """
        try:
            parts = source.split(".", 1)
            
            if len(parts) == 1:
                # 简单字段名，从 state 中获取
                if isinstance(state, dict):
                    return state.get(source)
                return getattr(state, source, None)
            
            prefix, field_path = parts
            
            if prefix == "state":
                # 从 state 中获取
                return self._get_nested_value(state, field_path)
            elif prefix == "global":
                # 从 global_context 中获取
                global_context = state.get("global_context", {}) if isinstance(state, dict) else getattr(state, "global_context", {})
                if isinstance(global_context, dict):
                    return global_context.get(field_path)
                return None
            else:
                # 从节点输出中获取
                node_outputs = state.get("node_outputs", {}) if isinstance(state, dict) else getattr(state, "node_outputs", {})
                if prefix in node_outputs:
                    node_output = node_outputs[prefix]
                    return self._get_nested_value(node_output.get("outputs", {}), field_path)
            
        except Exception as e:
            self.logger.warning(f"解析数据源失败 {source}: {e}")
        
        return None
    
    def _auto_resolve_input(self, field_name: str, field_type: str, state: Any) -> Any:
        """
        自动解析输入字段
        
        按优先级从不同位置查找数据
        """
        # 处理 dict 类型的 state
        if isinstance(state, dict):
            # 1. 从 state 直接获取
            if field_name in state:
                return state[field_name]
            
            # 2. 从 global_context 获取
            global_context = state.get("global_context", {})
            if field_name in global_context:
                return global_context[field_name]
            
            # 3. 特殊字段处理
            if field_name == "user_input":
                return state.get("user_input")
            
            if field_name in ["message", "messages", "conversation_history"]:
                # 尝试从前一个节点获取消息
                return self._get_previous_messages(state)
            
            # 4. 尝试从最近的节点输出获取
            node_outputs = state.get("node_outputs", {})
            if node_outputs:
                # 倒序查找最近的节点输出
                for node_name in reversed(list(node_outputs.keys())):
                    node_output = node_outputs[node_name]
                    outputs = node_output.get("outputs", {})
                    if field_name in outputs:
                        return outputs[field_name]
        else:
            # 处理对象类型的 state
            # 1. 从 state 直接属性获取
            if hasattr(state, field_name):
                return getattr(state, field_name)
            
            # 2. 从 global_context 获取
            if hasattr(state, "global_context") and field_name in state.global_context:
                return state.global_context[field_name]
            
            # 3. 特殊字段处理
            if field_name == "user_input" and hasattr(state, "user_input"):
                return state.user_input
            
            if field_name in ["message", "messages", "conversation_history"]:
                # 尝试从前一个节点获取消息
                return self._get_previous_messages(state)
            
            # 4. 尝试从最近的节点输出获取
            if hasattr(state, "node_outputs") and state.node_outputs:
                # 倒序查找最近的节点输出
                for node_name in reversed(list(state.node_outputs.keys())):
                    node_output = state.node_outputs[node_name]
                    outputs = node_output.get("outputs", {})
                    if field_name in outputs:
                        return outputs[field_name]
        
        return None
    
    def _extract_output_value(self, field_name: str, field_type: str, result: Any, state: Any) -> Any:
        """
        从结果中提取输出值
        
        Args:
            field_name: 输出字段名
            field_type: 输出字段类型
            result: 节点执行结果
            state: 图状态
        """
        # 如果 result 是字典，直接获取
        if isinstance(result, dict) and field_name in result:
            return result[field_name]
        
        # 特殊字段处理
        if field_name == "message" or field_name == "messages":
            # 返回消息历史
            if isinstance(state, dict):
                return state.get("messages", [])
            elif hasattr(state, 'messages'):
                return state.messages
            return []
        
        if field_name == "response" or field_name == "result":
            # 返回字符串结果
            if isinstance(result, str):
                return result
            if hasattr(result, 'content'):
                return result.content
            return str(result)
        
        # 默认返回整个结果
        if field_name == "final_report" or field_name == "output":
            if isinstance(result, str):
                return result
            return str(result)
        
        return result
    
    def _get_previous_messages(self, state: Any) -> List[BaseMessage]:
        """获取前一个节点的消息"""
        # 处理 dict 类型的 state
        if isinstance(state, dict):
            messages = state.get("messages", [])
            if messages:
                return messages
            
            # 尝试从最近的节点输出获取
            node_outputs = state.get("node_outputs", {})
            if node_outputs:
                for node_name in reversed(list(node_outputs.keys())):
                    outputs = node_outputs[node_name].get("outputs", {})
                    for key in ["message", "messages", "conversation_history"]:
                        if key in outputs:
                            return outputs[key]
        else:
            # 处理对象类型的 state
            if hasattr(state, 'messages') and state.messages:
                return state.messages
            
            # 尝试从最近的节点输出获取
            if hasattr(state, "node_outputs") and state.node_outputs:
                for node_name in reversed(list(state.node_outputs.keys())):
                    outputs = state.node_outputs[node_name].get("outputs", {})
                    for key in ["message", "messages", "conversation_history"]:
                        if key in outputs:
                            return outputs[key]
        
        return []
    
    def _format_message_history(self, messages: Any) -> str:
        """格式化消息历史"""
        if not messages:
            return ""
        
        if not isinstance(messages, list):
            return str(messages)
        
        formatted_lines = []
        formatted_lines.append("**历史对话**:")
        
        for msg in messages:
            if isinstance(msg, HumanMessage):
                formatted_lines.append(f"用户: {msg.content}")
            elif isinstance(msg, AIMessage):
                formatted_lines.append(f"助手: {msg.content[:500]}{'...' if len(msg.content) > 500 else ''}")
            elif isinstance(msg, BaseMessage):
                formatted_lines.append(f"{msg.__class__.__name__}: {msg.content[:200]}...")
        
        return "\n".join(formatted_lines)
    
    def _format_value(self, value: Any) -> str:
        """格式化值为字符串"""
        if isinstance(value, str):
            return value
        if isinstance(value, list):
            if len(value) > 0 and isinstance(value[0], BaseMessage):
                return self._format_message_history(value)
            return str(value)
        if isinstance(value, dict):
            return str(value)
        return str(value)
    
    def _get_nested_value(self, obj: Any, path: str) -> Any:
        """获取嵌套值"""
        if isinstance(obj, dict):
            return obj.get(path)
        
        # 支持点号分隔的路径
        parts = path.split(".")
        current = obj
        
        for part in parts:
            if isinstance(current, dict):
                current = current.get(part)
            elif hasattr(current, part):
                current = getattr(current, part)
            else:
                return None
            
            if current is None:
                return None
        
        return current


# 全局解析器实例
_resolver_instance = None


def get_io_resolver() -> InputOutputResolver:
    """获取全局 IO 解析器实例"""
    global _resolver_instance
    if _resolver_instance is None:
        _resolver_instance = InputOutputResolver()
    return _resolver_instance


__all__ = [
    "InputField",
    "OutputField",
    "InputOutputResolver",
    "get_io_resolver"
] 