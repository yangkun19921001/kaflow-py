"""
KaFlow-Py 服务端请求和响应模型

定义 FastAPI 接口的请求和响应数据结构

Author: DevYK
WeChat: DevYK
Email: yang1001yk@gmail.com
Github: https://github.com/yangkun19921001
"""

from typing import List, Dict, Any, Optional, Union
from pydantic import BaseModel, Field
from datetime import datetime


class Message(BaseModel):
    """聊天消息模型"""
    role: str = Field(..., description="消息角色: user, assistant, system")
    content: str = Field(..., description="消息内容")
    timestamp: Optional[datetime] = Field(None, description="消息时间戳")


class ChatStreamRequest(BaseModel):
    """聊天流式请求模型"""
    config_id: Union[str, int] = Field(..., description="配置ID，对应YAML配置文件中的ID，支持字符串或整数")
    messages: List[Message] = Field(..., description="聊天消息列表")
    thread_id: str = Field("__default__", description="会话线程ID")
    
    # 可选参数
    max_tokens: Optional[int] = Field(None, description="最大token数")
    temperature: Optional[float] = Field(None, description="温度参数")
    stream: bool = Field(True, description="是否启用流式响应")
    
    # 扩展配置
    custom_config: Optional[Dict[str, Any]] = Field(None, description="自定义配置覆盖")


class ConfigInfo(BaseModel):
    """配置信息模型"""
    id: str = Field(..., description="配置ID")
    name: str = Field(..., description="配置名称")
    description: Optional[str] = Field(None, description="配置描述")
    version: str = Field(..., description="版本号")
    author: Optional[str] = Field(None, description="作者")
    created_at: Optional[datetime] = Field(None, description="创建时间")
    updated_at: Optional[datetime] = Field(None, description="更新时间")
    agents_count: int = Field(0, description="Agent数量")
    nodes_count: int = Field(0, description="节点数量")
    edges_count: int = Field(0, description="边数量")


class ConfigListResponse(BaseModel):
    """配置列表响应模型"""
    configs: List[ConfigInfo] = Field(..., description="配置列表")
    total: int = Field(..., description="配置总数")


class ConfigDetailResponse(BaseModel):
    """配置详情响应模型"""
    config: ConfigInfo = Field(..., description="配置基本信息")
    agents: Dict[str, Any] = Field(..., description="Agent配置详情")
    nodes: List[Dict[str, Any]] = Field(..., description="节点配置详情")
    edges: List[Dict[str, Any]] = Field(..., description="边配置详情")
    global_config: Dict[str, Any] = Field(..., description="全局配置详情")


class HealthResponse(BaseModel):
    """健康检查响应模型"""
    status: str = Field(..., description="服务状态")
    message: str = Field(..., description="状态消息")
    timestamp: datetime = Field(..., description="检查时间")
    configs_loaded: int = Field(..., description="已加载配置数量")


class ErrorResponse(BaseModel):
    """错误响应模型"""
    error: str = Field(..., description="错误类型")
    message: str = Field(..., description="错误消息")
    details: Optional[Dict[str, Any]] = Field(None, description="错误详情")
    timestamp: datetime = Field(..., description="错误时间")


class ReloadResponse(BaseModel):
    """重新加载响应模型"""
    success: bool = Field(..., description="是否成功")
    message: str = Field(..., description="操作消息")
    configs_loaded: int = Field(..., description="重新加载的配置数量")
    timestamp: datetime = Field(..., description="操作时间")


# 兼容deer-flow的模型（如果需要）
class Resource(BaseModel):
    """资源模型（兼容deer-flow）"""
    id: str = Field(..., description="资源ID")
    name: str = Field(..., description="资源名称")
    type: str = Field(..., description="资源类型")
    url: Optional[str] = Field(None, description="资源URL")


class MCPSettings(BaseModel):
    """MCP设置模型（兼容deer-flow）"""
    servers: List[Dict[str, Any]] = Field(default_factory=list, description="MCP服务器列表")


class ExtendedChatStreamRequest(ChatStreamRequest):
    """扩展的聊天流式请求模型（兼容更多参数）"""
    resources: List[Resource] = Field(default_factory=list, description="资源列表")
    max_plan_iterations: int = Field(3, description="最大计划迭代次数")
    max_step_num: int = Field(10, description="最大步骤数")
    max_search_results: int = Field(10, description="最大搜索结果数")
    auto_accepted_plan: bool = Field(True, description="自动接受计划")
    interrupt_feedback: Optional[str] = Field(None, description="中断反馈")
    mcp_settings: Optional[MCPSettings] = Field(None, description="MCP设置")
    enable_background_investigation: bool = Field(False, description="启用后台调查")
    report_style: str = Field("academic", description="报告样式")
    enable_deep_thinking: bool = Field(False, description="启用深度思考")


__all__ = [
    "Message",
    "ChatStreamRequest",
    "ExtendedChatStreamRequest",
    "ConfigInfo",
    "ConfigListResponse", 
    "ConfigDetailResponse",
    "HealthResponse",
    "ErrorResponse",
    "ReloadResponse",
    "Resource",
    "MCPSettings"
] 