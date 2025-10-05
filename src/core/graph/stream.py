"""
KaFlow-Py 流式消息处理器

借鉴 agent-template 的优秀实践，处理 LangGraph astream 的各种消息类型
支持工具调用组装、消息块处理、错误处理等

Author: DevYK
微信公众号: DevYK
Email: yang1001yk@gmail.com
Github: https://github.com/yangkun19921001
"""

import asyncio
import json
import logging
from typing import Dict, Any, List, Optional, AsyncGenerator, cast, Tuple
from uuid import uuid4

from langchain_core.messages import (
    AIMessageChunk, 
    BaseMessage, 
    ToolMessage, 
    HumanMessage, 
    AIMessage
)

from .builder import GraphStreamEvent
from ...utils.logger import get_logger

logger = get_logger(__name__)


class ToolCallChunksAssembler:
    """工具调用块组装器 - 将分散的 tool_call_chunks 组装成完整的 tool_call"""
    
    def __init__(self):
        self.reset()
    
    def reset(self):
        """重置组装器状态"""
        self.assembling = False  # 是否正在组装
        self.current_tool_call = None  # 当前组装的工具调用
        self.accumulated_args = ""  # 累积的参数字符串
        
    def should_start_assembling(self, event_stream_message: dict) -> bool:
        """判断是否应该开始组装 - 检查是否有带 name 的 tool_call_chunks 或不完整的 tool_calls"""
        # 情况1：只有 tool_call_chunks 且有 name
        if event_stream_message.get("tool_call_chunks") and not event_stream_message.get("tool_calls"):
            chunks = event_stream_message["tool_call_chunks"]
            for chunk in chunks:
                # 如果有带 name 的 chunk，开始组装
                if chunk.get("name") and chunk.get("name") not in [None, "null", ""]:
                    return True
        
        # 情况2：有不完整的 tool_calls + tool_call_chunks
        elif (event_stream_message.get("tool_calls") and 
              event_stream_message.get("tool_call_chunks")):
            tool_calls = event_stream_message["tool_calls"]
            # 检查 tool_calls 是否不完整（name为空或args为空）
            for tool_call in tool_calls:
                name = tool_call.get("name")
                args = tool_call.get("args")
                
                # 检查 name 是否为空（None、空字符串、或 "null"）
                name_is_empty = (name is None or name == "" or name == "null")
                
                # 检查 args 是否为空（None 或空字典）
                args_is_empty = (args is None or args == {})
                if name_is_empty or args_is_empty:
                    return True
        
        return False
    
    def should_finalize_assembling(self, event_stream_message: dict) -> bool:
        """判断是否应该完成组装 - 检查是否收到完整的 tool_calls"""
        # 如果收到完整的 tool_calls（有 tool_calls 但没有 tool_call_chunks，或者 tool_calls 已经有完整信息）
        if event_stream_message.get("tool_calls") and not event_stream_message.get("tool_call_chunks"):
            return True
        elif event_stream_message.get("tool_calls"):
            # 检查 tool_calls 是否已经有完整的参数
            tool_calls = event_stream_message["tool_calls"]
            for tool_call in tool_calls:
                if (tool_call.get("args") and 
                    isinstance(tool_call.get("args"), dict) and 
                    len(tool_call.get("args", {})) > 0):
                    return True
        return False
    
    def should_stop_assembling(self, event_stream_message: dict) -> bool:
        """判断是否应该停止组装 - 检查是否收到 finish_reason: tool_calls"""
        return (not event_stream_message.get("tool_call_chunks") and 
                event_stream_message.get("finish_reason") == "tool_calls")
    
    def start_assembling(self, event_stream_message: dict):
        """开始组装 tool_call"""
        self.assembling = True
        self.accumulated_args = ""
        
        # 从 tool_calls 和 tool_call_chunks 中提取信息
        tool_call_id = None
        tool_call_name = ""
        
        # 从 tool_calls 中获取基础信息
        if event_stream_message.get("tool_calls"):
            first_tool_call = event_stream_message["tool_calls"][0]
            tool_call_id = first_tool_call.get("id")
            # 如果 tool_calls 中有 name 且不为空，使用它
            if first_tool_call.get("name") and first_tool_call.get("name") != "":
                tool_call_name = first_tool_call.get("name")
        
        # 从 tool_call_chunks 中获取更详细信息
        if event_stream_message.get("tool_call_chunks"):
            first_chunk = event_stream_message["tool_call_chunks"][0]
            logger.debug(f"🔍 第一个 chunk 详情: {first_chunk}")
            
            # 如果 chunks 中有 id，优先使用
            if first_chunk.get("id"):
                tool_call_id = first_chunk.get("id")
            # 如果 chunks 中有 name 且不为空/null，优先使用
            if first_chunk.get("name") and first_chunk.get("name") not in [None, "null", ""]:
                tool_call_name = first_chunk.get("name")
            
            # 累积第一个chunk的args
            chunk_args = first_chunk.get("args")
            
            if chunk_args:
                self.accumulated_args += chunk_args
                logger.debug(f"🔍 开始组装后累积参数: '{self.accumulated_args}'")
            else:
                logger.debug(f"🔍 第一个 chunk args 为空或假值，跳过累积: {chunk_args}")
        else:
            logger.debug("🔍 没有找到 tool_call_chunks")
        
        self.current_tool_call = {
            "id": tool_call_id,
            "name": tool_call_name,
            "args": {},
            "type": "function"
        }
        
    def accumulate_chunk(self, event_stream_message: dict):
        """累积 tool_call_chunks 的 args"""
        if event_stream_message.get("tool_call_chunks"):
            logger.debug(f"🔍 累积前参数: '{self.accumulated_args}'")
            for chunk in event_stream_message["tool_call_chunks"]:
                if chunk.get("args"):
                    chunk_args = chunk["args"]
                    logger.debug(f"🔍 累积 chunk args: '{chunk_args}'")
                    self.accumulated_args += chunk_args
            logger.debug(f"🔍 累积后参数: '{self.accumulated_args}'")
        
        logger.debug(f"累积参数: {self.accumulated_args[:100]}...")
    
    def finalize_tool_call(self, base_event_message: dict) -> dict:
        """完成组装并返回完整的 tool_call 事件"""
        if not self.current_tool_call:
            return None
        
        # 从最终的 tool_calls 中更新工具信息（如 name）
        if base_event_message.get("tool_calls"):
            self.update_tool_info_from_final_call(base_event_message["tool_calls"])
            
        # 尝试解析累积的参数为 JSON
        try:
            if self.accumulated_args.strip():
                self.current_tool_call["args"] = json.loads(self.accumulated_args)
            else:
                self.current_tool_call["args"] = {}
        except json.JSONDecodeError as e:
            logger.warning(f"无法解析工具调用参数为JSON: {e}, 原始参数: {self.accumulated_args}")
            self.current_tool_call["args"] = {"raw_args": self.accumulated_args}
        
        # 创建完整的 tool_call 事件
        assembled_event = {
            "thread_id": base_event_message.get("thread_id"),
            "agent": base_event_message.get("agent"),
            "id": base_event_message.get("id"),
            "role": "assistant",
            "tool_calls": [self.current_tool_call],
            "finish_reason": "tool_calls"
        }
        
        logger.info(f"完成组装 tool_call: {self.current_tool_call['name']}, "
                   f"参数长度: {len(str(self.current_tool_call['args']))}")
        
        # 重置状态
        assembled_tool_call = self.current_tool_call.copy()
        self.reset()
        
        return assembled_event
    
    def is_assembling(self) -> bool:
        """检查是否正在组装"""
        return self.assembling

    def update_tool_info_from_final_call(self, final_tool_calls):
        """从最终的 tool_calls 中更新工具信息（如 name）"""
        if self.current_tool_call and final_tool_calls:
            final_call = final_tool_calls[0]  # 假设只有一个工具调用
            # 如果当前没有 name 但最终调用有 name，更新它
            if not self.current_tool_call.get("name") and final_call.get("name"):
                self.current_tool_call["name"] = final_call.get("name")
                logger.debug(f"更新工具名称: {final_call.get('name')}")
            # 更新 id（如果需要）
            if not self.current_tool_call.get("id") and final_call.get("id"):
                self.current_tool_call["id"] = final_call.get("id")


class StreamMessageProcessor:
    """流式消息处理器"""
    
    def __init__(self, graph_id: str, thread_id: str = None):
        self.graph_id = graph_id
        self.thread_id = thread_id or str(uuid4())
        self.logger = get_logger(__name__)
        self.assembler = ToolCallChunksAssembler()
    
    def _make_event(self, event_type: str, data: dict) -> str:
        """生成SSE事件格式的字符串 - 完全复制app.py的逻辑"""
        if data.get("content") == "":
            data.pop("content")
        
        return f"event: {event_type}\ndata: {json.dumps(data, ensure_ascii=False)}\n\n"
    
    def _clean_tool_call_id(self, raw_tool_call_id: str) -> str:
        """清理重复累积的 tool_call_id - 完全复制app.py的逻辑"""
        clean_tool_call_id = raw_tool_call_id
        
        if raw_tool_call_id:
            # 检查是否存在重复累积的情况
            if raw_tool_call_id.startswith('call_'):
                # OpenAI格式的ID：call_xxx
                # 查找第一个完整的call_xxx
                parts = raw_tool_call_id.split('call_')
                if len(parts) > 2:  # 有重复
                    clean_tool_call_id = 'call_' + parts[1]
            elif len(raw_tool_call_id) >= 64:  # 32字符hex重复的情况
                # 检查是否是重复的32字符hex字符串
                first_32 = raw_tool_call_id[:32]
                if raw_tool_call_id == first_32 * (len(raw_tool_call_id) // 32):
                    clean_tool_call_id = first_32
            
            # 记录清理信息
            if raw_tool_call_id != clean_tool_call_id:
                logger.warning(f"🔧 清理重复累积的 tool_call_id: 原始长度={len(raw_tool_call_id)}, 清理后='{clean_tool_call_id}'")
        
        return clean_tool_call_id
    
    async def process_astream(self, compiled_graph, initial_state: Dict[str, Any]) -> AsyncGenerator[str, None]:
        """
        处理 LangGraph astream 输出，生成与app.py完全一致的SSE流式事件
        
        Args:
            compiled_graph: 编译后的 LangGraph
            initial_state: 初始状态
            
        Yields:
            str: SSE格式的事件字符串
        """
        # 发送开始事件
        # yield self._make_event("graph_start", {
        #     "graph_id": self.graph_id, 
        #     "thread_id": self.thread_id
        # })
        
        try:
            # 获取当前任务，用于检测取消
            current_task = asyncio.current_task()
            event_count = 0
            # 完全复制app.py的astream处理逻辑
            async for agent, mode, event_data in compiled_graph.astream(
                initial_state,
                config={
                    "configurable": {"thread_id": self.thread_id},
                },
                stream_mode=["messages"],
                subgraphs=True,
            ):
                # 检测任务是否被取消
                if current_task and current_task.cancelled():
                    logger.info(f"🛑 检测到任务取消，已处理 {event_count} 个事件")
                    yield self._make_event("cancelled", {
                        "thread_id": self.thread_id,
                        "graph_id": self.graph_id,
                        "message": "生成已停止",
                        "events_processed": event_count
                    })
                    break
                
                event_count += 1
                # logger.debug(f"🔍 收到 agent: {agent}, mode: {mode}, event_data: {event_data}")
                
                # 处理中断事件 - 完全复制app.py逻辑
                if isinstance(event_data, dict):
                    if "__interrupt__" in event_data:
                        yield self._make_event("interrupt", {
                            "thread_id": self.thread_id,
                            "id": event_data["__interrupt__"][0].ns[0],
                            "role": "assistant",
                            "content": event_data["__interrupt__"][0].value,
                            "finish_reason": "interrupt",
                            "options": [
                                {"text": "Edit plan", "value": "edit_plan"},
                                {"text": "Start research", "value": "accepted"},
                            ],
                        })
                    continue
                
                # 处理消息事件 - 完全复制app.py逻辑
                message_chunk, message_metadata = cast(
                    tuple[BaseMessage, dict[str, any]], event_data
                )
                
                # 处理agent名称 - 完全复制app.py逻辑
                agent_name = "unknown"
                if agent and len(agent) > 0:
                    agent_name = agent[0].split(":")[0] if ":" in agent[0] else agent[0]

                if agent_name == "unknown":
                    agent_name = message_metadata.get("langgraph_node")

                # 构建基础事件消息 - 完全复制app.py逻辑
                event_stream_message: dict[str, any] = {
                    "thread_id": self.thread_id,
                    "agent": agent_name,
                    "id": message_chunk.id,
                    "role": "assistant",
                    "content": message_chunk.content,
                }
                
                # 添加推理内容 - 完全复制app.py逻辑
                if message_chunk.additional_kwargs.get("reasoning_content"):
                    event_stream_message["reasoning_content"] = message_chunk.additional_kwargs[
                        "reasoning_content"
                    ]
                
                # 添加完成原因 - 完全复制app.py逻辑
                if message_chunk.response_metadata.get("finish_reason"):
                    event_stream_message["finish_reason"] = message_chunk.response_metadata.get(
                        "finish_reason"
                    )
                
                # 处理工具消息 - 完全复制app.py逻辑
                if isinstance(message_chunk, ToolMessage):
                    # 清理重复累积的 tool_call_id
                    raw_tool_call_id = message_chunk.tool_call_id
                    clean_tool_call_id = self._clean_tool_call_id(raw_tool_call_id)
                    
                    event_stream_message["tool_call_id"] = clean_tool_call_id
                    yield self._make_event("tool_call_result", event_stream_message)
                
                # 处理AI消息块 - 完全复制app.py逻辑
                elif isinstance(message_chunk, AIMessageChunk):
                    # 处理工具调用 - 完全复制app.py逻辑
                    if message_chunk.tool_calls:
                        event_stream_message["tool_calls"] = message_chunk.tool_calls
                        event_stream_message["tool_call_chunks"] = (
                            message_chunk.tool_call_chunks
                        )

                        # 如果正在组装，检查是否应该完成组装
                        if self.assembler.is_assembling() and self.assembler.should_finalize_assembling(event_stream_message):
                            assembled_event = self.assembler.finalize_tool_call(event_stream_message)
                            if assembled_event:
                                yield self._make_event("tool_calls", assembled_event)
                            continue
                        
                        # 如果正在组装但不应该完成组装，继续累积
                        elif self.assembler.is_assembling():
                            if event_stream_message.get("tool_call_chunks"):
                                has_useful_args = False
                                for chunk in event_stream_message["tool_call_chunks"]:
                                    if chunk.get("args"):
                                        has_useful_args = True
                                        break
                                
                                if has_useful_args:
                                    self.assembler.accumulate_chunk(event_stream_message)
                            continue
                        
                        # 如果不在组装状态，检查是否应该开始组装
                        elif not self.assembler.is_assembling() and self.assembler.should_start_assembling(event_stream_message):
                            self.assembler.start_assembling(event_stream_message)
                            
                            # 处理剩余的chunks
                            if event_stream_message.get("tool_call_chunks") and len(event_stream_message["tool_call_chunks"]) > 1:
                                remaining_chunks_event = {
                                    "tool_call_chunks": event_stream_message["tool_call_chunks"][1:]
                                }
                                self.assembler.accumulate_chunk(remaining_chunks_event)
                            
                            continue
                        
                        # 安全检查：确保不发送不完整的 tool_calls
                        tool_calls = event_stream_message.get("tool_calls", [])
                        has_incomplete_tool_call = False
                        
                        for tool_call in tool_calls:
                            name = tool_call.get("name")
                            args = tool_call.get("args")
                            
                            if (name is None or name == "" or name == "null") or (args is None or args == {}):
                                has_incomplete_tool_call = True
                                break
                        
                        if has_incomplete_tool_call:
                            if not self.assembler.is_assembling():
                                self.assembler.start_assembling(event_stream_message)
                            continue
                        
                        yield self._make_event("tool_calls", event_stream_message)
                    
                    # 处理工具调用块 - 完全复制app.py逻辑
                    elif message_chunk.tool_call_chunks:
                        event_stream_message["tool_call_chunks"] = message_chunk.tool_call_chunks
                        
                        # 检查是否应该开始组装
                        if not self.assembler.is_assembling() and self.assembler.should_start_assembling(event_stream_message):
                            self.assembler.start_assembling(event_stream_message)
                            continue
                        
                        # 如果正在组装，累积参数
                        elif self.assembler.is_assembling():
                            self.assembler.accumulate_chunk(event_stream_message)
                            continue
                        
                        # 正常发送 tool_call_chunks 事件
                        else:
                            yield self._make_event("tool_call_chunks", event_stream_message)
                    
                    # 处理普通消息 - 完全复制app.py逻辑
                    else:
                        # 忽略空的 message_chunk
                        if not event_stream_message.get("content") and not event_stream_message.get("finish_reason"):
                            continue
                        
                        # 检查是否应该结束组装
                        if self.assembler.is_assembling() and self.assembler.should_stop_assembling(event_stream_message):
                            assembled_event = self.assembler.finalize_tool_call(event_stream_message)
                            if assembled_event:
                                yield self._make_event("tool_calls", assembled_event)
                            continue
                        
                        # 正常的消息块
                        yield self._make_event("message_chunk", event_stream_message)

            # 发送完成事件
            # yield self._make_event("graph_end", {
            #     "status": "completed", 
            #     "graph_id": self.graph_id
            # })
            
        except asyncio.CancelledError:
            self.logger.info(f"🛑 流式处理被取消 (graph_id: {self.graph_id})")
            yield self._make_event("cancelled", {
                "thread_id": self.thread_id,
                "graph_id": self.graph_id,
                "message": "用户已取消生成",
                "events_processed": event_count if 'event_count' in locals() else 0
            })
            # 不再重新抛出异常，优雅地结束
            
        except Exception as e:
            self.logger.error(f"流式处理失败: {e}")
            yield self._make_event("error", {
                "error": str(e), 
                "graph_id": self.graph_id
            })


__all__ = [
    "ToolCallChunksAssembler",
    "StreamMessageProcessor",
] 