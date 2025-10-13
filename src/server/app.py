"""
KaFlow-Py FastAPI 服务端应用

基于配置驱动的 AI Agent 开发框架 Web API
实现基于 YAML 配置文件中 id 字段的按需加载和缓存机制

Author: DevYK
微信公众号: DevYK
Email: yang1001yk@gmail.com
Github: https://github.com/yangkun19921001
"""

import asyncio
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
    MCPServerMetadataResponse,
    HistoryMessageRequest,
    HistoryMessageResponse,
    FlatMessageRequest,
    FlatMessageResponse,
    ThreadListRequest,
    ThreadListResponse
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


def _get_config_file_by_id(config_id: str) -> Optional[Path]:
    """根据配置ID获取配置文件路径"""
    _load_config_file_mappings()
    return _config_file_cache.get(str(config_id))


def _extract_config_id_from_thread_id(thread_id: str) -> Optional[str]:
    """
    从 thread_id 中提取 config_id
    
    thread_id 格式: username_uuid_configid
    例如: admin_12345678-1234-1234-1234-123456789012_ops_agent
    
    策略：
    1. 按 _ 分割
    2. 从最后一个部分开始，尝试匹配已知的 config_id
    3. 如果最后一个部分不是有效的 config_id，尝试最后两个/三个部分组合
    """
    if not thread_id:
        return None
    
    parts = thread_id.split('_')
    if len(parts) < 3:
        return None
    
    # 加载配置文件映射
    _load_config_file_mappings()
    
    # 策略1: 尝试最后一个部分
    last_part = parts[-1]
    if last_part in _config_file_cache:
        logger.info(f"✅ 从 thread_id 解析出 config_id: {last_part}")
        return last_part
    
    # 策略2: 尝试最后两个部分（处理 config_id 中包含下划线的情况，如 ops_agent）
    if len(parts) >= 2:
        last_two = '_'.join(parts[-2:])
        if last_two in _config_file_cache:
            logger.info(f"✅ 从 thread_id 解析出 config_id: {last_two}")
            return last_two
    
    # 策略3: 尝试最后三个部分
    if len(parts) >= 3:
        last_three = '_'.join(parts[-3:])
        if last_three in _config_file_cache:
            logger.info(f"✅ 从 thread_id 解析出 config_id: {last_three}")
            return last_three
    
    logger.warning(f"⚠️  无法从 thread_id 中解析出有效的 config_id: {thread_id}")
    return None


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
        
        logger.info(f"开始流式生成 (config_id: {config_id}, thread_id: {thread_id})")
        event_count = 0
        
        # 使用图管理器的流式执行
        async for sse_event_string in manager.execute_graph_stream(
            graph_id=config_id,
            user_input=user_input,
            messages=messages,
            thread_id=thread_id,
            **(custom_config or {})
        ):
            # 正确：直接 yield 已格式化的 SSE 字符串
            event_count += 1
            yield sse_event_string
        
        logger.info(f"流式生成完成 (config_id: {config_id}, events: {event_count})")
            
    except asyncio.CancelledError:
        logger.info(f"🛑 流式生成被取消 (config_id: {config_id}, thread_id: {thread_id})")
        # 客户端断开连接时，不发送任何内容，直接结束
        
    except Exception as e:
        logger.error(f"流式生成器错误: {e}")
        error_data = {"error": str(e), "config_id": config_id}
        yield f"event: error\ndata: {json.dumps(error_data, ensure_ascii=False)}\n\n"


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


@app.post("/api/chat/history", response_model=HistoryMessageResponse)
async def get_chat_history(request: HistoryMessageRequest):
    """
    获取历史对话消息（支持分页）
    
    此接口从 MongoDB 持久化存储中获取历史对话记录。
    
    参数：
    - thread_id: 会话线程ID（必需，格式: username_uuid_configid）
    - page: 页码，从1开始（默认：1）
    - page_size: 每页大小，1-100（默认：20）
    - order: 排序方式，desc（最新在前）或asc（最早在前）（默认：desc）
    - config_id: 配置ID（可选，如果不提供则自动从 thread_id 中解析）
    
    返回：
    - thread_id: 会话线程ID
    - total: 总记录数
    - page: 当前页码
    - page_size: 每页大小
    - total_pages: 总页数
    - messages: 消息列表
    
    注意：
    - thread_id 格式为 username_uuid_configid，会自动从中提取 config_id
    - 只有配置了 MongoDB memory provider 的场景才能获取历史消息
    - 使用 memory provider 的场景无法持久化历史
    """
    try:
        logger.info(f"📝 获取历史消息: thread_id={request.thread_id}, page={request.page}, page_size={request.page_size}, config_id={request.config_id}")
        
        manager = get_graph_manager()
        checkpointer = None
        used_config_id = request.config_id
        
        # 优先级1：如果没有提供 config_id，尝试从 thread_id 中解析
        if not used_config_id:
            used_config_id = _extract_config_id_from_thread_id(request.thread_id)
            if used_config_id:
                logger.info(f"🎯 从 thread_id 中解析出 config_id: {used_config_id}")
        
        # 优先级2：如果有 config_id（无论是请求提供还是从 thread_id 解析出来的），使用该配置
        if used_config_id:
            logger.info(f"🔧 使用配置 ID: {used_config_id}")
            
            # 检查是否已加载
            compiled_graph = manager.registry.get_graph(used_config_id)
            if not compiled_graph:
                # 未加载，尝试加载
                logger.info(f"⏳ 配置 {used_config_id} 未加载，正在加载...")
                config_file = _get_config_file_by_id(used_config_id)
                if config_file:
                    manager.register_graph_from_file(config_file, used_config_id)
                    compiled_graph = manager.registry.get_graph(used_config_id)
                    logger.info(f"✅ 配置 {used_config_id} 加载成功")
                else:
                    raise HTTPException(
                        status_code=404,
                        detail=f"配置 ID {used_config_id} 不存在"
                    )
            
            if compiled_graph and hasattr(compiled_graph, "checkpointer"):
                checkpointer = compiled_graph.checkpointer
                logger.info(f"✅ 找到 checkpointer: {type(checkpointer).__name__}")
        
        # 优先级3：自动查找配置了 MongoDB 的场景（作为后备方案）
        else:
            logger.info("未指定 config_id，自动查找配置了 MongoDB 的场景")
            
            # 先从已加载的图中查找
            for config_id, compiled_graph in manager.registry._graphs.items():
                if compiled_graph and hasattr(compiled_graph, "checkpointer"):
                    temp_checkpointer = compiled_graph.checkpointer
                    if temp_checkpointer and hasattr(temp_checkpointer, "get_history_messages"):
                        checkpointer = temp_checkpointer
                        used_config_id = config_id
                        logger.info(f"找到已加载的 MongoDB checkpointer: {config_id}")
                        break
            
            # 如果没有找到，扫描所有配置文件
            if not checkpointer:
                logger.info("已加载的图中未找到，扫描配置文件...")
                _load_config_file_mappings()
                
                for config_id, config_file in _config_file_cache.items():
                    try:
                        # 读取配置文件检查是否配置了 MongoDB
                        with open(config_file, 'r', encoding='utf-8') as f:
                            import yaml
                            config_data = yaml.safe_load(f)
                        
                        # 检查是否配置了 MongoDB memory
                        memory_config = config_data.get('global_config', {}).get('memory', {})
                        if (memory_config.get('enabled') and 
                            memory_config.get('provider') == 'mongodb'):
                            logger.info(f"找到配置了 MongoDB 的场景: {config_id}")
                            
                            # 加载该配置
                            manager.register_graph_from_file(config_file, config_id)
                            compiled_graph = manager.registry.get_graph(config_id)
                            
                            if compiled_graph and hasattr(compiled_graph, "checkpointer"):
                                checkpointer = compiled_graph.checkpointer
                                used_config_id = config_id
                                break
                    except Exception as e:
                        logger.warning(f"检查配置文件 {config_id} 失败: {e}")
                        continue
        
        # 验证 checkpointer
        if not checkpointer or not hasattr(checkpointer, "get_history_messages"):
            raise HTTPException(
                status_code=400,
                detail={
                    "error": "no_mongodb_configured",
                    "message": "未找到配置了 MongoDB 的场景。请确保至少有一个场景配置了 MongoDB memory provider。",
                    "suggestion": "在 YAML 配置中添加: global_config.memory.provider = 'mongodb'",
                    "available_configs": list(_config_file_cache.keys())
                }
            )
        
        # 调用 checkpointer 的方法获取历史消息
        result = checkpointer.get_history_messages(
            thread_id=request.thread_id,
            page=request.page,
            page_size=request.page_size,
            order=request.order
        )
        
        logger.info(f"✅ 获取历史消息成功: config_id={used_config_id}, total={result.get('total')}, page={result.get('page')}")
        
        # 添加使用的 config_id 到结果中（用于调试）
        if used_config_id:
            result['config_id'] = used_config_id
        
        return HistoryMessageResponse(**result)
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ 获取历史消息失败: {e}")
        import traceback
        logger.error(traceback.format_exc())
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/chat/messages", response_model=FlatMessageResponse)
async def get_flat_messages(request: FlatMessageRequest):
    """
    获取展平的消息列表（按单条消息分页）
    
    与 /api/chat/history 不同，此接口：
    - 返回单条消息列表，而不是 checkpoint 列表
    - 从最新的 checkpoint 中提取所有消息
    - 按单条消息进行分页
    
    参数：
    - thread_id: 会话线程ID（必需，格式: username_uuid_configid）
    - page: 页码，从1开始（默认：1）
    - page_size: 每页大小，1-100（默认：20）
    - order: 排序方式，desc（最新在前）或asc（最早在前）（默认：desc）
    - config_id: 配置ID（可选，如果不提供则自动从 thread_id 中解析）
    
    返回：
    - thread_id: 会话线程ID
    - total: 总消息数
    - page: 当前页码
    - page_size: 每页大小
    - total_pages: 总页数
    - messages: 单条消息列表
    
    注意：
    - 只有配置了 MongoDB memory provider 的场景才能获取消息
    - 适用于显示对话历史的 UI 场景
    """
    try:
        logger.info(f"📨 获取展平消息: thread_id={request.thread_id}, page={request.page}, page_size={request.page_size}")
        
        manager = get_graph_manager()
        checkpointer = None
        used_config_id = request.config_id
        
        # 优先级1：如果没有提供 config_id，尝试从 thread_id 中解析
        if not used_config_id:
            used_config_id = _extract_config_id_from_thread_id(request.thread_id)
            if used_config_id:
                logger.info(f"🎯 从 thread_id 中解析出 config_id: {used_config_id}")
        
        # 优先级2：如果有 config_id，使用该配置
        if used_config_id:
            logger.info(f"🔧 使用配置 ID: {used_config_id}")
            
            # 检查是否已加载
            compiled_graph = manager.registry.get_graph(used_config_id)
            if not compiled_graph:
                # 未加载，尝试加载
                logger.info(f"⏳ 配置 {used_config_id} 未加载，正在加载...")
                config_file = _get_config_file_by_id(used_config_id)
                if config_file:
                    manager.register_graph_from_file(config_file, used_config_id)
                    compiled_graph = manager.registry.get_graph(used_config_id)
                    logger.info(f"✅ 配置 {used_config_id} 加载成功")
                else:
                    raise HTTPException(
                        status_code=404,
                        detail=f"配置 ID {used_config_id} 不存在"
                    )
            
            if compiled_graph and hasattr(compiled_graph, "checkpointer"):
                checkpointer = compiled_graph.checkpointer
                logger.info(f"✅ 找到 checkpointer: {type(checkpointer).__name__}")
        
        # 优先级3：自动查找配置了 MongoDB 的场景
        else:
            logger.info("📂 未指定 config_id，自动查找配置了 MongoDB 的场景")
            _load_config_file_mappings()
            
            for config_id, config_file in _config_file_cache.items():
                try:
                    with open(config_file, 'r', encoding='utf-8') as f:
                        import yaml
                        config_data = yaml.safe_load(f)
                    
                    memory_config = config_data.get('global_config', {}).get('memory', {})
                    if (memory_config.get('enabled') and 
                        memory_config.get('provider') == 'mongodb'):
                        logger.info(f"🎯 找到配置了 MongoDB 的场景: {config_id}")
                        
                        manager.register_graph_from_file(config_file, config_id)
                        compiled_graph = manager.registry.get_graph(config_id)
                        
                        if compiled_graph and hasattr(compiled_graph, "checkpointer"):
                            checkpointer = compiled_graph.checkpointer
                            used_config_id = config_id
                            break
                except Exception as e:
                    logger.warning(f"⚠️  检查配置文件 {config_id} 失败: {e}")
                    continue
        
        # 验证 checkpointer
        if not checkpointer or not hasattr(checkpointer, "get_flat_messages"):
            raise HTTPException(
                status_code=400,
                detail={
                    "error": "no_mongodb_configured",
                    "message": "未找到配置了 MongoDB 的场景。",
                    "suggestion": "在 YAML 配置中添加: global_config.memory.provider = 'mongodb'",
                    "available_configs": list(_config_file_cache.keys())
                }
            )
        
        # 调用 checkpointer 的方法获取展平消息
        result = checkpointer.get_flat_messages(
            thread_id=request.thread_id,
            page=request.page,
            page_size=request.page_size,
            order=request.order
        )
        
        logger.info(f"✅ 获取展平消息成功: config_id={used_config_id}, total={result.get('total')}, page={result.get('page')}")
        
        # 添加使用的 config_id 到结果中
        if used_config_id:
            result['config_id'] = used_config_id
        
        return FlatMessageResponse(**result)
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ 获取展平消息失败: {e}")
        import traceback
        logger.error(traceback.format_exc())
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/chat/threads", response_model=ThreadListResponse)
async def get_thread_list(request: ThreadListRequest):
    """
    获取会话列表（支持按用户筛选或获取所有会话）
    
    此接口用于显示历史会话，每个会话包含第一条消息作为预览。
    
    参数：
    - username: 用户名（可选，不传则返回所有用户的会话）
    - page: 页码，从1开始（默认：1）
    - page_size: 每页大小，1-100（默认：20）
    - order: 排序方式，desc（最新在前）或asc（最早在前）（默认：desc）
    
    返回：
    - username: 用户名（如果查询时指定了用户）
    - total: 总会话数
    - page: 当前页码
    - page_size: 每页大小
    - total_pages: 总页数
    - threads: 会话列表（每个会话包含 thread_id、username、first_message 等）
    
    注意：
    - 只有配置了 MongoDB memory provider 的场景才能获取会话列表
    - 会话按最后更新时间排序
    - 如果不传 username，将返回所有用户的会话（管理员视图）
    """
    try:
        filter_desc = f"username={request.username}" if request.username else "所有用户"
        logger.info(f"📋 获取会话列表: {filter_desc}, page={request.page}, page_size={request.page_size}")
        
        manager = get_graph_manager()
        checkpointer = None
        used_config_id = None
        
        # 查找配置了 MongoDB 的场景
        # 方法1：先从已加载的图中查找
        for config_id, compiled_graph in manager.registry._graphs.items():
            if compiled_graph and hasattr(compiled_graph, "checkpointer"):
                temp_checkpointer = compiled_graph.checkpointer
                if temp_checkpointer and hasattr(temp_checkpointer, "get_thread_list"):
                    checkpointer = temp_checkpointer
                    used_config_id = config_id
                    logger.info(f"✅ 找到已加载的 MongoDB checkpointer: {config_id}")
                    break
        
        # 方法2：如果没有找到，扫描所有配置文件
        if not checkpointer:
            logger.info("📂 已加载的图中未找到，扫描配置文件...")
            _load_config_file_mappings()
            
            for config_id, config_file in _config_file_cache.items():
                try:
                    # 读取配置文件检查是否配置了 MongoDB
                    with open(config_file, 'r', encoding='utf-8') as f:
                        import yaml
                        config_data = yaml.safe_load(f)
                    
                    # 检查是否配置了 MongoDB memory
                    memory_config = config_data.get('global_config', {}).get('memory', {})
                    if (memory_config.get('enabled') and 
                        memory_config.get('provider') == 'mongodb'):
                        logger.info(f"🎯 找到配置了 MongoDB 的场景: {config_id}")
                        
                        # 加载该配置
                        manager.register_graph_from_file(config_file, config_id)
                        compiled_graph = manager.registry.get_graph(config_id)
                        
                        if compiled_graph and hasattr(compiled_graph, "checkpointer"):
                            checkpointer = compiled_graph.checkpointer
                            used_config_id = config_id
                            break
                except Exception as e:
                    logger.warning(f"⚠️  检查配置文件 {config_id} 失败: {e}")
                    continue
        
        # 验证 checkpointer
        if not checkpointer or not hasattr(checkpointer, "get_thread_list"):
            raise HTTPException(
                status_code=400,
                detail={
                    "error": "no_mongodb_configured",
                    "message": "未找到配置了 MongoDB 的场景。请确保至少有一个场景配置了 MongoDB memory provider。",
                    "suggestion": "在 YAML 配置中添加: global_config.memory.provider = 'mongodb'",
                    "available_configs": list(_config_file_cache.keys())
                }
            )
        
        # 调用 checkpointer 的方法获取会话列表
        result = checkpointer.get_thread_list(
            username=request.username,
            page=request.page,
            page_size=request.page_size,
            order=request.order
        )
        
        logger.info(f"✅ 获取会话列表成功: username={request.username}, total={result.get('total')}, page={result.get('page')}")
        
        return ThreadListResponse(**result)
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ 获取会话列表失败: {e}")
        import traceback
        logger.error(traceback.format_exc())
        raise HTTPException(status_code=500, detail=str(e))


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
    
    # 🎯 关闭 MongoDB 共享客户端（如果使用了 MongoDB）
    try:
        from src.memory.mongodb_checkpointer import MongoDBCheckpointer
        MongoDBCheckpointer.close_shared_client()
        logger.info("✅ MongoDB 共享客户端已关闭")
    except Exception as e:
        logger.debug(f"关闭 MongoDB 客户端时出错（可能未使用 MongoDB）: {e}")
    
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
