"""
KaFlow-Py MongoDBCheckpointer

基于 MongoDB 的 Checkpointer 实现

Author: DevYK
微信公众号: DevYK
Email: yang1001yk@gmail.com
Github: https://github.com/yangkun19921001
"""

from typing import Optional, Dict, Any, Iterator, Tuple, AsyncIterator
from datetime import datetime
import pickle
import os

from langgraph.checkpoint.base import (
    Checkpoint,
    CheckpointMetadata,
    CheckpointTuple,
    ChannelVersions,
)
from .base import BaseCheckpointer
from ..utils.logger import get_logger

logger = get_logger(__name__)


class MongoDBCheckpointer(BaseCheckpointer):
    """
    MongoDB Checkpointer 实现
    
    特点：
    - 数据持久化到 MongoDB
    - 支持分布式部署
    - 适合生产环境
    - 支持历史记录查询
    
    数据结构：
    {
        "thread_id": "xxx",
        "checkpoint_id": "xxx",
        "parent_checkpoint_id": "xxx",
        "checkpoint_data": Binary(pickle),
        "metadata": {...},
        "created_at": ISODate(),
        "updated_at": ISODate()
    }
    
    使用场景：
    - 生产环境
    - 需要持久化对话历史
    - 多实例部署
    - 需要查询历史对话
    """
    
    def __init__(self, config: Dict[str, Any]):
        """
        初始化 MongoDB Checkpointer
        
        Args:
            config: MongoDB 连接配置
                - host: MongoDB 主机地址
                - port: MongoDB 端口（默认 27017）
                - database: 数据库名称
                - collection: 集合名称（默认 "checkpoints"）
                - username: 用户名（可选）
                - password: 密码（可选）
                - auth_source: 认证数据库（可选，默认 "admin"）
                - **kwargs: 其他 MongoDB 连接参数
        """
        super().__init__(config)
        
        # 提取配置
        self.host = config.get("host", "localhost")
        self.port = int(config.get("port", 27017))
        self.database_name = config.get("database", "kaflow")
        self.collection_name = config.get("collection", "checkpoints")
        self.username = config.get("username", "")
        self.password = config.get("password", "")
        self.auth_source = config.get("auth_source", "admin")
        
        # MongoDB 客户端（延迟初始化）
        self._client = None
        self._db = None
        self._collection = None
        self._is_connected = False  # 连接状态标志
        self._setup_lock = None  # 用于防止并发 setup
        
        logger.info(f"📦 MongoDBCheckpointer 配置: {self.host}:{self.port}/{self.database_name}")
    
    @property
    def config_specs(self):
        """
        LangGraph checkpointer 必须实现的属性
        返回配置规范列表
        """
        return []
    
    @staticmethod
    def _extract_username_from_thread_id(thread_id: str) -> Optional[str]:
        """
        从 thread_id 中提取 username
        
        thread_id 格式: username_uuid_configid
        例如: admin@example.com_12345678-1234-1234-1234-123456789012_ops_agent
        或: yang1001yk@gmail.com_3cb83f36-85a9-47d1-a2df-4df2e8eced86_4
        
        Returns:
            username: 用户名（thread_id 的第一个部分）
        """
        if not thread_id:
            return None
        
        # thread_id 格式: username_uuid_configid
        parts = thread_id.split('_')
        if len(parts) < 3:
            return None
        
        # 第一个部分是 username（邮箱或用户名）
        username = parts[0]
        return username if username else None
    
    def validate_config(self) -> bool:
        """验证配置"""
        if not self.host:
            logger.error("❌ MongoDB host 未配置")
            return False
        
        if not self.database_name:
            logger.error("❌ MongoDB database 未配置")
            return False
        
        return True
    
    async def setup(self) -> None:
        """
        设置 MongoDB 连接
        
        - 连接到 MongoDB
        - 创建索引以优化查询
        """
        try:
            from pymongo import MongoClient, ASCENDING, DESCENDING
            from pymongo.errors import ConnectionFailure
            
            # 构建连接 URI
            if self.username and self.password:
                # 支持从环境变量读取密码
                password = os.environ.get(self.password.replace("${", "").replace("}", ""), self.password)
                uri = f"mongodb://{self.username}:{password}@{self.host}:{self.port}/{self.database_name}?authSource={self.auth_source}"
            else:
                uri = f"mongodb://{self.host}:{self.port}/{self.database_name}"
            
            # 创建客户端
            logger.info(f"🔗 正在连接 MongoDB: {self.host}:{self.port}")
            self._client = MongoClient(
                uri,
                serverSelectionTimeoutMS=5000,  # 5秒超时
                connectTimeoutMS=5000,
            )
            
            # 测试连接
            self._client.admin.command('ping')
            logger.info("✅ MongoDB 连接成功")
            
            # 获取数据库和集合
            self._db = self._client[self.database_name]
            self._collection = self._db[self.collection_name]
            
            # 创建索引
            self._collection.create_index([("thread_id", ASCENDING), ("checkpoint_id", DESCENDING)])
            self._collection.create_index([("created_at", DESCENDING)])
            self._collection.create_index([("username", ASCENDING), ("created_at", DESCENDING)])  # 按用户查询索引
            logger.info(f"✅ 集合索引已创建: {self.collection_name}")
            
            self._is_connected = True
            
        except ImportError:
            logger.error("❌ pymongo 未安装，请运行: uv add pymongo")
            raise
        except ConnectionFailure as e:
            logger.error(f"❌ MongoDB 连接失败: {e}")
            self._is_connected = False
            raise
        except Exception as e:
            logger.error(f"❌ MongoDB 设置失败: {e}")
            self._is_connected = False
            raise
    
    def _ensure_connected(self) -> bool:
        """
        确保 MongoDB 已连接（同步版本）
        
        如果未连接，则立即建立连接
        用于在同步方法中确保连接可用
        
        Returns:
            bool: 连接是否成功
        """
        if self._is_connected and self._client is not None:
            return True
        
        try:
            from pymongo import MongoClient, ASCENDING, DESCENDING
            from pymongo.errors import ConnectionFailure
            
            # 构建连接 URI
            if self.username and self.password:
                # 支持从环境变量读取密码
                password = os.environ.get(self.password.replace("${", "").replace("}", ""), self.password)
                uri = f"mongodb://{self.username}:{password}@{self.host}:{self.port}/{self.database_name}?authSource={self.auth_source}"
            else:
                uri = f"mongodb://{self.host}:{self.port}/{self.database_name}"
            
            # 创建客户端
            logger.info(f"🔗 正在同步连接 MongoDB: {self.host}:{self.port}")
            self._client = MongoClient(
                uri,
                serverSelectionTimeoutMS=5000,  # 5秒超时
                connectTimeoutMS=5000,
            )
            
            # 测试连接
            self._client.admin.command('ping')
            logger.info("✅ MongoDB 连接成功")
            
            # 获取数据库和集合
            self._db = self._client[self.database_name]
            self._collection = self._db[self.collection_name]
            
            # 创建索引
            self._collection.create_index([("thread_id", ASCENDING), ("checkpoint_id", DESCENDING)])
            self._collection.create_index([("created_at", DESCENDING)])
            self._collection.create_index([("username", ASCENDING), ("created_at", DESCENDING)])  # 按用户查询索引
            logger.info(f"✅ 集合索引已创建: {self.collection_name}")
            
            self._is_connected = True
            return True
            
        except Exception as e:
            logger.error(f"❌ MongoDB 同步连接失败: {e}")
            self._is_connected = False
            return False
    
    async def teardown(self) -> None:
        """关闭 MongoDB 连接"""
        if self._client:
            self._client.close()
            self._is_connected = False
            logger.info("🔒 MongoDB 连接已关闭")
    
    def get_tuple(self, config: Dict[str, Any]) -> Optional[CheckpointTuple]:
        """
        获取指定的 checkpoint
        
        Args:
            config: 包含 thread_id 和可选的 checkpoint_id 的配置
            
        Returns:
            CheckpointTuple 或 None
        """
        # 确保 MongoDB 已连接
        if not self._ensure_connected():
            logger.warning("⚠️  MongoDB 连接失败，无法获取 checkpoint")
            return None
        
        thread_id = config.get("configurable", {}).get("thread_id")
        checkpoint_id = config.get("configurable", {}).get("checkpoint_id")
        
        if not thread_id:
            logger.warning("⚠️  thread_id 未提供")
            return None
        
        try:
            # 构建查询
            query = {"thread_id": thread_id}
            if checkpoint_id:
                query["checkpoint_id"] = checkpoint_id
            
            # 查询最新的 checkpoint
            doc = self._collection.find_one(
                query,
                sort=[("created_at", -1)]
            )
            
            if not doc:
                logger.debug(f"📭 未找到 checkpoint: thread_id={thread_id}")
                return None
            
            # 反序列化 checkpoint
            checkpoint = pickle.loads(doc["checkpoint_data"])
            metadata = doc.get("metadata", {})
            
            # 构建 CheckpointTuple
            return CheckpointTuple(
                config=config,
                checkpoint=checkpoint,
                metadata=metadata,
                parent_config={
                    "configurable": {
                        "thread_id": thread_id,
                        "checkpoint_id": doc.get("parent_checkpoint_id"),
                    }
                } if doc.get("parent_checkpoint_id") else None,
            )
            
        except Exception as e:
            logger.error(f"❌ 获取 checkpoint 失败: {e}")
            return None
    
    def list(self, config: Dict[str, Any], *, limit: Optional[int] = None, before: Optional[Dict[str, Any]] = None) -> Iterator[CheckpointTuple]:
        """
        列出指定 thread 的所有 checkpoints
        
        Args:
            config: 包含 thread_id 的配置
            limit: 返回的最大数量
            before: 在此 checkpoint 之前的记录
            
        Yields:
            CheckpointTuple 迭代器
        """
        # 确保 MongoDB 已连接
        if not self._ensure_connected():
            logger.warning("⚠️  MongoDB 连接失败，无法列出 checkpoints")
            return
        
        thread_id = config.get("configurable", {}).get("thread_id")
        if not thread_id:
            logger.warning("⚠️  thread_id 未提供")
            return
        
        try:
            # 构建查询
            query = {"thread_id": thread_id}
            
            # before 条件
            if before:
                before_checkpoint_id = before.get("configurable", {}).get("checkpoint_id")
                if before_checkpoint_id:
                    before_doc = self._collection.find_one({"checkpoint_id": before_checkpoint_id})
                    if before_doc:
                        query["created_at"] = {"$lt": before_doc["created_at"]}
            
            # 查询
            cursor = self._collection.find(query).sort("created_at", -1)
            
            if limit:
                cursor = cursor.limit(limit)
            
            # 迭代返回
            for doc in cursor:
                checkpoint = pickle.loads(doc["checkpoint_data"])
                metadata = doc.get("metadata", {})
                
                yield CheckpointTuple(
                    config=config,
                    checkpoint=checkpoint,
                    metadata=metadata,
                    parent_config={
                        "configurable": {
                            "thread_id": thread_id,
                            "checkpoint_id": doc.get("parent_checkpoint_id"),
                        }
                    } if doc.get("parent_checkpoint_id") else None,
                )
                
        except Exception as e:
            logger.error(f"❌ 列出 checkpoints 失败: {e}")
    
    def put(self, config: Dict[str, Any], checkpoint: Checkpoint, metadata: CheckpointMetadata, new_versions: ChannelVersions) -> Dict[str, Any]:
        """
        保存 checkpoint
        
        Args:
            config: 包含 thread_id 的配置
            checkpoint: Checkpoint 对象
            metadata: Checkpoint 元数据
            new_versions: Channel 版本信息
            
        Returns:
            更新后的配置
        """
        # 确保 MongoDB 已连接
        if not self._ensure_connected():
            logger.warning("⚠️  MongoDB 连接失败，无法保存 checkpoint")
            return config
        
        thread_id = config.get("configurable", {}).get("thread_id")
        if not thread_id:
            logger.warning("⚠️  thread_id 未提供")
            return config
        
        try:
            # 生成 checkpoint_id（使用时间戳）
            checkpoint_id = checkpoint.get("id", str(datetime.now().timestamp()))
            
            # 获取父 checkpoint_id
            parent_checkpoint_id = config.get("configurable", {}).get("checkpoint_id")
            
            # 注意：new_versions 参数由 LangGraph 传递，暂时不存储（预留用于未来优化）
            
            # 序列化 checkpoint
            checkpoint_data = pickle.dumps(checkpoint)
            
            # 从 thread_id 中提取 username
            username = self._extract_username_from_thread_id(thread_id)
            
            # 构建文档
            doc = {
                "thread_id": thread_id,
                "checkpoint_id": checkpoint_id,
                "parent_checkpoint_id": parent_checkpoint_id,
                "checkpoint_data": checkpoint_data,
                "metadata": dict(metadata) if metadata else {},
                "username": username,  # 新增：存储 username 用于按用户查询
                "created_at": datetime.now(),
                "updated_at": datetime.now(),
            }
            
            # 插入或更新
            self._collection.update_one(
                {"thread_id": thread_id, "checkpoint_id": checkpoint_id},
                {"$set": doc},
                upsert=True
            )
            
            logger.debug(f"💾 checkpoint 已保存: thread_id={thread_id}, checkpoint_id={checkpoint_id}")
            
            # 返回更新后的配置
            return {
                "configurable": {
                    "thread_id": thread_id,
                    "checkpoint_id": checkpoint_id,
                }
            }
            
        except Exception as e:
            logger.error(f"❌ 保存 checkpoint 失败: {e}")
            return config
    
    def put_writes(self, config: Dict[str, Any], writes: list, task_id: str, task_path: str = "") -> None:
        """
        保存中间写入操作（用于 subgraphs）
        
        Args:
            config: 配置
            writes: 写入操作列表
            task_id: 任务 ID
            task_path: 任务路径
        """
        # MongoDB 实现暂时不存储中间写入
        # 如果需要完整的状态恢复，可以将 writes 存储到单独的集合
        logger.debug(f"put_writes called: task_id={task_id}, writes_count={len(writes)}")
        pass
    
    # ==================== 异步方法（调用同步方法） ====================
    
    async def aget_tuple(self, config: Dict[str, Any]) -> Optional[CheckpointTuple]:
        """
        异步获取 checkpoint tuple
        
        由于 pymongo 是同步驱动，这里直接调用同步方法
        如果需要真正的异步，可以使用 motor 驱动
        """
        return self.get_tuple(config)
    
    async def aput(self, config: Dict[str, Any], checkpoint: Checkpoint, metadata: CheckpointMetadata, new_versions: ChannelVersions) -> Dict[str, Any]:
        """
        异步保存 checkpoint
        
        由于 pymongo 是同步驱动，这里直接调用同步方法
        """
        return self.put(config, checkpoint, metadata, new_versions)
    
    async def alist(self, config: Dict[str, Any], *, filter: Optional[Dict[str, Any]] = None, before: Optional[Dict[str, Any]] = None, limit: Optional[int] = None) -> AsyncIterator[CheckpointTuple]:
        """
        异步列出 checkpoints
        
        由于 pymongo 是同步驱动，这里直接调用同步方法
        """
        for item in self.list(config, before=before, limit=limit):
            yield item
    
    async def aput_writes(self, config: Dict[str, Any], writes: list, task_id: str, task_path: str = "") -> None:
        """
        异步保存中间写入
        
        由于 pymongo 是同步驱动，这里直接调用同步方法
        """
        return self.put_writes(config, writes, task_id, task_path)
    
    # ==================== 历史消息查询方法 ====================
    
    def get_flat_messages(
        self,
        thread_id: str,
        page: int = 1,
        page_size: int = 20,
        order: str = "desc"
    ) -> Dict[str, Any]:
        """
        获取指定 thread_id 的展平消息列表（按单条消息分页）
        
        与 get_history_messages 不同，此方法：
        1. 只获取最新的 checkpoint（包含完整对话历史）
        2. 提取其中的所有消息
        3. 按单条消息进行分页
        
        Args:
            thread_id: 会话线程 ID
            page: 页码（从 1 开始）
            page_size: 每页大小（默认 20）
            order: 排序方式，"desc" 表示最新的在前，"asc" 表示最早的在前
            
        Returns:
            {
                "thread_id": str,
                "total": int,           # 消息总数
                "page": int,
                "page_size": int,
                "total_pages": int,
                "messages": [...]       # 单条消息列表
            }
        """
        # 确保 MongoDB 已连接
        if not self._ensure_connected():
            logger.error("❌ MongoDB 连接失败，无法获取消息")
            return {
                "thread_id": thread_id,
                "total": 0,
                "page": page,
                "page_size": page_size,
                "total_pages": 0,
                "messages": []
            }
        
        try:
            from pymongo import DESCENDING
            
            # 1. 获取最新的 checkpoint（包含完整对话历史）
            latest_checkpoint = self._collection.find_one(
                {"thread_id": thread_id},
                sort=[("created_at", DESCENDING)]
            )
            
            if not latest_checkpoint:
                logger.info(f"未找到 thread_id: {thread_id} 的消息")
                return {
                    "thread_id": thread_id,
                    "total": 0,
                    "page": page,
                    "page_size": page_size,
                    "total_pages": 0,
                    "messages": []
                }
            
            # 2. 反序列化并提取消息
            checkpoint = pickle.loads(latest_checkpoint["checkpoint_data"])
            checkpoint_messages = checkpoint.get("channel_values", {}).get("messages", [])
            checkpoint_timestamp = latest_checkpoint.get("created_at")
            
            # 3. 格式化所有消息
            all_messages = self._format_messages(checkpoint_messages)
            
            # 4. 为每条消息添加时间戳（使用 checkpoint 的时间戳）
            if checkpoint_timestamp:
                timestamp_str = checkpoint_timestamp.isoformat()
                for msg in all_messages:
                    msg["timestamp"] = timestamp_str
            
            # 5. 根据排序方式调整顺序
            if order == "desc":
                all_messages = list(reversed(all_messages))  # 最新的在前
            
            # 6. 计算分页
            total = len(all_messages)
            total_pages = (total + page_size - 1) // page_size if total > 0 else 0
            start_idx = (page - 1) * page_size
            end_idx = start_idx + page_size
            
            # 7. 获取当前页的消息
            paginated_messages = all_messages[start_idx:end_idx]
            
            logger.info(f"📊 获取展平消息: thread_id={thread_id}, total_messages={total}, page={page}/{total_pages}, returned={len(paginated_messages)}")
            
            return {
                "thread_id": thread_id,
                "total": total,
                "page": page,
                "page_size": page_size,
                "total_pages": total_pages,
                "messages": paginated_messages
            }
            
        except Exception as e:
            logger.error(f"❌ 获取展平消息失败: {e}")
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
        获取会话列表（支持按用户筛选或获取所有会话）
        
        Args:
            username: 用户名（可选，如果不传则返回所有用户的会话）
            page: 页码（从 1 开始）
            page_size: 每页大小（默认 20）
            order: 排序方式，"desc" 表示最新的在前，"asc" 表示最早的在前
            
        Returns:
            {
                "username": str | None,
                "total": int,
                "page": int,
                "page_size": int,
                "total_pages": int,
                "threads": [
                    {
                        "thread_id": str,
                        "username": str,  # 会话所属用户
                        "first_message": str,  # 第一条消息内容（预览）
                        "last_updated": datetime,
                        "message_count": int,
                        "config_id": str,  # 从 thread_id 解析出的配置 ID
                    }
                ]
            }
        """
        # 确保 MongoDB 已连接
        if not self._ensure_connected():
            logger.error("❌ MongoDB 连接失败，无法获取会话列表")
            return {
                "username": username,
                "total": 0,
                "page": page,
                "page_size": page_size,
                "total_pages": 0,
                "threads": []
            }
        
        try:
            from pymongo import DESCENDING, ASCENDING
            
            # 使用聚合查询，按 thread_id 分组
            pipeline = []
            
            # 1. 筛选指定用户的记录（如果提供了 username）
            if username:
                pipeline.append({"$match": {"username": username}})
            
            # 2. 关键：先按 thread_id 分组，再按 created_at 排序
            # 注意：取最新的 checkpoint（$last），因为它包含完整的对话历史
            pipeline.append({"$sort": {"thread_id": 1, "created_at": 1}})
            
            # 3. 按 thread_id 分组
            pipeline.append({
                "$group": {
                    "_id": "$thread_id",
                    "username": {"$first": "$username"},  # 获取该 thread 的 username
                    "last_updated": {"$max": "$updated_at"},
                    "first_created": {"$min": "$created_at"},
                    "message_count": {"$sum": 1},
                    "latest_checkpoint": {"$last": "$checkpoint_data"},  # 取最新的 checkpoint（包含完整历史）
                }
            })
            
            # 4. 最后按 last_updated 排序
            pipeline.append({"$sort": {"last_updated": -1 if order == "desc" else 1}})
            
            # 执行聚合查询（不分页，先获取所有）
            all_threads = list(self._collection.aggregate(pipeline))
            total = len(all_threads)
            total_pages = (total + page_size - 1) // page_size if total > 0 else 0
            
            # 应用分页
            start_idx = (page - 1) * page_size
            end_idx = start_idx + page_size
            paginated_threads = all_threads[start_idx:end_idx]
            
            # 格式化返回结果
            threads = []
            for thread_data in paginated_threads:
                thread_id = thread_data["_id"]
                
                # 解析第一条消息（从最新的 checkpoint 中获取第一条用户消息）
                first_message = "暂无消息"
                try:
                    if thread_data.get("latest_checkpoint"):
                        checkpoint = pickle.loads(thread_data["latest_checkpoint"])
                        # 从 checkpoint 中提取消息
                        channel_values = checkpoint.get("channel_values", {})
                        messages = channel_values.get("messages", [])
                        
                        if messages:
                            # 获取第一条用户消息作为预览（因为 checkpoint 包含完整历史）
                            for msg in messages:
                                # 兼容不同的消息格式
                                content = None
                                msg_type = None
                                
                                if hasattr(msg, "content"):
                                    content = msg.content
                                    msg_type = getattr(msg, "type", None) or type(msg).__name__
                                elif isinstance(msg, dict):
                                    content = msg.get("content")
                                    msg_type = msg.get("type")
                                
                                # 优先显示用户消息（HumanMessage）
                                if content and ("Human" in str(msg_type) or "human" in str(msg_type)):
                                    first_message = str(content)[:100]  # 限制长度
                                    break
                            
                            # 如果没有找到用户消息，显示第一条有内容的消息
                            if first_message == "暂无消息":
                                for msg in messages:
                                    content = None
                                    if hasattr(msg, "content"):
                                        content = msg.content
                                    elif isinstance(msg, dict):
                                        content = msg.get("content")
                                    
                                    if content:
                                        first_message = str(content)[:100]
                                        break
                        else:
                            logger.debug(f"thread_id={thread_id} 的 checkpoint 中没有消息")
                    else:
                        logger.debug(f"thread_id={thread_id} 没有 latest_checkpoint 数据")
                except Exception as e:
                    logger.warning(f"解析 thread_id={thread_id} 的第一条消息失败: {e}")
                    import traceback
                    logger.debug(traceback.format_exc())
                
                # 从 thread_id 解析 config_id
                parts = thread_id.split('_')
                config_id = parts[-1] if len(parts) >= 3 else "unknown"
                
                # 获取 username（从聚合结果或 thread_id 解析）
                thread_username = thread_data.get("username") or self._extract_username_from_thread_id(thread_id) or "unknown"
                
                threads.append({
                    "thread_id": thread_id,
                    "username": thread_username,  # 新增：返回该会话所属用户
                    "first_message": first_message,
                    "last_updated": thread_data["last_updated"].isoformat() if thread_data.get("last_updated") else None,
                    "message_count": thread_data.get("message_count", 0),
                    "config_id": config_id,
                })
            
            logger.info(f"✅ 获取会话列表成功: username={username}, total={total}, page={page}")
            
            return {
                "username": username,
                "total": total,
                "page": page,
                "page_size": page_size,
                "total_pages": total_pages,
                "threads": threads
            }
            
        except Exception as e:
            logger.error(f"❌ 获取会话列表失败: {e}")
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
        获取指定 thread_id 的历史消息（支持分页）
        
        Args:
            thread_id: 会话线程 ID
            page: 页码（从 1 开始）
            page_size: 每页大小（默认 20）
            order: 排序方式，"desc" 表示最新的在前，"asc" 表示最早的在前
            
        Returns:
            {
                "thread_id": str,
                "total": int,
                "page": int,
                "page_size": int,
                "total_pages": int,
                "messages": [
                    {
                        "checkpoint_id": str,
                        "messages": [...],  # LangGraph 消息列表
                        "created_at": datetime,
                        "updated_at": datetime,
                    }
                ]
            }
        """
        # 确保 MongoDB 已连接
        if not self._ensure_connected():
            logger.error("❌ MongoDB 连接失败，无法获取历史消息")
            return {
                "thread_id": thread_id,
                "total": 0,
                "page": page,
                "page_size": page_size,
                "total_pages": 0,
                "messages": []
            }
        
        try:
            # 计算总数（checkpoint 总数）
            total = self._collection.count_documents({"thread_id": thread_id})
            total_pages = (total + page_size - 1) // page_size if total > 0 else 0
            
            # 计算跳过的记录数
            skip = (page - 1) * page_size
            
            # 排序方向
            from pymongo import ASCENDING, DESCENDING
            sort_direction = DESCENDING if order == "desc" else ASCENDING
            
            logger.info(f"📊 查询历史消息: thread_id={thread_id}, total_checkpoints={total}, page={page}/{total_pages}, skip={skip}, limit={page_size}")
            
            # 查询（按 checkpoint 分页）
            cursor = self._collection.find(
                {"thread_id": thread_id}
            ).sort("created_at", sort_direction).skip(skip).limit(page_size)
            
            # 构建结果
            messages = []
            checkpoint_count = 0
            for doc in cursor:
                checkpoint_count += 1
                try:
                    # 反序列化 checkpoint
                    checkpoint = pickle.loads(doc["checkpoint_data"])
                    
                    # 提取消息列表
                    checkpoint_messages = checkpoint.get("channel_values", {}).get("messages", [])
                    
                    messages.append({
                        "checkpoint_id": doc["checkpoint_id"],
                        "messages": self._format_messages(checkpoint_messages),
                        "metadata": doc.get("metadata", {}),
                        "created_at": doc["created_at"].isoformat() if doc.get("created_at") else None,
                        "updated_at": doc["updated_at"].isoformat() if doc.get("updated_at") else None,
                    })
                except Exception as e:
                    logger.error(f"反序列化 checkpoint 失败: {e}")
                    continue
            
            logger.info(f"✅ 成功返回 {checkpoint_count} 个 checkpoint（共 {total} 个）")
            
            return {
                "thread_id": thread_id,
                "total": total,
                "page": page,
                "page_size": page_size,
                "total_pages": total_pages,
                "messages": messages
            }
            
        except Exception as e:
            logger.error(f"❌ 获取历史消息失败: {e}")
            import traceback
            logger.debug(traceback.format_exc())
            return {
                "thread_id": thread_id,
                "total": 0,
                "page": page,
                "page_size": page_size,
                "total_pages": 0,
                "messages": [],
                "error": str(e)
            }
    
    def _format_messages(self, messages: list) -> list:
        """
        格式化消息列表，转换为 API 友好的格式
        
        特性：自动去重 - 同一个 checkpoint 中的重复 HumanMessage 只保留第一个
        
        Args:
            messages: LangGraph 消息列表
            
        Returns:
            格式化后的消息列表（已去重）
        """
        formatted = []
        seen_human_contents = set()  # 跟踪已见过的 HumanMessage 内容
        duplicate_count = 0
        
        for msg in messages:
            try:
                # 判断消息类型
                msg_type = type(msg).__name__
                
                # 提取基本信息
                message_data = {
                    "type": msg_type,
                    "content": "",
                    "additional_kwargs": {},
                }
                
                # HumanMessage
                if hasattr(msg, "content"):
                    message_data["content"] = msg.content
                
                # AIMessage
                if hasattr(msg, "additional_kwargs"):
                    message_data["additional_kwargs"] = msg.additional_kwargs
                
                # ToolMessage
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
                
                # 🎯 关键：去重逻辑 - 智能去重（支持子串匹配）
                if message_data["role"] == "human":
                    content = message_data["content"]
                    if content:
                        # 检查是否有任何已见过的 human message 在当前 content 中（子串匹配）
                        # 例如：content="123456", seen_human_contents=["1234"]
                        # "1234" in "123456" → True，认为是重复
                        is_duplicate = any(seen_content in content for seen_content in seen_human_contents)
                        
                        if is_duplicate:
                            # 这是重复的 HumanMessage，跳过不添加
                            duplicate_count += 1
                            logger.debug(f"⏭️ 跳过重复的 HumanMessage（子串匹配）: {content[:50]}...")
                            continue  # 跳过，不添加到 formatted
                        
                        # 记录这个 human message
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
        
        # 记录去重结果
        if duplicate_count > 0:
            logger.info(f"🧹 消息去重: 跳过 {duplicate_count} 条重复的 HumanMessage，返回 {len(formatted)} 条消息")
        
        return formatted

