"""
KaFlow-Py MemoryCheckpointer

基于内存的 Checkpointer 实现（使用 LangGraph 的 MemorySaver）

Author: DevYK
微信公众号: DevYK
Email: yang1001yk@gmail.com
Github: https://github.com/yangkun19921001
"""

from typing import Optional, Dict, Any
from langgraph.checkpoint.memory import MemorySaver
from ..utils.logger import get_logger

logger = get_logger(__name__)


class MemoryCheckpointer(MemorySaver):
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
        super().__init__()
        self.config = config or {}
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

