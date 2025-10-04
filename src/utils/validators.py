"""
KaFlow-Py 配置验证器模块

提供KaFlow配置协议的验证功能，确保配置的正确性和完整性

Author: DevYK
微信公众号: DevYK
Email: yang1001yk@gmail.com
Github: https://github.com/yangkun19921001
"""

import re
from typing import Dict, Any, List, Optional, Union, Tuple
from .logger import get_logger

logger = get_logger(__name__)


class ValidationError(Exception):
    """配置验证错误异常"""
    def __init__(self, message: str, field_path: str = ""):
        super().__init__(message)
        self.message = message
        self.field_path = field_path
    
    def __str__(self):
        if self.field_path:
            return f"验证错误 [{self.field_path}]: {self.message}"
        return f"验证错误: {self.message}"


class ConfigValidator:
    """KaFlow 配置验证器"""
    
    def __init__(self):
        self.errors: List[ValidationError] = []
    
    def validate(self, config: Dict[str, Any]) -> Tuple[bool, List[ValidationError]]:
        """
        验证完整的KaFlow配置
        
        Args:
            config: 要验证的配置字典
            
        Returns:
            (是否通过验证, 错误列表)
        """
        self.errors.clear()
        
        try:
            # 验证协议信息
            self._validate_protocol(config.get('protocol', {}))
            
            # 验证全局配置
            self._validate_global_config(config.get('global_config', {}))
            
            # 验证Agents配置
            if 'agents' in config:
                self._validate_agents(config['agents'])
            
            # 验证工作流配置
            if 'workflow' in config:
                self._validate_workflow(config['workflow'])
            
            # 验证节点配置
            if 'nodes' in config:
                self._validate_nodes(config['nodes'])
            
            # 验证边配置
            if 'edges' in config:
                self._validate_edges(config['edges'])
            
        except Exception as e:
            logger.error(f"配置验证过程中出现异常: {e}")
            self.errors.append(ValidationError(f"验证过程异常: {e}"))
        
        return len(self.errors) == 0, self.errors.copy()
    
    def _validate_protocol(self, protocol: Dict[str, Any], path: str = "protocol") -> None:
        """验证协议信息"""
        required_fields = ['name', 'version', 'schema_version']
        
        for field in required_fields:
            if field not in protocol:
                self.errors.append(ValidationError(f"缺少必需字段: {field}", f"{path}.{field}"))
            elif not isinstance(protocol[field], str):
                self.errors.append(ValidationError(f"字段类型错误，应为字符串", f"{path}.{field}"))
        
        # 验证版本格式
        if 'version' in protocol:
            version = protocol['version']
            if not re.match(r'^\d+\.\d+\.\d+$', version):
                self.errors.append(ValidationError(f"版本格式错误，应为 x.y.z 格式", f"{path}.version"))
    
    def _validate_global_config(self, global_config: Dict[str, Any], path: str = "global_config") -> None:
        """验证全局配置"""
        if not global_config:
            return
        
        # 验证运行时配置
        if 'runtime' in global_config:
            self._validate_runtime_config(global_config['runtime'], f"{path}.runtime")
        
        # 验证日志配置
        if 'logging' in global_config:
            self._validate_logging_config(global_config['logging'], f"{path}.logging")
        
        # 验证记忆配置
        if 'memory' in global_config:
            self._validate_memory_config(global_config['memory'], f"{path}.memory")
    
    def _validate_runtime_config(self, runtime: Dict[str, Any], path: str) -> None:
        """验证运行时配置"""
        # 验证数值类型字段
        numeric_fields = {
            'timeout': (int, 1, 3600),
            'max_retries': (int, 0, 10),
            'parallel_limit': (int, 1, 100)
        }
        
        for field, (field_type, min_val, max_val) in numeric_fields.items():
            if field in runtime:
                value = runtime[field]
                if not isinstance(value, field_type):
                    self.errors.append(ValidationError(f"字段类型错误，应为{field_type.__name__}", f"{path}.{field}"))
                elif not (min_val <= value <= max_val):
                    self.errors.append(ValidationError(f"数值超出范围 [{min_val}, {max_val}]", f"{path}.{field}"))
        
        # 验证布尔类型字段
        bool_fields = ['debug_mode', 'trace_enabled', 'checkpoint_enabled']
        for field in bool_fields:
            if field in runtime and not isinstance(runtime[field], bool):
                self.errors.append(ValidationError(f"字段类型错误，应为布尔值", f"{path}.{field}"))
    
    def _validate_logging_config(self, logging: Dict[str, Any], path: str) -> None:
        """验证日志配置"""
        # 验证日志级别
        if 'level' in logging:
            valid_levels = ['DEBUG', 'INFO', 'WARN', 'ERROR']
            if logging['level'] not in valid_levels:
                self.errors.append(ValidationError(f"无效的日志级别，应为: {valid_levels}", f"{path}.level"))
        
        # 验证日志格式
        if 'format' in logging:
            valid_formats = ['json', 'text']
            if logging['format'] not in valid_formats:
                self.errors.append(ValidationError(f"无效的日志格式，应为: {valid_formats}", f"{path}.format"))
        
        # 验证输出目标
        if 'output' in logging:
            valid_outputs = ['stdout', 'file']
            if logging['output'] not in valid_outputs:
                self.errors.append(ValidationError(f"无效的输出目标，应为: {valid_outputs}", f"{path}.output"))
    
    def _validate_memory_config(self, memory: Dict[str, Any], path: str) -> None:
        """验证记忆配置"""
        # 验证存储提供商
        if 'provider' in memory:
            valid_providers = ['memory', 'redis', 'postgresql', 'mongodb', 'sqlite']
            if memory['provider'] not in valid_providers:
                self.errors.append(ValidationError(f"无效的存储提供商，应为: {valid_providers}", f"{path}.provider"))
        
        # 验证TTL
        if 'ttl' in memory:
            ttl = memory['ttl']
            if not isinstance(ttl, int) or ttl < 0:
                self.errors.append(ValidationError(f"TTL应为非负整数", f"{path}.ttl"))
        
        # 验证最大大小格式
        if 'max_size' in memory:
            max_size = memory['max_size']
            if not isinstance(max_size, str) or not re.match(r'^\d+[KMGT]?B$', max_size):
                self.errors.append(ValidationError(f"最大大小格式错误，应为如 100MB", f"{path}.max_size"))
    
    def _validate_agents(self, agents: Dict[str, Any], path: str = "agents") -> None:
        """验证Agents配置"""
        if not isinstance(agents, dict):
            self.errors.append(ValidationError("agents配置应为字典类型", path))
            return
        
        for agent_name, agent_config in agents.items():
            agent_path = f"{path}.{agent_name}"
            self._validate_agent_config(agent_config, agent_path, agent_name)
    
    def _validate_agent_config(self, agent: Dict[str, Any], path: str, name: str) -> None:
        """验证单个Agent配置"""
        # 验证必需字段
        required_fields = ['type', 'system_prompt', 'llm']
        for field in required_fields:
            if field not in agent:
                self.errors.append(ValidationError(f"Agent缺少必需字段: {field}", path))
        
        # 验证Agent类型
        if 'type' in agent:
            valid_types = ['agent', 'react_agent', 'chain_agent', 'multi_agent']
            if agent['type'] not in valid_types:
                self.errors.append(ValidationError(f"无效的Agent类型，应为: {valid_types}", f"{path}.type"))
        
        # 验证名称格式
        if not re.match(r'^[a-zA-Z][a-zA-Z0-9_]*$', name):
            self.errors.append(ValidationError(f"Agent名称格式错误，应以字母开头", path))
        
        # 验证系统提示词
        if 'system_prompt' in agent:
            prompt = agent['system_prompt']
            if not isinstance(prompt, str):
                self.errors.append(ValidationError("system_prompt应为字符串类型", f"{path}.system_prompt"))
            elif len(prompt.strip()) < 10:
                self.errors.append(ValidationError("system_prompt过短，至少10个字符", f"{path}.system_prompt"))
            elif len(prompt) > 8192:
                self.errors.append(ValidationError("system_prompt过长，最多8192个字符", f"{path}.system_prompt"))
        
        # 验证LLM配置
        if 'llm' in agent:
            self._validate_llm_config(agent['llm'], f"{path}.llm")
        
        # 验证工具配置
        if 'tools' in agent:
            self._validate_tools_config(agent['tools'], f"{path}.tools")
        
        # 验证MCP服务器配置
        if 'mcp_servers' in agent:
            self._validate_mcp_servers_config(agent['mcp_servers'], f"{path}.mcp_servers")
    
    def _validate_llm_config(self, llm: Dict[str, Any], path: str) -> None:
        """验证LLM配置"""
        # 验证必需字段
        required_fields = ['api_key', 'model']
        for field in required_fields:
            if field not in llm:
                self.errors.append(ValidationError(f"LLM配置缺少必需字段: {field}", f"{path}.{field}"))
        
        # 验证API密钥
        if 'api_key' in llm:
            api_key = llm['api_key']
            if not isinstance(api_key, str):
                self.errors.append(ValidationError("api_key应为字符串类型", f"{path}.api_key"))
            elif len(api_key.strip()) < 10:
                self.errors.append(ValidationError("api_key过短，至少10个字符", f"{path}.api_key"))
        
        # 验证模型名称
        if 'model' in llm:
            model = llm['model']
            if not isinstance(model, str):
                self.errors.append(ValidationError("model应为字符串类型", f"{path}.model"))
        
        # 验证温度参数
        if 'temperature' in llm:
            temp = llm['temperature']
            if not isinstance(temp, (int, float)):
                self.errors.append(ValidationError("temperature应为数值类型", f"{path}.temperature"))
            elif not (0.0 <= temp <= 2.0):
                self.errors.append(ValidationError("temperature应在0.0-2.0范围内", f"{path}.temperature"))
        
        # 验证最大token数
        if 'max_tokens' in llm:
            max_tokens = llm['max_tokens']
            if not isinstance(max_tokens, int):
                self.errors.append(ValidationError("max_tokens应为整数类型", f"{path}.max_tokens"))
            elif not (1 <= max_tokens <= 32768):
                self.errors.append(ValidationError("max_tokens应在1-32768范围内", f"{path}.max_tokens"))
        
        # 验证超时时间
        if 'timeout' in llm:
            timeout = llm['timeout']
            if not isinstance(timeout, int):
                self.errors.append(ValidationError("timeout应为整数类型", f"{path}.timeout"))
            elif not (1 <= timeout <= 300):
                self.errors.append(ValidationError("timeout应在1-300秒范围内", f"{path}.timeout"))
    
    def _validate_tools_config(self, tools: List[Dict[str, Any]], path: str) -> None:
        """验证工具配置"""
        if not isinstance(tools, list):
            self.errors.append(ValidationError("tools应为列表类型", path))
            return
        
        for i, tool in enumerate(tools):
            tool_path = f"{path}[{i}]"
            self._validate_tool_config(tool, tool_path)
    
    def _validate_tool_config(self, tool: Dict[str, Any], path: str) -> None:
        """验证单个工具配置"""
        # 验证必需字段
        if 'name' not in tool:
            self.errors.append(ValidationError("工具配置缺少name字段", path))
        
        # 验证工具名称格式
        if 'name' in tool:
            name = tool['name']
            if not isinstance(name, str):
                self.errors.append(ValidationError("工具名称应为字符串类型", f"{path}.name"))
            elif not re.match(r'^[a-zA-Z][a-zA-Z0-9_]*$', name):
                self.errors.append(ValidationError("工具名称格式错误，应以字母开头", f"{path}.name"))
        
        # 验证工具类型
        if 'type' in tool:
            valid_types = ['builtin', 'custom', 'api', 'function']
            if tool['type'] not in valid_types:
                self.errors.append(ValidationError(f"无效的工具类型，应为: {valid_types}", f"{path}.type"))
    
    def _validate_mcp_servers_config(self, mcp_servers: List[Dict[str, Any]], path: str) -> None:
        """验证MCP服务器配置"""
        if not isinstance(mcp_servers, list):
            self.errors.append(ValidationError("mcp_servers应为列表类型", path))
            return
        
        for i, server in enumerate(mcp_servers):
            server_path = f"{path}[{i}]"
            self._validate_mcp_server_config(server, server_path)
    
    def _validate_mcp_server_config(self, server: Dict[str, Any], path: str) -> None:
        """验证单个MCP服务器配置"""
        # 验证必需字段
        required_fields = ['name', 'url']
        for field in required_fields:
            if field not in server:
                self.errors.append(ValidationError(f"MCP服务器配置缺少必需字段: {field}", f"{path}.{field}"))
        
        # 验证URL格式
        if 'url' in server:
            url = server['url']
            if not isinstance(url, str):
                self.errors.append(ValidationError("URL应为字符串类型", f"{path}.url"))
            elif not re.match(r'^https?://.*$', url):
                self.errors.append(ValidationError("URL格式错误，应以http://或https://开头", f"{path}.url"))
        
        # 验证协议类型
        if 'protocol' in server:
            valid_protocols = ['sse', 'stdio', 'websocket']
            if server['protocol'] not in valid_protocols:
                self.errors.append(ValidationError(f"无效的协议类型，应为: {valid_protocols}", f"{path}.protocol"))
    
    def _validate_workflow(self, workflow: Dict[str, Any], path: str = "workflow") -> None:
        """验证工作流配置"""
        # 验证必需字段
        required_fields = ['name', 'version']
        for field in required_fields:
            if field not in workflow:
                self.errors.append(ValidationError(f"工作流配置缺少必需字段: {field}", f"{path}.{field}"))
        
        # 验证名称格式
        if 'name' in workflow:
            name = workflow['name']
            if not isinstance(name, str):
                self.errors.append(ValidationError("工作流名称应为字符串类型", f"{path}.name"))
            elif not re.match(r'^[a-zA-Z][a-zA-Z0-9_\-\s]*$', name):
                self.errors.append(ValidationError("工作流名称格式错误", f"{path}.name"))
        
        # 验证版本格式
        if 'version' in workflow:
            version = workflow['version']
            if not isinstance(version, str):
                self.errors.append(ValidationError("版本应为字符串类型", f"{path}.version"))
            elif not re.match(r'^\d+\.\d+\.\d+$', version):
                self.errors.append(ValidationError("版本格式错误，应为 x.y.z 格式", f"{path}.version"))
    
    def _validate_nodes(self, nodes: Dict[str, Any], path: str = "nodes") -> None:
        """验证节点配置"""
        if not isinstance(nodes, dict):
            self.errors.append(ValidationError("nodes配置应为字典类型", path))
            return
        
        for node_name, node_config in nodes.items():
            node_path = f"{path}.{node_name}"
            self._validate_node_config(node_config, node_path, node_name)
    
    def _validate_node_config(self, node: Dict[str, Any], path: str, name: str) -> None:
        """验证单个节点配置"""
        # 验证必需字段
        if 'type' not in node:
            self.errors.append(ValidationError("节点配置缺少type字段", path))
        
        # 验证节点类型
        if 'type' in node:
            valid_types = [
                'start', 'end', 'agent', 'condition', 'loop', 'parallel',
                'rag', 'tool', 'code', 'template', 'http', 'webhook',
                'schedule', 'custom'
            ]
            if node['type'] not in valid_types:
                self.errors.append(ValidationError(f"无效的节点类型，应为: {valid_types}", f"{path}.type"))
        
        # 验证节点名称格式
        if not re.match(r'^[a-zA-Z][a-zA-Z0-9_]*$', name):
            self.errors.append(ValidationError("节点名称格式错误，应以字母开头", path))
        
        # 验证Agent引用（对于agent类型节点）
        if node.get('type') == 'agent' and 'agent_ref' not in node:
            self.errors.append(ValidationError("agent类型节点必须包含agent_ref字段", f"{path}.agent_ref"))
    
    def _validate_edges(self, edges: List[Dict[str, Any]], path: str = "edges") -> None:
        """验证边配置"""
        if not isinstance(edges, list):
            self.errors.append(ValidationError("edges配置应为列表类型", path))
            return
        
        for i, edge in enumerate(edges):
            edge_path = f"{path}[{i}]"
            self._validate_edge_config(edge, edge_path)
    
    def _validate_edge_config(self, edge: Dict[str, Any], path: str) -> None:
        """验证单个边配置"""
        # 验证必需字段
        required_fields = ['from', 'to']
        for field in required_fields:
            if field not in edge:
                self.errors.append(ValidationError(f"边配置缺少必需字段: {field}", f"{path}.{field}"))
        
        # 验证节点名称格式
        for field in ['from', 'to']:
            if field in edge:
                node_name = edge[field]
                if not isinstance(node_name, str):
                    self.errors.append(ValidationError(f"{field}应为字符串类型", f"{path}.{field}"))
                elif not re.match(r'^[a-zA-Z][a-zA-Z0-9_]*$', node_name):
                    self.errors.append(ValidationError(f"{field}节点名称格式错误", f"{path}.{field}"))
        
        # 验证权重
        if 'weight' in edge:
            weight = edge['weight']
            if not isinstance(weight, (int, float)):
                self.errors.append(ValidationError("权重应为数值类型", f"{path}.weight"))
            elif not (0.0 <= weight <= 10.0):
                self.errors.append(ValidationError("权重应在0.0-10.0范围内", f"{path}.weight"))


def validate_config(config: Dict[str, Any]) -> Tuple[bool, List[ValidationError]]:
    """
    验证KaFlow配置
    
    Args:
        config: 要验证的配置字典
        
    Returns:
        (是否通过验证, 错误列表)
    """
    validator = ConfigValidator()
    return validator.validate(config)


def validate_agent_config(agent_config: Dict[str, Any], agent_name: str = "agent") -> Tuple[bool, List[ValidationError]]:
    """
    验证单个Agent配置
    
    Args:
        agent_config: Agent配置字典
        agent_name: Agent名称
        
    Returns:
        (是否通过验证, 错误列表)
    """
    validator = ConfigValidator()
    validator._validate_agent_config(agent_config, f"agents.{agent_name}", agent_name)
    return len(validator.errors) == 0, validator.errors


def validate_llm_config(llm_config: Dict[str, Any]) -> Tuple[bool, List[ValidationError]]:
    """
    验证LLM配置
    
    Args:
        llm_config: LLM配置字典
        
    Returns:
        (是否通过验证, 错误列表)
    """
    validator = ConfigValidator()
    validator._validate_llm_config(llm_config, "llm")
    return len(validator.errors) == 0, validator.errors