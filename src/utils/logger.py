"""
KaFlow-Py 日志记录模块

提供统一的日志记录功能，支持多种输出格式和级别控制

Author: DevYK  
WeChat: DevYK
Email: yang1001yk@gmail.com
Github: https://github.com/yangkun19921001
"""

import logging
import logging.handlers
import sys
import json
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, Optional, Union, Literal
from enum import Enum


class LogLevel(Enum):
    """日志级别枚举"""
    DEBUG = "DEBUG"
    INFO = "INFO" 
    WARNING = "WARNING"
    ERROR = "ERROR"
    CRITICAL = "CRITICAL"


class LogFormat(Enum):
    """日志格式枚举"""
    JSON = "json"
    TEXT = "text"
    SIMPLE = "simple"


class ColoredFormatter(logging.Formatter):
    """彩色日志格式化器"""
    
    # ANSI 颜色代码
    COLORS = {
        'DEBUG': '\033[36m',     # 青色
        'INFO': '\033[32m',      # 绿色
        'WARNING': '\033[33m',   # 黄色
        'ERROR': '\033[31m',     # 红色
        'CRITICAL': '\033[35m',  # 紫色
        'RESET': '\033[0m'       # 重置
    }
    
    def format(self, record):
        """格式化日志记录"""
        log_color = self.COLORS.get(record.levelname, self.COLORS['RESET'])
        reset_color = self.COLORS['RESET']
        
        # 添加颜色
        record.levelname = f"{log_color}{record.levelname}{reset_color}"
        
        return super().format(record)


class JsonFormatter(logging.Formatter):
    """JSON 格式化器"""
    
    def format(self, record):
        """格式化为 JSON 格式"""
        log_entry = {
            'timestamp': datetime.fromtimestamp(record.created).isoformat(),
            'level': record.levelname,
            'logger': record.name,
            'message': record.getMessage(),
            'module': record.module,
            'function': record.funcName,
            'line': record.lineno
        }
        
        # 添加异常信息
        if record.exc_info:
            log_entry['exception'] = self.formatException(record.exc_info)
            
        # 添加额外字段
        if hasattr(record, 'extra_fields'):
            log_entry.update(record.extra_fields)
            
        return json.dumps(log_entry, ensure_ascii=False)


class KaFlowLogger:
    """KaFlow 日志记录器类"""
    
    _loggers: Dict[str, logging.Logger] = {}
    _configured: bool = False
    
    def __init__(
        self,
        name: str,
        level: Union[LogLevel, str] = LogLevel.INFO,
        format_type: Union[LogFormat, str] = LogFormat.TEXT,
        output: Literal["stdout", "file", "both"] = "stdout",
        file_path: Optional[str] = None,
        max_size: str = "100MB",
        max_files: int = 10,
        enable_color: bool = True
    ):
        """
        初始化日志记录器
        
        Args:
            name: 日志记录器名称
            level: 日志级别
            format_type: 日志格式类型
            output: 输出目标
            file_path: 日志文件路径
            max_size: 最大文件大小
            max_files: 最大文件数量
            enable_color: 是否启用彩色输出
        """
        self.name = name
        self.level = level if isinstance(level, LogLevel) else LogLevel(level)
        self.format_type = format_type if isinstance(format_type, LogFormat) else LogFormat(format_type)
        self.output = output
        self.file_path = file_path
        self.max_size = self._parse_size(max_size)
        self.max_files = max_files
        self.enable_color = enable_color
        
        self._setup_logger()
    
    def _parse_size(self, size_str: str) -> int:
        """解析大小字符串为字节数"""
        size_str = size_str.upper().strip()
        multipliers = {'GB': 1024**3, 'MB': 1024**2, 'KB': 1024, 'B': 1}
        
        # 先检查完整后缀
        for suffix, multiplier in multipliers.items():
            if size_str.endswith(suffix):
                number_part = size_str[:-len(suffix)].strip()
                if number_part:
                    try:
                        return int(number_part) * multiplier
                    except ValueError:
                        continue
        
        # 处理简写形式 (如 100M -> 100MB, 100K -> 100KB, 100G -> 100GB)
        short_multipliers = {'G': 1024**3, 'M': 1024**2, 'K': 1024}
        for suffix, multiplier in short_multipliers.items():
            if size_str.endswith(suffix):
                number_part = size_str[:-1].strip()
                if number_part:
                    try:
                        return int(number_part) * multiplier
                    except ValueError:
                        continue
        
        # 默认为字节
        try:
            return int(size_str)
        except ValueError:
            # 如果无法解析，返回默认值 100MB
            return 100 * 1024**2
    
    def _get_formatter(self) -> logging.Formatter:
        """获取格式化器"""
        if self.format_type == LogFormat.JSON:
            return JsonFormatter()
        elif self.format_type == LogFormat.SIMPLE:
            fmt = "%(levelname)s - %(message)s"
        else:  # TEXT
            fmt = "%(asctime)s - %(name)s - %(levelname)s - %(module)s:%(funcName)s:%(lineno)d - %(message)s"
        
        if self.enable_color and self.output in ["stdout", "both"]:
            return ColoredFormatter(fmt)
        else:
            return logging.Formatter(fmt)
    
    def _setup_logger(self):
        """设置日志记录器"""
        if self.name in self._loggers:
            return self._loggers[self.name]
        
        logger = logging.getLogger(self.name)
        logger.setLevel(getattr(logging, self.level.value))
        
        # 清除现有处理器
        logger.handlers.clear()
        
        formatter = self._get_formatter()
        
        # 控制台输出
        if self.output in ["stdout", "both"]:
            console_handler = logging.StreamHandler(sys.stdout)
            console_handler.setFormatter(formatter)
            logger.addHandler(console_handler)
        
        # 文件输出
        if self.output in ["file", "both"] and self.file_path:
            # 确保日志目录存在
            log_path = Path(self.file_path)
            log_path.parent.mkdir(parents=True, exist_ok=True)
            
            # 使用轮转文件处理器
            file_handler = logging.handlers.RotatingFileHandler(
                self.file_path,
                maxBytes=self.max_size,
                backupCount=self.max_files,
                encoding='utf-8'
            )
            
            # 文件输出不使用颜色
            if self.format_type == LogFormat.JSON:
                file_formatter = JsonFormatter()
            else:
                fmt = "%(asctime)s - %(name)s - %(levelname)s - %(module)s:%(funcName)s:%(lineno)d - %(message)s"
                file_formatter = logging.Formatter(fmt)
            
            file_handler.setFormatter(file_formatter)
            logger.addHandler(file_handler)
        
        self._loggers[self.name] = logger
        return logger
    
    def get_logger(self) -> logging.Logger:
        """获取日志记录器实例"""
        return self._loggers[self.name]
    
    def debug(self, message: str, **kwargs):
        """记录调试信息"""
        self._log(logging.DEBUG, message, **kwargs)
    
    def info(self, message: str, **kwargs):
        """记录信息"""
        self._log(logging.INFO, message, **kwargs)
    
    def warning(self, message: str, **kwargs):
        """记录警告"""
        self._log(logging.WARNING, message, **kwargs)
    
    def error(self, message: str, **kwargs):
        """记录错误"""
        self._log(logging.ERROR, message, **kwargs)
    
    def critical(self, message: str, **kwargs):
        """记录严重错误"""
        self._log(logging.CRITICAL, message, **kwargs)
    
    def _log(self, level: int, message: str, **kwargs):
        """内部日志记录方法"""
        logger = self.get_logger()
        
        # 创建日志记录
        record = logger.makeRecord(
            logger.name, level, "", 0, message, (), None
        )
        
        # 添加额外字段
        if kwargs:
            record.extra_fields = kwargs
        
        logger.handle(record)


# 全局配置
_global_config: Dict[str, Any] = {
    'level': LogLevel.INFO,
    'format_type': LogFormat.TEXT,
    'output': 'stdout',
    'file_path': './logs/kaflow.log',
    'max_size': '100MB',
    'max_files': 10,
    'enable_color': True
}

# 日志记录器缓存
_logger_cache: Dict[str, KaFlowLogger] = {}


def setup_logger(
    level: Union[LogLevel, str] = LogLevel.INFO,
    format_type: Union[LogFormat, str] = LogFormat.TEXT,
    output: Literal["stdout", "file", "both"] = "stdout",
    file_path: Optional[str] = None,
    max_size: str = "100MB",
    max_files: int = 10,
    enable_color: bool = True
) -> None:
    """
    全局日志配置设置
    
    Args:
        level: 日志级别
        format_type: 日志格式类型
        output: 输出目标
        file_path: 日志文件路径
        max_size: 最大文件大小
        max_files: 最大文件数量
        enable_color: 是否启用彩色输出
    """
    global _global_config
    
    _global_config.update({
        'level': level if isinstance(level, LogLevel) else LogLevel(level),
        'format_type': format_type if isinstance(format_type, LogFormat) else LogFormat(format_type),
        'output': output,
        'file_path': file_path or _global_config['file_path'],
        'max_size': max_size,
        'max_files': max_files,
        'enable_color': enable_color
    })
    
    # 清空缓存，强制重新创建日志记录器
    _logger_cache.clear()


def get_logger(name: str = "kaflow") -> KaFlowLogger:
    """
    获取日志记录器实例
    
    Args:
        name: 日志记录器名称
        
    Returns:
        KaFlowLogger: 日志记录器实例
    """
    if name not in _logger_cache:
        _logger_cache[name] = KaFlowLogger(
            name=name,
            **_global_config
        )
    
    return _logger_cache[name]


def get_standard_logger(name: str = "kaflow") -> logging.Logger:
    """
    获取标准 logging.Logger 实例
    
    Args:
        name: 日志记录器名称
        
    Returns:
        logging.Logger: 标准日志记录器实例
    """
    return get_logger(name).get_logger()


# 创建默认日志记录器
logger = get_logger()

# 便捷函数
def debug(message: str, **kwargs):
    """记录调试信息"""
    logger.debug(message, **kwargs)

def info(message: str, **kwargs):
    """记录信息"""
    logger.info(message, **kwargs)

def warning(message: str, **kwargs):
    """记录警告"""
    logger.warning(message, **kwargs)

def error(message: str, **kwargs):
    """记录错误"""
    logger.error(message, **kwargs)

def critical(message: str, **kwargs):
    """记录严重错误"""
    logger.critical(message, **kwargs)