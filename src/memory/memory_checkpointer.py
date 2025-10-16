"""
KaFlow-Py MemoryCheckpointer

基于内存的 Checkpointer 实现（使用 LangGraph 的 MemorySaver）

Author: DevYK
微信公众号: DevYK
Email: yang1001yk@gmail.com
Github: https://github.com/yangkun19921001
"""

from typing import Optional, Dict, Any
import pickle
from collections import defaultdict
from datetime import datetime, timezone, timedelta
from langgraph.checkpoint.memory import MemorySaver
from .base import BaseCheckpointer
from ..utils.logger import get_logger

logger = get_logger(__name__)


class MemoryCheckpointer(MemorySaver, BaseCheckpointer):
    """
    内存 Checkpointer 实现
    
    特点：
    - 数据存储在进程内存中
    - 重启后数据丢失
    - 适合开发和测试环境
    - 性能最高
    
    使用场景：
    - 本地开发调试
    - 不需要持久化的临时对话
    - 性能测试
    """
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """
        初始化内存 Checkpointer
        
        Args:
            config: 配置字典（内存模式不需要配置）
        """
        MemorySaver.__init__(self)
        BaseCheckpointer.__init__(self, config)
        self._is_connected = True  # 内存模式始终连接
        logger.info("✅ MemoryCheckpointer 初始化成功（内存模式）")
    
    async def setup(self) -> None:
        """内存模式无需设置"""
        logger.debug("MemoryCheckpointer: 无需设置（内存模式）")
    
    async def teardown(self) -> None:
        """内存模式无需清理"""
        logger.debug("MemoryCheckpointer: 无需清理（内存模式）")
    
    @property
    def is_connected(self) -> bool:
        """内存模式始终连接"""
        return True
    
    def validate_config(self) -> bool:
        """内存模式无需验证配置"""
        return True
    
    # ==================== 历史消息查询方法实现 ====================
    
    @staticmethod
    def _extract_username_from_thread_id(thread_id: str) -> Optional[str]:
        """
        从 thread_id 中提取 username
        
        thread_id 格式: username_uuid_configid
        """
        if not thread_id:
            return None
        
        parts = thread_id.split('_')
        if len(parts) < 3:
            return None
        
        username = parts[0]
        return username if username else None
    
    @staticmethod
    def _get_cn_time() -> datetime:
        """获取东八区（中国）时间"""
        cn_tz = timezone(timedelta(hours=8))
        return datetime.now(cn_tz)
    
    def _format_messages(self, messages: list) -> list:
        """
        格式化消息列表，转换为 API 友好的格式
        
        Args:
            messages: LangGraph 消息列表
            
        Returns:
            格式化后的消息列表（已去重）
        """
        formatted = []
        seen_human_contents = set()
        duplicate_count = 0
        
        for msg in messages:
            try:
                msg_type = type(msg).__name__
                
                message_data = {
                    "type": msg_type,
                    "content": "",
                    "additional_kwargs": {},
                }
                
                if hasattr(msg, "content"):
                    message_data["content"] = msg.content
                
                if hasattr(msg, "additional_kwargs"):
                    message_data["additional_kwargs"] = msg.additional_kwargs
                
                if hasattr(msg, "tool_call_id"):
                    message_data["tool_call_id"] = msg.tool_call_id
                
                # 角色
                if hasattr(msg, "type"):
                    message_data["role"] = msg.type
                elif "Human" in msg_type:
                    message_data["role"] = "human"
                elif "AI" in msg_type:
                    message_data["role"] = "ai"
                elif "System" in msg_type:
                    message_data["role"] = "system"
                elif "Tool" in msg_type:
                    message_data["role"] = "tool"
                else:
                    message_data["role"] = "unknown"
                
                # 去重逻辑
                if message_data["role"] == "human":
                    content = message_data["content"]
                    if content:
                        is_duplicate = any(seen_content in content for seen_content in seen_human_contents)
                        
                        if is_duplicate:
                            duplicate_count += 1
                            logger.debug(f"⏭️ 跳过重复的 HumanMessage: {content[:50]}...")
                            continue
                        
                        seen_human_contents.add(content)
                
                formatted.append(message_data)
                
            except Exception as e:
                logger.warning(f"格式化消息失败: {e}")
                formatted.append({
                    "type": "unknown",
                    "content": str(msg),
                    "role": "unknown",
                    "error": str(e)
                })
        
        if duplicate_count > 0:
            logger.info(f"🧹 消息去重: 跳过 {duplicate_count} 条重复的 HumanMessage，返回 {len(formatted)} 条消息")
        
        return formatted
    
    def get_flat_messages(
        self,
        thread_id: str,
        page: int = 1,
        page_size: int = 20,
        order: str = "desc"
    ) -> Dict[str, Any]:
        """
        获取指定 thread_id 的展平消息列表（按单条消息分页）
        
        内存实现：从 MemorySaver 的 storage 中读取最新的 checkpoint
        """
        try:
            # 从内存中获取该 thread_id 的数据
            thread_data = self.storage.get(thread_id, {})
            if not thread_data:
                logger.info(f"未找到 thread_id: {thread_id} 的消息（内存中无数据）")
                return {
                    "thread_id": thread_id,
                    "total": 0,
                    "page": page,
                    "page_size": page_size,
                    "total_pages": 0,
                    "messages": []
                }
            
            # 获取默认命名空间（""）的数据
            ns_data = thread_data.get("", {})
            if not ns_data:
                logger.info(f"未找到 thread_id: {thread_id} 的消息（无命名空间数据）")
                return {
                    "thread_id": thread_id,
                    "total": 0,
                    "page": page,
                    "page_size": page_size,
                    "total_pages": 0,
                    "messages": []
                }
            
            # 获取最新的 checkpoint（按 checkpoint_id 降序排序）
            checkpoint_ids = sorted(ns_data.keys(), reverse=True)
            if not checkpoint_ids:
                return {
                    "thread_id": thread_id,
                    "total": 0,
                    "page": page,
                    "page_size": page_size,
                    "total_pages": 0,
                    "messages": []
                }
            
            latest_checkpoint_id = checkpoint_ids[0]
            checkpoint_tuple = ns_data[latest_checkpoint_id]
            
            # 反序列化 checkpoint
            checkpoint_bytes = checkpoint_tuple[0][1]
            checkpoint = pickle.loads(checkpoint_bytes)
            
            # 提取消息
            checkpoint_messages = checkpoint.get("channel_values", {}).get("messages", [])
            
            # 格式化消息
            all_messages = self._format_messages(checkpoint_messages)
            
            # 添加时间戳
            timestamp_str = self._get_cn_time().isoformat()
            for msg in all_messages:
                msg["timestamp"] = timestamp_str
            
            # 排序
            if order == "desc":
                all_messages = list(reversed(all_messages))
            
            # 分页
            total = len(all_messages)
            total_pages = (total + page_size - 1) // page_size if total > 0 else 0
            start_idx = (page - 1) * page_size
            end_idx = start_idx + page_size
            paginated_messages = all_messages[start_idx:end_idx]
            
            logger.info(f"📊 获取展平消息（内存）: thread_id={thread_id}, total={total}, page={page}/{total_pages}")
            
            return {
                "thread_id": thread_id,
                "total": total,
                "page": page,
                "page_size": page_size,
                "total_pages": total_pages,
                "messages": paginated_messages
            }
            
        except Exception as e:
            logger.error(f"❌ 获取展平消息失败（内存）: {e}")
            import traceback
            logger.error(traceback.format_exc())
            return {
                "thread_id": thread_id,
                "total": 0,
                "page": page,
                "page_size": page_size,
                "total_pages": 0,
                "messages": []
            }
    
    def get_thread_list(
        self,
        username: Optional[str] = None,
        page: int = 1,
        page_size: int = 20,
        order: str = "desc"
    ) -> Dict[str, Any]:
        """
        获取会话列表（内存实现）
        
        从 MemorySaver 的 storage 中获取所有 thread
        """
        try:
            threads = []
            
            # 遍历所有 thread_id
            for thread_id, thread_data in self.storage.items():
                # 提取 username
                thread_username = self._extract_username_from_thread_id(thread_id) or "unknown"
                
                # 如果指定了 username，只返回该用户的会话
                if username and thread_username != username:
                    continue
                
                # 获取默认命名空间的数据
                ns_data = thread_data.get("", {})
                if not ns_data:
                    continue
                
                # 获取最新的 checkpoint
                checkpoint_ids = sorted(ns_data.keys(), reverse=True)
                if not checkpoint_ids:
                    continue
                
                latest_checkpoint_id = checkpoint_ids[0]
                checkpoint_tuple = ns_data[latest_checkpoint_id]
                
                # 反序列化 checkpoint
                try:
                    checkpoint_bytes = checkpoint_tuple[0][1]
                    checkpoint = pickle.loads(checkpoint_bytes)
                    messages = checkpoint.get("channel_values", {}).get("messages", [])
                    
                    # 获取第一条用户消息
                    first_message = "暂无消息"
                    for msg in messages:
                        if hasattr(msg, "content") and ("Human" in type(msg).__name__):
                            first_message = str(msg.content)[:100]
                            break
                    
                    # 从 thread_id 解析 config_id
                    parts = thread_id.split('_')
                    config_id = parts[-1] if len(parts) >= 3 else "unknown"
                    
                    threads.append({
                        "thread_id": thread_id,
                        "username": thread_username,
                        "first_message": first_message,
                        "last_updated": self._get_cn_time().isoformat(),
                        "message_count": len(checkpoint_ids),
                        "config_id": config_id,
                    })
                    
                except Exception as e:
                    logger.warning(f"解析 thread_id={thread_id} 失败: {e}")
                    continue
            
            # 排序
            threads.sort(key=lambda x: x["last_updated"], reverse=(order == "desc"))
            
            # 分页
            total = len(threads)
            total_pages = (total + page_size - 1) // page_size if total > 0 else 0
            start_idx = (page - 1) * page_size
            end_idx = start_idx + page_size
            paginated_threads = threads[start_idx:end_idx]
            
            logger.info(f"✅ 获取会话列表成功（内存）: username={username}, total={total}, page={page}")
            
            return {
                "username": username,
                "total": total,
                "page": page,
                "page_size": page_size,
                "total_pages": total_pages,
                "threads": paginated_threads
            }
            
        except Exception as e:
            logger.error(f"❌ 获取会话列表失败（内存）: {e}")
            import traceback
            logger.error(traceback.format_exc())
            return {
                "username": username,
                "total": 0,
                "page": page,
                "page_size": page_size,
                "total_pages": 0,
                "threads": []
            }
    
    def get_history_messages(
        self, 
        thread_id: str, 
        page: int = 1, 
        page_size: int = 20,
        order: str = "desc"
    ) -> Dict[str, Any]:
        """
        获取指定 thread_id 的历史消息（按 checkpoint 分页，内存实现）
        """
        try:
            # 从内存中获取该 thread_id 的数据
            thread_data = self.storage.get(thread_id, {})
            if not thread_data:
                return {
                    "thread_id": thread_id,
                    "total": 0,
                    "page": page,
                    "page_size": page_size,
                    "total_pages": 0,
                    "messages": []
                }
            
            # 获取默认命名空间的数据
            ns_data = thread_data.get("", {})
            if not ns_data:
                return {
                    "thread_id": thread_id,
                    "total": 0,
                    "page": page,
                    "page_size": page_size,
                    "total_pages": 0,
                    "messages": []
                }
            
            # 获取所有 checkpoint_id
            checkpoint_ids = sorted(ns_data.keys(), reverse=(order == "desc"))
            total = len(checkpoint_ids)
            total_pages = (total + page_size - 1) // page_size if total > 0 else 0
            
            # 分页
            start_idx = (page - 1) * page_size
            end_idx = start_idx + page_size
            paginated_checkpoint_ids = checkpoint_ids[start_idx:end_idx]
            
            # 构建结果
            messages = []
            for checkpoint_id in paginated_checkpoint_ids:
                try:
                    checkpoint_tuple = ns_data[checkpoint_id]
                    checkpoint_bytes = checkpoint_tuple[0][1]
                    checkpoint = pickle.loads(checkpoint_bytes)
                    
                    checkpoint_messages = checkpoint.get("channel_values", {}).get("messages", [])
                    
                    messages.append({
                        "checkpoint_id": checkpoint_id,
                        "messages": self._format_messages(checkpoint_messages),
                        "metadata": {},
                        "created_at": self._get_cn_time().isoformat(),
                        "updated_at": self._get_cn_time().isoformat(),
                    })
                except Exception as e:
                    logger.error(f"反序列化 checkpoint 失败: {e}")
                    continue
            
            logger.info(f"✅ 获取历史消息成功（内存）: thread_id={thread_id}, total={total}, page={page}")
            
            return {
                "thread_id": thread_id,
                "total": total,
                "page": page,
                "page_size": page_size,
                "total_pages": total_pages,
                "messages": messages
            }
            
        except Exception as e:
            logger.error(f"❌ 获取历史消息失败（内存）: {e}")
            import traceback
            logger.error(traceback.format_exc())
            return {
                "thread_id": thread_id,
                "total": 0,
                "page": page,
                "page_size": page_size,
                "total_pages": 0,
                "messages": []
            }

