"""
KaFlow-Py 配置加载器和验证器

提供统一的配置加载、验证和管理功能，包括：
- ConfigLoader: 配置文件加载器
- ConfigValidator: 配置验证器
- KaFlowConfig: 完整的KaFlow配置模型

Author: DevYK
WeChat: DevYK
Email: yang1001yk@gmail.com
Github: https://github.com/yangkun19921001
"""

import yaml
import json
from pathlib import Path
from typing import Dict, Any, Optional, List, Union
from pydantic import BaseModel, Field, ValidationError

from .config.model.base_models import Protocol, GlobalConfig
from .config.model.agent_models import AgentBaseStructure
from .config.model.workflow_models import NodeBaseStructure, EdgeBaseStructure
from .config.model.memory_models import MemoryBaseConfig
from .config.model.workflow_models import WorkflowBaseConfig


class KaFlowConfig(BaseModel):
    """完整的KaFlow配置模型"""
    protocol: Protocol = Field(..., description="协议版本与元信息")
    global_config: Optional[GlobalConfig] = Field(None, description="全局配置")
    agents: Optional[Dict[str, AgentBaseStructure]] = Field(None, description="Agent配置")
    nodes: Optional[Dict[str, NodeBaseStructure]] = Field(None, description="节点配置")
    edges: Optional[List[EdgeBaseStructure]] = Field(None, description="边配置")
    workflow: Optional[WorkflowBaseConfig] = Field(None, description="工作流配置")
    memory: Optional[MemoryBaseConfig] = Field(None, description="记忆存储配置")

    class Config:
        extra = "allow"  # 允许额外字段，以支持扩展


class ConfigLoader:
    """配置文件加载器"""
    
    @staticmethod
    def load_from_file(file_path: Union[str, Path]) -> Dict[str, Any]:
        """从文件加载配置"""
        file_path = Path(file_path)
        
        if not file_path.exists():
            raise FileNotFoundError(f"Configuration file not found: {file_path}")
        
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                if file_path.suffix.lower() in ['.yaml', '.yml']:
                    return yaml.safe_load(f)
                elif file_path.suffix.lower() == '.json':
                    return json.load(f)
                else:
                    raise ValueError(f"Unsupported file format: {file_path.suffix}")
        except Exception as e:
            raise ValueError(f"Failed to load configuration file: {e}")
    
    @staticmethod
    def load_from_dict(config_dict: Dict[str, Any]) -> KaFlowConfig:
        """从字典创建配置对象"""
        try:
            return KaFlowConfig(**config_dict)
        except ValidationError as e:
            raise ValueError(f"Configuration validation failed: {e}")
    
    @staticmethod
    def load_config(file_path: Union[str, Path]) -> KaFlowConfig:
        """加载并验证配置文件"""
        config_dict = ConfigLoader.load_from_file(file_path)
        return ConfigLoader.load_from_dict(config_dict)


class ConfigValidator:
    """配置验证器"""
    
    @staticmethod
    def validate_protocol_version(config: KaFlowConfig) -> bool:
        """验证协议版本兼容性"""
        supported_versions = ["1.0.0"]
        if config.protocol.version not in supported_versions:
            raise ValueError(f"Unsupported protocol version: {config.protocol.version}")
        return True
    
    @staticmethod
    def validate_agent_references(config: KaFlowConfig) -> bool:
        """验证Agent引用的完整性"""
        if not config.agents or not config.nodes:
            return True
        
        agent_names = set(config.agents.keys())
        
        for node_name, node in config.nodes.items():
            if node.type.value == "agent" and node.agent_ref:
                if node.agent_ref not in agent_names:
                    raise ValueError(f"Node '{node_name}' references unknown agent '{node.agent_ref}'")
        
        return True
    
    @staticmethod
    def validate_node_connections(config: KaFlowConfig) -> bool:
        """验证节点连接的完整性"""
        if not config.nodes or not config.edges:
            return True
        
        node_names = set(config.nodes.keys())
        
        for edge in config.edges:
            if edge.from_node not in node_names:
                raise ValueError(f"Edge references unknown source node '{edge.from_node}'")
            if edge.to_node not in node_names:
                raise ValueError(f"Edge references unknown target node '{edge.to_node}'")
        
        return True
    
    @staticmethod
    def validate_workflow_completeness(config: KaFlowConfig) -> bool:
        """验证工作流的完整性"""
        if not config.nodes:
            return True
        
        # 检查是否有开始和结束节点
        has_start = any(node.type.value == "start" for node in config.nodes.values())
        has_end = any(node.type.value == "end" for node in config.nodes.values())
        
        if not has_start:
            raise ValueError("Workflow must have at least one start node")
        if not has_end:
            raise ValueError("Workflow must have at least one end node")
        
        return True
    
    @staticmethod
    def validate_config(config: KaFlowConfig) -> bool:
        """完整配置验证"""
        try:
            ConfigValidator.validate_protocol_version(config)
            ConfigValidator.validate_agent_references(config)
            ConfigValidator.validate_node_connections(config)
            ConfigValidator.validate_workflow_completeness(config)
            return True
        except Exception as e:
            raise ValueError(f"Configuration validation failed: {e}")


class ConfigManager:
    """配置管理器"""
    
    def __init__(self, config_path: Optional[Union[str, Path]] = None):
        """初始化配置管理器"""
        self._config: Optional[KaFlowConfig] = None
        self._config_path: Optional[Path] = None
        
        if config_path:
            self.load_config(config_path)
    
    def load_config(self, config_path: Union[str, Path]) -> KaFlowConfig:
        """加载配置文件"""
        self._config_path = Path(config_path)
        self._config = ConfigLoader.load_config(self._config_path)
        ConfigValidator.validate_config(self._config)
        return self._config
    
    def reload_config(self) -> KaFlowConfig:
        """重新加载配置文件"""
        if not self._config_path:
            raise ValueError("No configuration file path set")
        return self.load_config(self._config_path)
    
    @property
    def config(self) -> KaFlowConfig:
        """获取当前配置"""
        if not self._config:
            raise ValueError("No configuration loaded")
        return self._config
    
    def get_agent(self, agent_name: str) -> Optional[AgentBaseStructure]:
        """获取指定Agent配置"""
        if not self._config or not self._config.agents:
            return None
        return self._config.agents.get(agent_name)
    
    def get_node(self, node_name: str) -> Optional[NodeBaseStructure]:
        """获取指定节点配置"""
        if not self._config or not self._config.nodes:
            return None
        return self._config.nodes.get(node_name)
    
    def list_agents(self) -> List[str]:
        """列出所有Agent名称"""
        if not self._config or not self._config.agents:
            return []
        return list(self._config.agents.keys())
    
    def list_nodes(self) -> List[str]:
        """列出所有节点名称"""
        if not self._config or not self._config.nodes:
            return []
        return list(self._config.nodes.keys())
    
    def save_config(self, output_path: Optional[Union[str, Path]] = None) -> None:
        """保存配置到文件"""
        if not self._config:
            raise ValueError("No configuration to save")
        
        save_path = Path(output_path) if output_path else self._config_path
        if not save_path:
            raise ValueError("No output path specified")
        
        config_dict = self._config.dict(exclude_none=True)
        
        try:
            with open(save_path, 'w', encoding='utf-8') as f:
                if save_path.suffix.lower() in ['.yaml', '.yml']:
                    yaml.dump(config_dict, f, default_flow_style=False, allow_unicode=True)
                elif save_path.suffix.lower() == '.json':
                    json.dump(config_dict, f, indent=2, ensure_ascii=False)
                else:
                    raise ValueError(f"Unsupported file format: {save_path.suffix}")
        except Exception as e:
            raise ValueError(f"Failed to save configuration file: {e}")


# 便捷函数
def load_kaflow_config(config_path: Union[str, Path]) -> KaFlowConfig:
    """便捷函数：加载KaFlow配置"""
    return ConfigLoader.load_config(config_path)


def validate_kaflow_config(config: KaFlowConfig) -> bool:
    """便捷函数：验证KaFlow配置"""
    return ConfigValidator.validate_config(config) 