"""
KaFlow-Py FastAPI 服务端应用

基于配置驱动的 AI Agent 开发框架 Web API
实现基于 YAML 配置文件中 id 字段的按需加载和缓存机制

Author: DevYK
微信公众号: DevYK
Email: yang1001yk@gmail.com
Github: https://github.com/yangkun19921001
"""

import json
import yaml
from datetime import datetime
from typing import Dict, Any, List, Optional
from uuid import uuid4
from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse

from .models import (
    ChatStreamRequest, 
    ExtendedChatStreamRequest, 
    HealthResponse,
    MCPServerMetadataRequest,
    MCPServerMetadataResponse
)
from ..core.graph import get_graph_manager, GraphManager
from ..mcp.mcp import load_mcp_tools
from ..utils.logger import get_logger

logger = get_logger(__name__)

INTERNAL_SERVER_ERROR_DETAIL = "Internal Server Error"

app = FastAPI(
    title="KaFlow-Py API",
    description="配置驱动的 AI Agent 开发框架 API",
    version="1.0.0",
)

# 添加 CORS 中间件
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 配置文件缓存：{config_id: config_file_path}
_config_file_cache: Dict[str, Path] = {}
_config_loaded = False


def _load_config_file_mappings():
    """加载配置文件ID映射，扫描所有配置文件并建立ID到文件路径的映射"""
    global _config_file_cache, _config_loaded
    
    if _config_loaded:
        return
    
    logger.info("开始扫描配置文件...")
    config_dir = Path(__file__).parent.parent / "core" / "config"
    
    if not config_dir.exists():
        logger.warning(f"配置目录不存在: {config_dir}")
        return
    
    # 查找所有YAML文件（排除模板文件）
    yaml_files = []
    for pattern in ["*.yaml", "*.yml"]:
        yaml_files.extend(config_dir.glob(pattern))
    
    config_files = [f for f in yaml_files if not f.name.endswith('.template')]
    logger.info(f"发现 {len(config_files)} 个配置文件")
    
    for config_file in config_files:
        try:
            with open(config_file, 'r', encoding='utf-8') as f:
                config_data = yaml.safe_load(f)
            
            if config_data and 'id' in config_data:
                config_id = str(config_data['id'])  # 确保ID是字符串
                _config_file_cache[config_id] = config_file
                logger.info(f"映射配置 ID {config_id} -> {config_file.name}")
            else:
                logger.warning(f"配置文件缺少 id 字段: {config_file.name}")
                
        except Exception as e:
            logger.error(f"读取配置文件失败 {config_file}: {e}")
    
    logger.info(f"成功建立 {len(_config_file_cache)} 个配置ID映射")
    _config_loaded = True


def _ensure_graph_loaded(config_id: str) -> bool:
    """确保指定ID的图已加载到缓存中"""
    manager = get_graph_manager()
    
    # 检查图是否已在缓存中
    if manager.registry.get_graph(config_id):
        logger.debug(f"图 {config_id} 已在缓存中")
        return True
    
    # 确保配置文件映射已加载
    _load_config_file_mappings()
    
    # 查找配置文件
    if config_id not in _config_file_cache:
        logger.error(f"配置ID {config_id} 不存在，可用ID: {list(_config_file_cache.keys())}")
        return False
    
    config_file = _config_file_cache[config_id]
    
    try:
        # 加载图到缓存
        logger.info(f"按需加载配置 {config_id} 从 {config_file.name}")
        manager.register_graph_from_file(config_file, config_id)
        logger.info(f"成功加载图 {config_id} 到缓存")
        return True
        
    except Exception as e:
        logger.error(f"加载配置文件失败 {config_id}: {e}")
        return False


@app.post("/api/chat/stream")
async def chat_stream(request: ChatStreamRequest):
    """
    聊天流式接口 - 根据配置ID按需加载对应的工作流并处理请求
    
    Args:
        request: 聊天流式请求
        
    Returns:
        StreamingResponse: SSE流式响应
    """
    try:
        config_id = str(request.config_id)  # 确保ID是字符串
        
        # 确保图已加载
        if not _ensure_graph_loaded(config_id):
            # 加载配置文件映射以获取可用ID列表
            _load_config_file_mappings()
            available_ids = list(_config_file_cache.keys())
            raise HTTPException(
                status_code=404, 
                detail=f"配置ID {config_id} 不存在或加载失败。可用配置ID: {available_ids}"
            )
        
        logger.info(f"使用配置ID: {config_id}")
        
        # 生成线程ID
        thread_id = request.thread_id
        if thread_id == "__default__":
            thread_id = str(uuid4())
        
        # 构建用户输入
        user_input = request.messages[-1].content if request.messages else ""
        
        # 返回流式响应
        return StreamingResponse(
            _chat_stream_generator(
                config_id=config_id,
                user_input=user_input,
                messages=request.messages,
                thread_id=thread_id,
                custom_config=request.custom_config or {}
            ),
            media_type="text/event-stream",
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.exception(f"聊天流式接口错误: {e}")
        raise HTTPException(status_code=500, detail=INTERNAL_SERVER_ERROR_DETAIL)



async def _chat_stream_generator(
    config_id: str,
    user_input: str,
    messages: List[Any],
    thread_id: str,
    custom_config: Dict[str, Any] = None
):
    """
    聊天流式生成器
    
    Args:
        config_id: 配置ID
        user_input: 用户输入
        messages: 消息列表
        thread_id: 线程ID
        custom_config: 自定义配置
    """
    try:
        manager = get_graph_manager()
        
        # 使用图管理器的流式执行
        async for sse_event_string in manager.execute_graph_stream(
            graph_id=config_id,
            user_input=user_input,
            messages=messages,
            thread_id=thread_id,
            **(custom_config or {})
        ):
            # 正确：直接 yield 已格式化的 SSE 字符串
            yield sse_event_string
            
    except Exception as e:
        logger.error(f"流式生成器错误: {e}")
        yield f"event: error\ndata: {json.dumps(e, ensure_ascii=False)}\n\n"


@app.get("/api/configs")
async def list_configs():
    """获取当前所有可用配置ID列表"""
    try:
        # 确保配置文件映射已加载
        _load_config_file_mappings()
        
        # 构建配置信息
        configs = []
        for config_id, config_file in _config_file_cache.items():
            try:
                # 读取配置文件基本信息
                with open(config_file, 'r', encoding='utf-8') as f:
                    config_data = yaml.safe_load(f)
                
                protocol_info = config_data.get('protocol', {})
                workflow_info = config_data.get('workflow', {})
                
                config_info = {
                    "id": config_id,
                    "name": protocol_info.get('name', f"Config {config_id}"),
                    "description": protocol_info.get('description', ''),
                    "version": protocol_info.get('version', '1.0.0'),
                    "author": protocol_info.get('author', ''),
                    "file_name": config_file.name,
                    "agents_count": len(config_data.get('agents', {})),
                    "nodes_count": len(config_data.get('nodes', [])),
                    "edges_count": len(config_data.get('edges', [])),
                    "cached": get_graph_manager().registry.get_graph(config_id) is not None
                }
                configs.append(config_info)
                
            except Exception as e:
                logger.error(f"读取配置文件信息失败 {config_file}: {e}")
                # 添加基础信息
                configs.append({
                    "id": config_id,
                    "name": f"Config {config_id}",
                    "description": f"配置文件读取失败: {str(e)}",
                    "version": "unknown",
                    "author": "",
                    "file_name": config_file.name,
                    "agents_count": 0,
                    "nodes_count": 0,
                    "edges_count": 0,
                    "cached": False
                })
        
        return {
            "configs": configs,
            "total": len(configs),
            "cached_count": sum(1 for c in configs if c["cached"]),
            "timestamp": datetime.now().isoformat()
        }
        
    except Exception as e:
        logger.exception(f"获取配置列表错误: {e}")
        raise HTTPException(status_code=500, detail=INTERNAL_SERVER_ERROR_DETAIL)


@app.get("/health", response_model=HealthResponse)
async def health_check():
    """健康检查接口"""
    try:
        # 确保配置文件映射已加载
        _load_config_file_mappings()
        
        manager = get_graph_manager()
        cached_configs = len(manager.registry.list_graphs())
        available_configs = len(_config_file_cache)
        
        return HealthResponse(
            status="healthy",
            message="KaFlow-Py 服务运行正常",
            timestamp=datetime.now(),
            configs_loaded=cached_configs
        )
        
    except Exception as e:
        logger.exception(f"健康检查错误: {e}")
        return HealthResponse(
            status="unhealthy",
            message=f"服务异常: {str(e)}",
            timestamp=datetime.now(),
            configs_loaded=0
        )


@app.get("/api/version")
async def get_version():
    """获取版本信息"""
    return {
        "name": "KaFlow-Py",
        "version": "1.0.0",
        "description": "配置驱动的 AI Agent 开发框架",
        "author": "DevYK",
        "timestamp": datetime.now().isoformat()
    }


@app.post("/api/mcp/server/metadata", response_model=MCPServerMetadataResponse)
async def mcp_server_metadata(request: MCPServerMetadataRequest):
    """
    获取 MCP 服务器元数据和工具列表
    
    该接口用于连接到 MCP 服务器并获取其提供的工具信息
    
    Args:
        request: MCP 服务器元数据请求
        
    Returns:
        MCPServerMetadataResponse: 包含服务器信息和工具列表
        
    Raises:
        HTTPException: 当连接失败或参数错误时
    """
    try:
        logger.info(f"接收到 MCP 服务器元数据请求: transport={request.transport}")
        
        # 设置默认超时时间
        timeout = request.timeout_seconds if request.timeout_seconds is not None else 300
        
        # 使用 mcp 模块中的 load_mcp_tools 函数加载工具
        tools = await load_mcp_tools(
            server_type=request.transport,
            command=request.command,
            args=request.args,
            url=request.url,
            env=request.env,
            timeout_seconds=timeout
        )
        
        logger.info(f"成功加载 {len(tools)} 个工具从 MCP 服务器")
        
        # 构建响应
        response = MCPServerMetadataResponse(
            transport=request.transport,
            command=request.command,
            args=request.args,
            url=request.url,
            env=request.env,
            tools=tools
        )
        
        return response
        
    except HTTPException:
        # 重新抛出 HTTPException
        raise
    except Exception as e:
        logger.exception(f"MCP 服务器元数据接口错误: {str(e)}")
        raise HTTPException(
            status_code=500, 
            detail=f"获取 MCP 服务器元数据失败: {str(e)}"
        )


# 启动时事件
@app.on_event("startup")
async def startup_event():
    """应用启动时执行"""
    logger.info("KaFlow-Py 服务启动中...")
    
    try:
        # 初始化配置文件映射（不预加载图）
        _load_config_file_mappings()
        
        available_configs = len(_config_file_cache)
        logger.info(f"发现 {available_configs} 个可用配置，将按需加载")
        logger.info("KaFlow-Py 服务启动完成")
        
    except Exception as e:
        logger.error(f"服务启动失败: {e}")
        raise


# 关闭时事件
@app.on_event("shutdown")
async def shutdown_event():
    """应用关闭时执行"""
    logger.info("KaFlow-Py 服务关闭中...")
    
    # 清理资源
    manager = get_graph_manager()
    manager.registry.clear()
    _config_file_cache.clear()
    
    logger.info("KaFlow-Py 服务已关闭")


if __name__ == "__main__":
    import uvicorn
    
    uvicorn.run(
        "src.server.app:app",
        host="0.0.0.0",
        port=8102,
        reload=True,
        log_level="info"
    )
