# 企业级Agent开发教程(四): 基于 MongoDB 实现持久化记忆缓存

## 一、前言

在前面几篇文章中，我们构建了 KaFlow-Py 这个配置驱动的 AI Agent 框架。但有个问题一直困扰着我：**对话记忆存在内存里，服务重启就全没了**。

这在开发阶段还能忍，但到了生产环境就不行了。用户跟 Agent 聊了半天，结果服务器重启一次，所有历史都丢了，用户体验会非常糟糕。

所以这次我们要解决的核心问题是：**如何实现生产级的持久化记忆缓存**。

实现后的效果:

    ![](http://devyk.top/2022/202510152048331.gif)


我们会先从 LangGraph 的 Checkpointer 原理入手，详细讲解如何实现一个生产级的 MongoDB Checkpointer

## 二、LangGraph Checkpointer 原理

在实现自己的 Checkpointer 之前，我们需要先深入理解 LangGraph 的设计思路。让我们从顶层抽象开始，逐层剖析。

### 2.1 BaseCheckpointSaver - 顶层抽象

`BaseCheckpointSaver` 是 LangGraph 为所有 Checkpointer 定义的抽象基类，它规定了持久化层必须实现的完整接口规范。

#### 完整接口定义

```python
from abc import ABC, abstractmethod
from typing import Optional, Iterator, AsyncIterator, Any
from langchain_core.runnables import RunnableConfig

class BaseCheckpointSaver(ABC):
    """Checkpoint Saver 抽象基类"""
    
    # ==================== 配置属性 ====================
    
    @property
    def config_specs(self) -> list[ConfigurableFieldSpec]:
        """配置规范（有默认实现，可重写）"""
        return [CheckpointThreadId, CheckpointNS, CheckpointId]
    
    # ==================== 同步接口（必须实现） ====================
    
    @abstractmethod
    def get_tuple(self, config: RunnableConfig) -> Optional[CheckpointTuple]:
        """获取指定的 checkpoint tuple"""
        pass
    
    @abstractmethod
    def list(
        self, 
        config: Optional[RunnableConfig], 
        *, 
        filter: Optional[dict[str, Any]] = None,
        before: Optional[RunnableConfig] = None,
        limit: Optional[int] = None
    ) -> Iterator[CheckpointTuple]:
        """列出 checkpoints（支持分页和过滤）"""
        pass
    
    @abstractmethod
    def put(
        self, 
        config: RunnableConfig, 
        checkpoint: Checkpoint,
        metadata: CheckpointMetadata,
        new_versions: ChannelVersions
    ) -> RunnableConfig:
        """保存 checkpoint"""
        pass
    
    @abstractmethod
    def put_writes(
        self,
        config: RunnableConfig,
        writes: Sequence[tuple[str, Any]],
        task_id: str,
        task_path: str = ""
    ) -> None:
        """保存中间写入操作（用于 subgraphs）"""
        pass
    
    @abstractmethod
    def delete_thread(self, thread_id: str) -> None:
        """删除指定 thread 的所有 checkpoints"""
        pass
    
    # ==================== 异步接口（必须实现） ====================
    
    @abstractmethod
    async def aget_tuple(self, config: RunnableConfig) -> Optional[CheckpointTuple]:
        """异步获取 checkpoint tuple"""
        pass
    
    @abstractmethod
    async def alist(
        self, 
        config: Optional[RunnableConfig], 
        *, 
        filter: Optional[dict[str, Any]] = None,
        before: Optional[RunnableConfig] = None,
        limit: Optional[int] = None
    ) -> AsyncIterator[CheckpointTuple]:
        """异步列出 checkpoints"""
        pass
    
    @abstractmethod
    async def aput(
        self, 
        config: RunnableConfig, 
        checkpoint: Checkpoint,
        metadata: CheckpointMetadata,
        new_versions: ChannelVersions
    ) -> RunnableConfig:
        """异步保存 checkpoint"""
        pass
    
    @abstractmethod
    async def aput_writes(
        self,
        config: RunnableConfig,
        writes: Sequence[tuple[str, Any]],
        task_id: str,
        task_path: str = ""
    ) -> None:
        """异步保存中间写入"""
        pass
    
    @abstractmethod
    async def adelete_thread(self, thread_id: str) -> None:
        """异步删除指定 thread 的所有 checkpoints"""
        pass
    
    # ==================== 可选方法（有默认实现） ====================
    
    def get_next_version(self, current: Optional[V], channel: ChannelProtocol) -> V:
        """生成下一个版本号（默认递增整数）"""
        if isinstance(current, str):
            raise NotImplementedError
        elif current is None:
            return 1
        else:
            return current + 1
    
    # ==================== 辅助方法（基于抽象方法实现） ====================
    
    def get(self, config: RunnableConfig) -> Optional[Checkpoint]:
        """获取 checkpoint（内部调用 get_tuple）"""
        if value := self.get_tuple(config):
            return value.checkpoint
    
    async def aget(self, config: RunnableConfig) -> Optional[Checkpoint]:
        """异步获取 checkpoint（内部调用 aget_tuple）"""
        if value := await self.aget_tuple(config):
            return value.checkpoint
```

#### 接口实现要求

LangGraph 定义了 **10 个抽象方法**，必须全部实现：

| 方法 | 类型 | 是否必须 | 说明 |
|------|------|---------|------|
| `get_tuple()` | 同步 | ✅ 必须 | 获取单个 checkpoint，LangGraph 加载对话历史时调用 |
| `list()` | 同步 | ✅ 必须 | 列出 checkpoints，支持分页和过滤 |
| `put()` | 同步 | ✅ 必须 | 保存 checkpoint，每轮对话后调用 |
| `put_writes()` | 同步 | ✅ 必须 | 保存中间写入（subgraphs），可以空实现 |
| `delete_thread()` | 同步 | ✅ 必须 | 删除 thread，删除对话历史时调用 |
| `aget_tuple()` | 异步 | ✅ 必须 | 异步版本的 get_tuple |
| `alist()` | 异步 | ✅ 必须 | 异步版本的 list |
| `aput()` | 异步 | ✅ 必须 | 异步版本的 put |
| `aput_writes()` | 异步 | ✅ 必须 | 异步版本的 put_writes |
| `adelete_thread()` | 异步 | ✅ 必须 | 异步版本的 delete_thread |
| `config_specs` | 属性 | ⚪ 可选 | 配置规范，有默认实现 |
| `get_next_version()` | 方法 | ⚪ 可选 | 生成版本号，有默认实现 |

#### 核心方法详解

**1. get_tuple() - 读取 Checkpoint**

```python
def get_tuple(self, config: RunnableConfig) -> Optional[CheckpointTuple]:
    """
    获取指定的 checkpoint
    
    Args:
        config: 包含 thread_id 和可选的 checkpoint_id
        
    Returns:
        CheckpointTuple: 包含 checkpoint、metadata、parent_config
        
    调用时机：
        - LangGraph 加载对话历史时
        - 恢复状态时
    """
```

**关键点**：
- 如果 `checkpoint_id` 未提供，返回最新的 checkpoint
- 必须返回 `CheckpointTuple`，包含完整的上下文信息

**2. put() - 保存 Checkpoint**

```python
def put(
    self, 
    config: RunnableConfig, 
    checkpoint: Checkpoint,
    metadata: CheckpointMetadata,
    new_versions: ChannelVersions
) -> RunnableConfig:
    """
    保存 checkpoint
    
    Args:
        config: 包含 thread_id
        checkpoint: 完整的 checkpoint 对象（包含 channel_values）
        metadata: 元数据（source、step、writes 等）
        new_versions: 通道版本信息
        
    Returns:
        RunnableConfig: 更新后的 config，包含新的 checkpoint_id
        
    调用时机：
        - 每轮对话结束后
        - 状态更新后
    """
```

**关键点**：
- 使用 `upsert` 模式，避免重复插入
- 必须返回包含 `checkpoint_id` 的 config

**3. list() - 列出 Checkpoints**

```python
def list(
    self, 
    config: Optional[RunnableConfig], 
    *, 
    filter: Optional[dict[str, Any]] = None,
    before: Optional[RunnableConfig] = None,
    limit: Optional[int] = None
) -> Iterator[CheckpointTuple]:
    """
    列出 checkpoints
    
    Args:
        config: 包含 thread_id（可选，不传则列出所有）
        filter: 元数据过滤条件
        before: 列出此 checkpoint 之前的记录（用于分页）
        limit: 返回的最大数量
        
    Yields:
        CheckpointTuple: checkpoint 迭代器
        
    调用时机：
        - 查询历史对话时
        - 时间旅行（回溯状态）时
    """
```

**关键点**：
- 返回 `Iterator`，支持惰性加载
- `before` 参数用于实现分页

**4. put_writes() - 保存中间写入**

```python
def put_writes(
    self,
    config: RunnableConfig,
    writes: Sequence[tuple[str, Any]],
    task_id: str,
    task_path: str = ""
) -> None:
    """
    保存中间写入操作（用于 subgraphs）
    
    Args:
        config: 包含 thread_id 和 checkpoint_id
        writes: 写入操作列表 [(channel_name, value), ...]
        task_id: 任务 ID
        task_path: 任务路径（嵌套 subgraph 时使用）
        
    调用时机：
        - Subgraph 执行时
        - 需要记录中间状态时
    """
```

**关键点**：
- 可以空实现（如果不需要支持 subgraph 状态恢复）
- 如果需要完整支持，应存储到单独的集合

**5. delete_thread() - 删除 Thread**

```python
def delete_thread(self, thread_id: str) -> None:
    """
    删除指定 thread 的所有 checkpoints
    
    Args:
        thread_id: 线程 ID
        
    调用时机：
        - 用户删除对话历史时
        - 清理过期数据时
    """
```

**关键点**：
- 可以实现硬删除或软删除
- 需要考虑级联删除（writes、blobs 等）

#### 同步 vs 异步接口

LangGraph 要求同时实现同步和异步两套接口。在实际开发中，我们有两种选择：

**选择 1：真正的异步驱动**

```python
# 使用 motor（MongoDB 异步驱动）
async def aget_tuple(self, config: RunnableConfig) -> Optional[CheckpointTuple]:
    doc = await self._collection.find_one({"thread_id": thread_id})
    return self._deserialize(doc)
```

**优点**：真正的非阻塞 I/O，高并发性能好  
**缺点**：代码复杂度高，motor 生态不如 pymongo 成熟

**选择 2：同步驱动 + 异步包装**

```python
# 使用 pymongo（同步驱动）
async def aget_tuple(self, config: RunnableConfig) -> Optional[CheckpointTuple]:
    return self.get_tuple(config)  # 直接调用同步方法
```

**优点**：实现简单，pymongo 生态成熟  
**缺点**：在异步环境中会被放到线程池执行

**我的选择**：对于 checkpoint 这种低频操作（每轮对话才保存一次），选择 **pymongo + 异步包装** 已经足够，而且大大降低了实现复杂度。

### 2.2 InMemorySaver - 官方参考实现

理解了 BaseCheckpointSaver 的接口规范后，让我们看看 LangGraph 官方提供的 `InMemorySaver` 是如何实现这些抽象方法的。

#### InMemorySaver 的核心设计

```python
class InMemorySaver(BaseCheckpointSaver[str]):
    """内存版 Checkpointer（官方参考实现）"""
    
    def __init__(self, *, serde: Optional[SerializerProtocol] = None):
        super().__init__(serde=serde)
        # 核心数据结构
        self.storage = defaultdict(lambda: defaultdict(dict))
        self.writes = defaultdict(dict)
        self.blobs = {}
```

**核心数据结构解析**：

```python
# 1. storage: 存储 checkpoint 核心数据
storage: defaultdict[
    str,  # thread_id
    dict[
        str,  # checkpoint_ns (命名空间)
        dict[
            str,  # checkpoint_id
            tuple[
                tuple[str, bytes],  # checkpoint 序列化数据
                tuple[str, bytes],  # metadata 序列化数据
                Optional[str]       # parent_checkpoint_id
            ]
        ]
    ]
]

# 2. writes: 存储中间写入操作
writes: defaultdict[
    tuple[str, str, str],  # (thread_id, checkpoint_ns, checkpoint_id)
    dict[
        tuple[str, int],   # (task_id, idx)
        tuple[str, str, tuple[str, bytes], str]  # 写入数据
    ]
]

# 3. blobs: 存储 channel values
blobs: dict[
    tuple[str, str, str, Union[str, int, float]],  # (thread_id, ns, channel, version)
    tuple[str, bytes]  # 序列化的 channel value
]
```

**为什么这样设计？**

1. **三层嵌套隔离** - `thread_id -> checkpoint_ns -> checkpoint_id`，支持多线程、多命名空间
2. **Blobs 分离存储** - channel values 单独存储，避免重复序列化大对象
3. **Writes 增量存储** - 中间写入单独管理，支持 subgraph 状态回溯

#### InMemorySaver 实现的抽象方法

让我们看看 InMemorySaver 如何实现 BaseCheckpointSaver 的核心方法：

**1. get_tuple() 实现**

```python
def get_tuple(self, config: RunnableConfig) -> Optional[CheckpointTuple]:
    """获取 checkpoint（内存版）"""
    thread_id = config["configurable"]["thread_id"]
    checkpoint_ns = config["configurable"].get("checkpoint_ns", "")
    checkpoint_id = get_checkpoint_id(config)
    
    if checkpoint_id:
        # 获取指定的 checkpoint
        if saved := self.storage[thread_id][checkpoint_ns].get(checkpoint_id):
            checkpoint, metadata, parent_checkpoint_id = saved
            # 从 blobs 加载 channel values
            checkpoint_ = self.serde.loads_typed(checkpoint)
            checkpoint_["channel_values"] = self._load_blobs(
                thread_id, checkpoint_ns, checkpoint_["channel_versions"]
            )
            return CheckpointTuple(
                config=config,
                checkpoint=checkpoint_,
                metadata=self.serde.loads_typed(metadata),
                parent_config=...
            )
    else:
        # 获取最新的 checkpoint
        if checkpoints := self.storage[thread_id][checkpoint_ns]:
            checkpoint_id = max(checkpoints.keys())  # 🎯 取最大 ID（最新）
            # ... 类似上面的逻辑
```

**关键点**：
- 使用 **三层字典嵌套** 快速定位 checkpoint
- 使用 `max(checkpoints.keys())` 获取最新 checkpoint
- 通过 `_load_blobs()` 从 blobs 字典加载 channel values

**2. put() 实现**

```python
def put(
    self,
    config: RunnableConfig,
    checkpoint: Checkpoint,
    metadata: CheckpointMetadata,
    new_versions: ChannelVersions,
) -> RunnableConfig:
    """保存 checkpoint（内存版）"""
    thread_id = config["configurable"]["thread_id"]
    checkpoint_ns = config["configurable"].get("checkpoint_ns", "")
    
    # 1. 从 checkpoint 中分离 channel_values
    c = checkpoint.copy()
    c.pop("pending_sends")
    values = c.pop("channel_values")
    
    # 2. 将 channel_values 存储到 blobs
    for k, v in new_versions.items():
        self.blobs[(thread_id, checkpoint_ns, k, v)] = (
            self.serde.dumps_typed(values[k]) if k in values else ("empty", b"")
        )
    
    # 3. 存储 checkpoint 核心数据
    self.storage[thread_id][checkpoint_ns][checkpoint["id"]] = (
        self.serde.dumps_typed(c),
        self.serde.dumps_typed(metadata),
        config["configurable"].get("checkpoint_id"),  # parent
    )
    
    return {
        "configurable": {
            "thread_id": thread_id,
            "checkpoint_ns": checkpoint_ns,
            "checkpoint_id": checkpoint["id"],
        }
    }
```

**关键点**：
- **分离存储** - checkpoint 核心数据和 channel_values 分开存储
- **版本管理** - 通过 `new_versions` 管理 channel 的版本变化
- **父子关系** - 记录 parent_checkpoint_id，支持状态回溯

**3. list() 实现**

```python
def list(
    self,
    config: Optional[RunnableConfig],
    *,
    filter: Optional[Dict[str, Any]] = None,
    before: Optional[RunnableConfig] = None,
    limit: Optional[int] = None,
) -> Iterator[CheckpointTuple]:
    """列出 checkpoints（内存版）"""
    thread_ids = (config["configurable"]["thread_id"],) if config else self.storage
    
    for thread_id in thread_ids:
        for checkpoint_ns in self.storage[thread_id].keys():
            for checkpoint_id, (checkpoint, metadata_b, parent_id) in sorted(
                self.storage[thread_id][checkpoint_ns].items(),
                key=lambda x: x[0],  # 按 checkpoint_id 排序
                reverse=True,        # 降序（最新的在前）
            ):
                # 应用过滤条件
                metadata = self.serde.loads_typed(metadata_b)
                if filter and not all(
                    query_value == metadata.get(query_key)
                    for query_key, query_value in filter.items()
                ):
                    continue
                
                # 应用 limit
                if limit is not None and limit <= 0:
                    break
                elif limit is not None:
                    limit -= 1
                
                # 加载并返回 checkpoint
                checkpoint_ = self.serde.loads_typed(checkpoint)
                checkpoint_["channel_values"] = self._load_blobs(...)
                yield CheckpointTuple(...)
```

**关键点**：
- **迭代器模式** - 返回 Iterator，支持惰性加载
- **排序逻辑** - 按 checkpoint_id 降序，最新的在前
- **过滤和限制** - 支持 metadata 过滤和数量限制

**4. delete_thread() 实现**

```python
def delete_thread(self, thread_id: str) -> None:
    """删除 thread（内存版）"""
    # 1. 删除 storage 中的数据
    if thread_id in self.storage:
        del self.storage[thread_id]
    
    # 2. 删除 writes 中的数据
    for k in list(self.writes.keys()):
        if k[0] == thread_id:
            del self.writes[k]
    
    # 3. 删除 blobs 中的数据
    for k in list(self.blobs.keys()):
        if k[0] == thread_id:
            del self.blobs[k]
```

**关键点**：
- **级联删除** - 需要删除 storage、writes、blobs 三处的数据
- **遍历删除** - writes 和 blobs 使用元组 key，需要遍历查找

#### InMemorySaver 的优势与局限

| 维度 | 优势 | 局限 |
|------|------|------|
| **性能** | O(1) 随机访问<br>无序列化成本<br>内存级速度 | 重启后数据丢失<br>内存有限 |
| **设计** | 三层嵌套隔离清晰<br>Blobs 分离避免重复<br>版本管理精细 | 不支持持久化<br>无法分布式部署 |
| **适用场景** | 开发测试<br>临时对话<br>性能测试 | ❌ 生产环境<br>❌ 长期存储<br>❌ 多实例部署 |

#### 从 InMemorySaver 到 MongoDB：设计转换

理解了 InMemorySaver 的设计后，我们在实现 MongoDB 版本时需要做出调整：

| 设计元素 | InMemorySaver | MongoDBCheckpointer |
|---------|---------------|---------------------|
| **数据结构** | 三层嵌套字典 | 扁平化文档 |
| **索引策略** | 无需索引（内存） | 复合索引优化查询 |
| **Blobs 存储** | 分离存储（版本管理） | 合并存储（简化设计） |
| **序列化** | 使用 serde 协议 | 使用 pickle |
| **查询最新** | `max(keys())` | `sort([("created_at", -1)])` |
| **级联删除** | 三处手动删除 | MongoDB 单次删除 |

**核心思想**：
- InMemorySaver 追求 **性能和精细控制**
- MongoDBCheckpointer 追求 **持久化和简单可靠**

## 三、MongoDB 记忆缓存实现

### 3.1 框架设计

KaFlow-Py 的记忆系统采用**工厂模式 + 策略模式**的设计，支持多种存储后端的无缝切换。

#### 整体架构

```
src/memory/
├── __init__.py              # 模块导出
├── base.py                  # BaseCheckpointer 抽象基类
├── factory.py               # CheckpointerFactory 工厂类
├── memory_checkpointer.py   # MemoryCheckpointer (内存实现)
└── mongodb_checkpointer.py  # MongoDBCheckpointer (MongoDB 实现)
```

#### 设计模式

**1. 抽象基类（BaseCheckpointer）**

```python
# src/memory/base.py
from abc import ABC, abstractmethod
from langgraph.checkpoint.base import BaseCheckpointSaver

class BaseCheckpointer(BaseCheckpointSaver, ABC):
    """
    Checkpointer 抽象基类
    
    继承自 LangGraph 的 BaseCheckpointSaver，添加了 KaFlow-Py 特有的功能
    """
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        super().__init__()
        self.config = config or {}
        self._is_connected = False
    
    @abstractmethod
    async def setup(self) -> None:
        """初始化连接（子类实现）"""
        pass
    
    @abstractmethod
    async def teardown(self) -> None:
        """清理资源（子类实现）"""
        pass
    
    @property
    def is_connected(self) -> bool:
        """连接状态"""
        return self._is_connected
    
    def validate_config(self) -> bool:
        """验证配置（子类可重写）"""
        return True
```

**2. 工厂类（CheckpointerFactory）**

```python
# src/memory/factory.py
class CheckpointerType(str, Enum):
    """Checkpointer 类型枚举"""
    MEMORY = "memory"
    MONGODB = "mongodb"
    REDIS = "redis"          # 预留
    POSTGRESQL = "postgresql"  # 预留

class CheckpointerFactory:
    """
    Checkpointer 工厂类
    
    负责根据配置创建相应的 checkpointer 实例
    使用单例模式，确保每种类型只创建一次
    """
    
    # 实例缓存
    _instances: Dict[str, BaseCheckpointer] = {}
    
    @classmethod
    def create(
        cls, 
        provider: str, 
        config: Optional[Dict[str, Any]] = None
    ) -> Optional[BaseCheckpointer]:
        """
        创建 Checkpointer 实例
        
        Args:
            provider: 提供商类型 (memory, mongodb, redis, ...)
            config: 配置字典
            
        Returns:
            Checkpointer 实例或 None
        """
        config = config or {}
        
        # 生成缓存 key
        cache_key = f"{provider}_{hash(str(sorted(config.items())))}"
        
        # 检查缓存
        if cache_key in cls._instances:
            logger.debug(f"♻️ 复用已存在的 {provider} checkpointer")
            return cls._instances[cache_key]
        
        # 根据 provider 创建
        if provider == CheckpointerType.MEMORY:
            checkpointer = MemoryCheckpointer(config)
        elif provider == CheckpointerType.MONGODB:
            checkpointer = MongoDBCheckpointer(config)
        else:
            logger.error(f"❌ 不支持的 checkpointer 类型: {provider}")
            return None
        
        # 缓存实例
        cls._instances[cache_key] = checkpointer
        return checkpointer
```

#### YAML 配置驱动

KaFlow-Py 通过 YAML 配置文件控制记忆系统的行为：

```yaml
# ops_agent.yaml
global_config:
  memory:
    enabled: true                    # 是否启用记忆
    provider: "mongodb"              # 🎯 存储提供商（切换点）
    connection:                      # 连接配置
      host: "127.0.0.1"
      port: 27017
      database: "kaflow"
      collection: "checkpoints"
      username: "test"
      password: "${MEMORY_PASSWORD}"  # 环境变量
      auth_source: "admin"
```

**切换存储后端只需修改 `provider`**：

```yaml
# 切换到内存模式
memory:
  enabled: true
  provider: "memory"  # ✅ 改这里即可
```

#### 工作流程

```
1. 加载 YAML 配置
   ↓
2. 解析 memory.provider (如 "mongodb")
   ↓
3. CheckpointerFactory.create("mongodb", config)
   ↓
4. 创建 MongoDBCheckpointer 实例
   ↓
5. 调用 setup() 初始化连接
   ↓
6. 传给 LangGraph: graph.compile(checkpointer=checkpointer)
   ↓
7. LangGraph 调用 get_tuple/put 等方法
```

### 3.2 MongoDB Checkpointer 实现

#### 数据结构设计

```python
# MongoDB 文档结构
{
    "thread_id": "user@example.com_uuid_config_id",
    "checkpoint_id": "1704636800.123456",
    "parent_checkpoint_id": "1704636700.123456",
    "checkpoint_data": Binary(pickle),  # 完整的 Checkpoint 对象
    "metadata": {
        "source": "update",
        "step": 1,
        "writes": null
    },
    "username": "user@example.com",  # 从 thread_id 解析
    "created_at": ISODate("2025-01-07T10:00:00.000+08:00"),
    "updated_at": ISODate("2025-01-07T10:00:00.000+08:00")
}
```

**设计要点**：

1. **扁平化结构** - 不像 InMemorySaver 嵌套三层，而是扁平存储，便于索引
2. **pickle 序列化** - 直接序列化整个 Checkpoint，避免分离 blobs 的复杂性
3. **提取 username** - 从 thread_id 解析用户名，支持按用户查询
4. **时区感知** - 使用东八区时间，避免时区转换问题

#### 索引策略

```python
# 创建索引
self._collection.create_index([
    ("thread_id", ASCENDING), 
    ("checkpoint_id", DESCENDING)
])  # 复合索引：快速查询某个 thread 的最新 checkpoint

self._collection.create_index([
    ("created_at", DESCENDING)
])  # 时间索引：按时间排序

self._collection.create_index([
    ("username", ASCENDING), 
    ("created_at", DESCENDING)
])  # 用户索引：按用户查询历史
```

#### 核心实现

**1. 初始化和连接管理**

```python
class MongoDBCheckpointer(BaseCheckpointer):
    # 🎯 类级别的单例客户端（避免线程泄漏）
    _shared_client = None
    _shared_client_uri = None
    _client_lock = None
    
    def __init__(self, config: Dict[str, Any]):
        super().__init__(config)
        
        # 提取配置
        self.host = config.get("host", "localhost")
        self.port = int(config.get("port", 27017))
        self.database_name = config.get("database", "kaflow")
        self.collection_name = config.get("collection", "checkpoints")
        self.username = config.get("username", "")
        self.password = config.get("password", "")
        self.auth_source = config.get("auth_source", "admin")
        
        # 🎯 从环境变量提取密码
        if self.username and self.password:
            password = os.environ.get(
                self.password.replace("${", "").replace("}", ""),
                self.password
            )
            self._uri = f"mongodb://{self.username}:{password}@{self.host}:{self.port}/{self.database_name}?authSource={self.auth_source}"
        else:
            self._uri = f"mongodb://{self.host}:{self.port}/{self.database_name}"
        
        # 初始化锁
        if MongoDBCheckpointer._client_lock is None:
            import threading
            MongoDBCheckpointer._client_lock = threading.Lock()
    
    def _get_or_create_shared_client(self):
        """
        获取或创建共享的 MongoDB 客户端（单例模式）
        
        关键：避免每个实例都创建 MongoClient，导致线程泄漏
        """
        with MongoDBCheckpointer._client_lock:
            # 如果已有客户端且 URI 匹配，直接复用
            if (MongoDBCheckpointer._shared_client is not None and 
                MongoDBCheckpointer._shared_client_uri == self._uri):
                return MongoDBCheckpointer._shared_client
            
            # 创建新的客户端
            from pymongo import MongoClient
            cn_tz = timezone(timedelta(hours=8))
            
            MongoDBCheckpointer._shared_client = MongoClient(
                self._uri,
                serverSelectionTimeoutMS=5000,
                connectTimeoutMS=5000,
                maxPoolSize=5,  # Docker 环境减少连接数
                minPoolSize=1,
                connect=False,  # 延迟连接
                tz_aware=True,  # 时区感知
                tzinfo=cn_tz    # 东八区
            )
            MongoDBCheckpointer._shared_client_uri = self._uri
            
            # 测试连接
            MongoDBCheckpointer._shared_client.admin.command('ping')
            logger.info("✅ MongoDB 共享客户端创建成功")
            
            return MongoDBCheckpointer._shared_client
```

**2. get_tuple() - 读取 Checkpoint**

```python
def get_tuple(self, config: Dict[str, Any]) -> Optional[CheckpointTuple]:
    """获取指定的 checkpoint"""
    if not self._ensure_connected():
        return None
    
    thread_id = config.get("configurable", {}).get("thread_id")
    checkpoint_id = config.get("configurable", {}).get("checkpoint_id")
    
    # 构建查询
    query = {"thread_id": thread_id}
    if checkpoint_id:
        query["checkpoint_id"] = checkpoint_id
    
    # 查询最新的 checkpoint（按创建时间降序）
    doc = self._collection.find_one(query, sort=[("created_at", -1)])
    
    if not doc:
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
```

**3. put() - 保存 Checkpoint**

```python
def put(
    self, 
    config: Dict[str, Any], 
    checkpoint: Checkpoint, 
    metadata: CheckpointMetadata, 
    new_versions: ChannelVersions
) -> Dict[str, Any]:
    """保存 checkpoint"""
    if not self._ensure_connected():
        return config
    
    thread_id = config.get("configurable", {}).get("thread_id")
    checkpoint_id = checkpoint.get("id", str(self._get_cn_time().timestamp()))
    parent_checkpoint_id = config.get("configurable", {}).get("checkpoint_id")
    
    # 序列化 checkpoint
    checkpoint_data = pickle.dumps(checkpoint)
    
    # 从 thread_id 提取 username
    username = self._extract_username_from_thread_id(thread_id)
    
    # 获取东八区时间
    cn_time = self._get_cn_time()
    
    # 构建文档
    doc = {
        "thread_id": thread_id,
        "checkpoint_id": checkpoint_id,
        "parent_checkpoint_id": parent_checkpoint_id,
        "checkpoint_data": checkpoint_data,
        "metadata": dict(metadata) if metadata else {},
        "username": username,
        "created_at": cn_time,
        "updated_at": cn_time,
    }
    
    # upsert（存在则更新，不存在则插入）
    self._collection.update_one(
        {"thread_id": thread_id, "checkpoint_id": checkpoint_id},
        {"$set": doc},
        upsert=True
    )
    
    logger.debug(f"💾 checkpoint 已保存: {checkpoint_id}")
    
    return {
        "configurable": {
            "thread_id": thread_id,
            "checkpoint_id": checkpoint_id,
        }
    }
```

**4. list() - 列出 Checkpoints**

```python
def list(
    self, 
    config: Dict[str, Any], 
    *, 
    limit: Optional[int] = None, 
    before: Optional[Dict[str, Any]] = None
) -> Iterator[CheckpointTuple]:
    """列出指定 thread 的所有 checkpoints"""
    if not self._ensure_connected():
        return
    
    thread_id = config.get("configurable", {}).get("thread_id")
    query = {"thread_id": thread_id}
    
    # before 条件（用于分页）
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
        yield CheckpointTuple(
            config=config,
            checkpoint=checkpoint,
            metadata=doc.get("metadata", {}),
            parent_config={
                "configurable": {
                    "thread_id": thread_id,
                    "checkpoint_id": doc.get("parent_checkpoint_id"),
                }
            } if doc.get("parent_checkpoint_id") else None,
        )
```

**5. 异步接口实现**

```python
# 直接调用同步方法（pymongo 是同步驱动）
async def aget_tuple(self, config: Dict[str, Any]) -> Optional[CheckpointTuple]:
    return self.get_tuple(config)

async def aput(self, config, checkpoint, metadata, new_versions):
    return self.put(config, checkpoint, metadata, new_versions)

async def alist(self, config, *, filter=None, before=None, limit=None):
    for item in self.list(config, before=before, limit=limit):
        yield item
```

#### 辅助功能

**1. 从 thread_id 提取 username**

```python
@staticmethod
def _extract_username_from_thread_id(thread_id: str) -> Optional[str]:
    """
    从 thread_id 中提取 username
    
    thread_id 格式: username_uuid_config_id
    例如: user@example.com_uuid_1
    """
    if not thread_id:
        return None
    
    parts = thread_id.split('_')
    if len(parts) < 3:
        return None
    
    return parts[0]  # 第一个部分是 username
```

**2. 东八区时间**

```python
@staticmethod
def _get_cn_time() -> datetime:
    """获取东八区（中国）时间"""
    cn_tz = timezone(timedelta(hours=8))
    return datetime.now(cn_tz)
```

**3. 消息去重**

```python
def _format_messages(self, messages: list) -> list:
    """
    格式化消息列表（自动去重）
    
    原因：LangGraph 的 checkpoint 包含完整消息列表，
         每个 checkpoint 都会重复之前的消息
    """
    formatted = []
    seen_human_contents = set()
    
    for msg in messages:
        msg_type = type(msg).__name__
        content = msg.content if hasattr(msg, "content") else ""
        
        # 去重逻辑：跳过重复的 HumanMessage
        if "Human" in msg_type:
            # 子串匹配（因为有些消息可能被截断）
            is_duplicate = any(
                seen_content in content 
                for seen_content in seen_human_contents
            )
            if is_duplicate:
                continue
            seen_human_contents.add(content)
        
        formatted.append({
            "type": msg_type,
            "content": content,
            "role": self._infer_role(msg_type),
        })
    
    return formatted
```

### 3.3 历史对话查询 API

除了 LangGraph 要求的接口，MongoDBCheckpointer 还提供了额外的查询功能。

#### 1. 获取会话列表

```python
def get_thread_list(
    self,
    username: Optional[str] = None,
    page: int = 1,
    page_size: int = 20,
    order: str = "desc"
) -> Dict[str, Any]:
    """
    获取会话列表（支持按用户筛选）
    
    Args:
        username: 用户名（可选）
        page: 页码
        page_size: 每页大小
        order: 排序方式（desc/asc）
        
    Returns:
        {
            "total": 总数,
            "threads": [
                {
                    "thread_id": "...",
                    "username": "...",
                    "first_message": "...",
                    "last_updated": "...",
                    "message_count": 10
                }
            ]
        }
    """
    # 使用 MongoDB 聚合管道
    pipeline = []
    
    # 1. 筛选用户
    if username:
        pipeline.append({"$match": {"username": username}})
    
    # 2. 按 thread_id 分组
    pipeline.append({"$sort": {"thread_id": 1, "created_at": 1}})
    pipeline.append({
        "$group": {
            "_id": "$thread_id",
            "username": {"$first": "$username"},
            "last_updated": {"$max": "$updated_at"},
            "message_count": {"$sum": 1},
            "latest_checkpoint": {"$last": "$checkpoint_data"},
        }
    })
    
    # 3. 排序
    pipeline.append({
        "$sort": {"last_updated": -1 if order == "desc" else 1}
    })
    
    # 执行查询
    all_threads = list(self._collection.aggregate(pipeline))
    
    # 分页
    start_idx = (page - 1) * page_size
    end_idx = start_idx + page_size
    paginated_threads = all_threads[start_idx:end_idx]
    
    # 格式化结果
    threads = []
    for thread_data in paginated_threads:
        # 从 checkpoint 中提取第一条消息
        first_message = self._extract_first_message(
            thread_data.get("latest_checkpoint")
        )
        
        threads.append({
            "thread_id": thread_data["_id"],
            "username": thread_data.get("username"),
            "first_message": first_message,
            "last_updated": thread_data["last_updated"].isoformat(),
            "message_count": thread_data.get("message_count", 0),
        })
    
    return {
        "total": len(all_threads),
        "threads": threads
    }
```

#### 2. 获取对话消息

```python
def get_flat_messages(
    self,
    thread_id: str,
    page: int = 1,
    page_size: int = 20,
    order: str = "desc"
) -> Dict[str, Any]:
    """
    获取指定 thread 的消息列表（按单条消息分页）
    
    Args:
        thread_id: 线程 ID
        page: 页码
        page_size: 每页大小
        order: 排序方式
        
    Returns:
        {
            "total": 消息总数,
            "messages": [
                {
                    "type": "HumanMessage",
                    "content": "...",
                    "role": "human",
                    "timestamp": "..."
                }
            ]
        }
    """
    # 1. 获取最新的 checkpoint（包含完整对话历史）
    latest_checkpoint = self._collection.find_one(
        {"thread_id": thread_id},
        sort=[("created_at", DESCENDING)]
    )
    
    if not latest_checkpoint:
        return {"total": 0, "messages": []}
    
    # 2. 反序列化并提取消息
    checkpoint = pickle.loads(latest_checkpoint["checkpoint_data"])
    checkpoint_messages = checkpoint.get("channel_values", {}).get("messages", [])
    
    # 3. 格式化所有消息
    all_messages = self._format_messages(checkpoint_messages)
    
    # 4. 根据排序方式调整顺序
    if order == "desc":
        all_messages = list(reversed(all_messages))
    
    # 5. 分页
    total = len(all_messages)
    start_idx = (page - 1) * page_size
    end_idx = start_idx + page_size
    paginated_messages = all_messages[start_idx:end_idx]
    
    return {
        "total": total,
        "messages": paginated_messages
    }
```

#### 3. 获取 Checkpoint 历史

```python
def get_history_messages(
    self, 
    thread_id: str, 
    page: int = 1, 
    page_size: int = 20,
    order: str = "desc"
) -> Dict[str, Any]:
    """
    获取指定 thread 的历史 checkpoints（按 checkpoint 分页）
    
    用途：查看对话的演变过程，每个 checkpoint 是一个快照
    """
    total = self._collection.count_documents({"thread_id": thread_id})
    skip = (page - 1) * page_size
    
    cursor = self._collection.find(
        {"thread_id": thread_id}
    ).sort("created_at", DESCENDING if order == "desc" else ASCENDING).skip(skip).limit(page_size)
    
    messages = []
    for doc in cursor:
        checkpoint = pickle.loads(doc["checkpoint_data"])
        checkpoint_messages = checkpoint.get("channel_values", {}).get("messages", [])
        
        messages.append({
            "checkpoint_id": doc["checkpoint_id"],
            "messages": self._format_messages(checkpoint_messages),
            "created_at": doc["created_at"].isoformat(),
        })
    
    return {
        "total": total,
        "messages": messages
    }
```

## 四、如何使用

### 4.1 YAML 配置

在场景配置文件中启用 MongoDB：

```yaml
# src/core/config/ops_agent.yaml
global_config:
  memory:
    enabled: true                          # 是否启用记忆
    provider: "mongodb"                    # 存储提供商: memory|mongodb
    connection:
      host: "127.0.0.1"                    # MongoDB 主机
      port: 27017                          # MongoDB 端口
      database: "kaflow"                   # 数据库名称
      collection: "checkpoints"            # 集合名称
      username: "test"                     # 用户名
      password: "${MEMORY_PASSWORD}"       # 密码（环境变量）
      auth_source: "admin"                 # 认证数据库
```

**切换到内存模式**：

```yaml
global_config:
  memory:
    enabled: true
    provider: "memory"  # ✅ 只需改这里
```

### 4.2 环境变量配置

在项目根目录创建 `.env` 文件：

```bash
# .env

# MongoDB 密码（必须）
MEMORY_PASSWORD=your_mongodb_password_here

# LLM API Key
DEEPSEEK_API_KEY=sk-xxx
```

**安全提示**：
- ⚠️ 永远不要将 `.env` 文件提交到 Git 仓库
- 在 `.gitignore` 中添加 `.env`
- 生产环境使用 Docker Secrets 或云服务的密钥管理

### 4.3 环境变量提取机制

MongoDBCheckpointer 会自动从环境变量中提取密码：

```python
# mongodb_checkpointer.py
if self.username and self.password:
    # 如果 password 是 "${MEMORY_PASSWORD}"，则从环境变量中获取
    password = os.environ.get(
        self.password.replace("${", "").replace("}", ""),
        self.password  # 如果环境变量不存在，使用原值
    )
```

**工作原理**：
1. YAML 中配置 `password: "${MEMORY_PASSWORD}"`
2. 提取环境变量名：`MEMORY_PASSWORD`
3. 从 `os.environ` 中获取实际密码值
4. 构建 MongoDB 连接 URI


## 五、总结

### 核心收获

经过这次实现，让我对 LangGraph 的 Checkpoint 机制有了更深入的理解：

1. **理解接口契约** - LangGraph 定义了 10 个抽象方法，必须全部实现才能正常工作
2. **参考官方实现** - InMemorySaver 的代码质量很高，设计思路可以直接借鉴
3. **单例模式很重要** - 在涉及数据库连接时，必须考虑单例，避免资源泄漏
4. **工厂模式的优雅** - 通过工厂模式实现存储后端的无缝切换，配置驱动非常灵活

### 设计亮点

**1. 工厂模式 + 策略模式**

通过 `CheckpointerFactory` 实现存储后端的无缝切换，用户只需修改 YAML 配置中的 `provider` 即可。

**2. 类级别单例客户端**

所有 MongoDBCheckpointer 实例共享同一个 MongoClient，避免线程泄漏和资源浪费。

**3. 环境变量注入**

敏感信息（如密码）通过环境变量传入，支持 `${ENV_VAR}` 语法，安全又灵活。

**4. 扁平化存储 + 索引优化**

不像 InMemorySaver 嵌套三层，而是扁平存储，配合索引实现高效查询。

**5. 扩展查询 API**

除了 LangGraph 要求的接口，还提供了 `get_thread_list`、`get_flat_messages` 等实用功能。


---

**项目地址**：
- 后端：[kaflow-py](https://github.com/yangkun19921001/kaflow-py)
- 前端：[kaflow-web](https://github.com/yangkun19921001/kaflow-web)

如果这篇文章对你有帮助，欢迎点赞、转发、Star 支持！🙏

