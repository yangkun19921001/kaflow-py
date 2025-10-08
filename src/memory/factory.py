"""
KaFlow-Py CheckpointerFactory

Checkpointer 工厂类，负责创建不同类型的 checkpointer

Author: DevYK
微信公众号: DevYK
Email: yang1001yk@gmail.com
Github: https://github.com/yangkun19921001
"""

from typing import Optional, Dict, Any
from enum import Enum

from .base import BaseCheckpointer
from .memory_checkpointer import MemoryCheckpointer
from .mongodb_checkpointer import MongoDBCheckpointer
from ..utils.logger import get_logger

logger = get_logger(__name__)


class CheckpointerType(str, Enum):
    """Checkpointer 类型枚举"""
    MEMORY = "memory"
    MONGODB = "mongodb"
    REDIS = "redis"          # 预留
    POSTGRESQL = "postgresql"  # 预留
    SQLITE = "sqlite"        # 预留


class CheckpointerFactory:
    """
    Checkpointer 工厂类
    
    负责根据配置创建相应的 checkpointer 实例
    
    使用单例模式，确保每种类型的 checkpointer 只创建一次
    """
    
    # 已创建的 checkpointer 实例缓存
    _instances: Dict[str, BaseCheckpointer] = {}
    
    @classmethod
    def create(cls, provider: str, config: Optional[Dict[str, Any]] = None) -> Optional[BaseCheckpointer]:
        """
        创建 Checkpointer 实例
        
        Args:
            provider: 提供商类型 (memory, mongodb, redis, postgresql, sqlite)
            config: 配置字典
            
        Returns:
            Checkpointer 实例或 None
            
        Examples:
            >>> # 创建内存 checkpointer
            >>> checkpointer = CheckpointerFactory.create("memory")
            
            >>> # 创建 MongoDB checkpointer
            >>> checkpointer = CheckpointerFactory.create("mongodb", {
            ...     "host": "localhost",
            ...     "port": 27017,
            ...     "database": "kaflow",
            ...     "username": "admin",
            ...     "password": "password123"
            ... })
        """
        config = config or {}
        
        # 标准化 provider 名称
        provider_lower = provider.lower()
        
        # 检查是否已创建
        cache_key = f"{provider_lower}_{hash(str(sorted(config.items())))}"
        if cache_key in cls._instances:
            logger.debug(f"♻️  复用已存在的 {provider_lower} checkpointer")
            return cls._instances[cache_key]
        
        # 根据 provider 类型创建
        try:
            if provider_lower == CheckpointerType.MEMORY:
                checkpointer = cls._create_memory_checkpointer(config)
                
            elif provider_lower == CheckpointerType.MONGODB:
                checkpointer = cls._create_mongodb_checkpointer(config)
                
            elif provider_lower in (CheckpointerType.REDIS, CheckpointerType.POSTGRESQL, CheckpointerType.SQLITE):
                logger.warning(
                    f"⚠️  {provider} checkpointer 尚未实现。"
                    f"当前支持的类型: {', '.join([t.value for t in CheckpointerType if t.value in ['memory', 'mongodb']])}"
                )
                return None
                
            else:
                logger.error(f"❌ 不支持的 checkpointer 类型: {provider}")
                logger.info(f"ℹ️  支持的类型: {', '.join([t.value for t in CheckpointerType])}")
                return None
            
            # 缓存实例
            cls._instances[cache_key] = checkpointer
            return checkpointer
            
        except Exception as e:
            logger.error(f"❌ 创建 {provider} checkpointer 失败: {e}")
            import traceback
            logger.debug(traceback.format_exc())
            return None
    
    @staticmethod
    def _create_memory_checkpointer(config: Dict[str, Any]) -> MemoryCheckpointer:
        """创建内存 Checkpointer"""
        logger.info("✅ 创建 MemoryCheckpointer (内存模式)")
        return MemoryCheckpointer(config)
    
    @staticmethod
    def _create_mongodb_checkpointer(config: Dict[str, Any]) -> MongoDBCheckpointer:
        """创建 MongoDB Checkpointer"""
        logger.info("✅ 创建 MongoDBCheckpointer (MongoDB 持久化)")
        
        # 验证必要的配置
        required_keys = ["host", "database"]
        missing_keys = [key for key in required_keys if key not in config]
        
        if missing_keys:
            raise ValueError(
                f"MongoDB checkpointer 缺少必要配置: {', '.join(missing_keys)}\n"
                f"需要的配置: host, database\n"
                f"可选配置: port, username, password, collection, auth_source"
            )
        
        return MongoDBCheckpointer(config)
    
    @classmethod
    def clear_cache(cls) -> None:
        """清除所有缓存的 checkpointer 实例"""
        logger.info("🧹 清除 checkpointer 缓存")
        cls._instances.clear()


def create_checkpointer(
    provider: str,
    config: Optional[Dict[str, Any]] = None,
    auto_setup: bool = False
) -> Optional[BaseCheckpointer]:
    """
    便捷函数：创建 Checkpointer
    
    Args:
        provider: 提供商类型
        config: 配置字典
        auto_setup: 是否自动调用 setup() 方法
        
    Returns:
        Checkpointer 实例或 None
        
    Examples:
        >>> # 创建并自动设置
        >>> checkpointer = create_checkpointer("mongodb", {
        ...     "host": "localhost",
        ...     "port": 27017,
        ...     "database": "kaflow"
        ... }, auto_setup=True)
    """
    checkpointer = CheckpointerFactory.create(provider, config)
    
    if checkpointer and auto_setup:
        import asyncio
        try:
            # 如果在异步上下文中
            loop = asyncio.get_event_loop()
            if loop.is_running():
                # 已经在运行的循环中，创建任务
                asyncio.create_task(checkpointer.setup())
            else:
                # 没有运行的循环，同步执行
                loop.run_until_complete(checkpointer.setup())
        except RuntimeError:
            # 没有事件循环，创建一个新的
            asyncio.run(checkpointer.setup())
        
        logger.info("✅ Checkpointer 已自动设置")
    
    return checkpointer

