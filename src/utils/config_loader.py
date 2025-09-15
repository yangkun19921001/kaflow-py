"""
KaFlow-Py 配置加载器模块

提供YAML和JSON配置文件的加载、缓存和环境变量替换功能

Author: DevYK
WeChat: DevYK
Email: yang1001yk@gmail.com
Github: https://github.com/yangkun19921001
"""

import os
import yaml
import json
from pathlib import Path
from typing import Dict, Any, Optional, Union, List
from .logger import get_logger
from .json_utils import safe_json_loads

logger = get_logger(__name__)


class ConfigLoader:
    """配置加载器类，提供统一的配置文件加载接口"""
    
    def __init__(self, cache_enabled: bool = True):
        """
        初始化配置加载器
        
        Args:
            cache_enabled: 是否启用配置缓存
        """
        self.cache_enabled = cache_enabled
        self._config_cache: Dict[str, Dict[str, Any]] = {}
        self._file_timestamps: Dict[str, float] = {}
    
    def load_config(
        self,
        file_path: Union[str, Path],
        format_type: Optional[str] = None,
        encoding: str = 'utf-8',
        force_reload: bool = False
    ) -> Dict[str, Any]:
        """
        加载配置文件
        
        Args:
            file_path: 配置文件路径
            format_type: 配置文件格式 ('yaml', 'json')，None时自动检测
            encoding: 文件编码
            force_reload: 是否强制重新加载
            
        Returns:
            配置字典
        """
        file_path = Path(file_path).resolve()
        file_path_str = str(file_path)
        
        # 检查文件是否存在
        if not file_path.exists():
            logger.warning(f"配置文件不存在: {file_path}")
            return {}
        
        # 检查缓存
        if self.cache_enabled and not force_reload:
            cached_config = self._get_cached_config(file_path_str)
            if cached_config is not None:
                return cached_config
        
        # 自动检测文件格式
        if format_type is None:
            format_type = self._detect_format(file_path)
        
        try:
            # 加载配置文件
            with open(file_path, 'r', encoding=encoding) as f:
                content = f.read()
            
            if format_type == 'yaml':
                config = yaml.safe_load(content) or {}
            elif format_type == 'json':
                config = safe_json_loads(content, default={})
            else:
                logger.error(f"不支持的配置文件格式: {format_type}")
                return {}
            
            # 处理环境变量替换
            processed_config = self._process_env_vars(config)
            
            # 缓存配置
            if self.cache_enabled:
                self._cache_config(file_path_str, processed_config)
            
            logger.info(f"成功加载配置文件: {file_path}")
            return processed_config
            
        except Exception as e:
            logger.error(f"加载配置文件失败 {file_path}: {e}")
            return {}
    
    def _detect_format(self, file_path: Path) -> str:
        """自动检测配置文件格式"""
        suffix = file_path.suffix.lower()
        if suffix in ['.yaml', '.yml']:
            return 'yaml'
        elif suffix in ['.json']:
            return 'json'
        else:
            # 尝试通过内容检测
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    content = f.read().strip()
                    if content.startswith('{') or content.startswith('['):
                        return 'json'
                    else:
                        return 'yaml'
            except Exception:
                return 'yaml'  # 默认为YAML
    
    def _get_cached_config(self, file_path: str) -> Optional[Dict[str, Any]]:
        """获取缓存的配置"""
        if file_path not in self._config_cache:
            return None
        
        # 检查文件是否被修改
        try:
            current_mtime = os.path.getmtime(file_path)
            cached_mtime = self._file_timestamps.get(file_path, 0)
            
            if current_mtime > cached_mtime:
                # 文件已被修改，清除缓存
                self._clear_cache(file_path)
                return None
            
            logger.debug(f"使用缓存的配置: {file_path}")
            return self._config_cache[file_path]
            
        except OSError:
            # 文件不存在或无法访问，清除缓存
            self._clear_cache(file_path)
            return None
    
    def _cache_config(self, file_path: str, config: Dict[str, Any]) -> None:
        """缓存配置"""
        try:
            self._config_cache[file_path] = config
            self._file_timestamps[file_path] = os.path.getmtime(file_path)
            logger.debug(f"缓存配置: {file_path}")
        except OSError as e:
            logger.warning(f"无法缓存配置 {file_path}: {e}")
    
    def _clear_cache(self, file_path: str) -> None:
        """清除指定文件的缓存"""
        self._config_cache.pop(file_path, None)
        self._file_timestamps.pop(file_path, None)
        logger.debug(f"清除缓存: {file_path}")
    
    def clear_all_cache(self) -> None:
        """清除所有缓存"""
        self._config_cache.clear()
        self._file_timestamps.clear()
        logger.info("已清除所有配置缓存")
    
    def _process_env_vars(self, config: Any) -> Any:
        """递归处理配置中的环境变量"""
        if isinstance(config, dict):
            return {key: self._process_env_vars(value) for key, value in config.items()}
        elif isinstance(config, list):
            return [self._process_env_vars(item) for item in config]
        elif isinstance(config, str):
            return self._replace_env_vars(config)
        else:
            return config
    
    def _replace_env_vars(self, value: str) -> str:
        """替换字符串中的环境变量"""
        if not isinstance(value, str):
            return value
        
        # 支持多种环境变量格式
        # ${VAR_NAME} 或 ${VAR_NAME:default_value}
        import re
        
        def replace_match(match):
            var_expr = match.group(1)
            if ':' in var_expr:
                var_name, default_value = var_expr.split(':', 1)
                return os.getenv(var_name.strip(), default_value.strip())
            else:
                return os.getenv(var_expr.strip(), match.group(0))
        
        # ${VAR_NAME} 格式
        value = re.sub(r'\$\{([^}]+)\}', replace_match, value)
        
        # $VAR_NAME 格式（简单情况）
        if value.startswith('$') and not value.startswith('${'):
            env_var = value[1:]
            return os.getenv(env_var, value)
        
        return value
    
    def merge_configs(self, *configs: Dict[str, Any]) -> Dict[str, Any]:
        """
        合并多个配置字典
        
        Args:
            *configs: 要合并的配置字典
            
        Returns:
            合并后的配置字典
        """
        result = {}
        
        for config in configs:
            if not isinstance(config, dict):
                continue
            
            result = self._deep_merge(result, config)
        
        return result
    
    def _deep_merge(self, base: Dict[str, Any], update: Dict[str, Any]) -> Dict[str, Any]:
        """深度合并两个字典"""
        result = base.copy()
        
        for key, value in update.items():
            if (key in result and 
                isinstance(result[key], dict) and 
                isinstance(value, dict)):
                result[key] = self._deep_merge(result[key], value)
            else:
                result[key] = value
        
        return result


# 全局配置加载器实例
_global_loader = ConfigLoader()


def load_yaml_config(
    file_path: Union[str, Path],
    encoding: str = 'utf-8',
    force_reload: bool = False
) -> Dict[str, Any]:
    """
    加载YAML配置文件
    
    Args:
        file_path: YAML文件路径
        encoding: 文件编码
        force_reload: 是否强制重新加载
        
    Returns:
        配置字典
    """
    return _global_loader.load_config(
        file_path=file_path,
        format_type='yaml',
        encoding=encoding,
        force_reload=force_reload
    )


def load_json_config(
    file_path: Union[str, Path],
    encoding: str = 'utf-8',
    force_reload: bool = False
) -> Dict[str, Any]:
    """
    加载JSON配置文件
    
    Args:
        file_path: JSON文件路径
        encoding: 文件编码
        force_reload: 是否强制重新加载
        
    Returns:
        配置字典
    """
    return _global_loader.load_config(
        file_path=file_path,
        format_type='json',
        encoding=encoding,
        force_reload=force_reload
    )


def load_config_from_multiple_sources(
    *file_paths: Union[str, Path],
    base_config: Optional[Dict[str, Any]] = None
) -> Dict[str, Any]:
    """
    从多个配置文件源加载并合并配置
    
    Args:
        *file_paths: 配置文件路径列表
        base_config: 基础配置字典
        
    Returns:
        合并后的配置字典
    """
    configs = []
    
    if base_config:
        configs.append(base_config)
    
    for file_path in file_paths:
        config = _global_loader.load_config(file_path)
        if config:
            configs.append(config)
    
    return _global_loader.merge_configs(*configs)


def get_config_value(
    config: Dict[str, Any],
    key_path: str,
    default: Any = None,
    separator: str = '.'
) -> Any:
    """
    通过点分隔的路径获取配置值
    
    Args:
        config: 配置字典
        key_path: 点分隔的键路径，如 'database.host'
        default: 默认值
        separator: 路径分隔符
        
    Returns:
        配置值或默认值
    """
    keys = key_path.split(separator)
    current = config
    
    try:
        for key in keys:
            if isinstance(current, dict) and key in current:
                current = current[key]
            else:
                return default
        return current
    except (KeyError, TypeError):
        return default


def set_config_value(
    config: Dict[str, Any],
    key_path: str,
    value: Any,
    separator: str = '.'
) -> None:
    """
    通过点分隔的路径设置配置值
    
    Args:
        config: 配置字典
        key_path: 点分隔的键路径，如 'database.host'
        value: 要设置的值
        separator: 路径分隔符
    """
    keys = key_path.split(separator)
    current = config
    
    for key in keys[:-1]:
        if key not in current or not isinstance(current[key], dict):
            current[key] = {}
        current = current[key]
    
    current[keys[-1]] = value


def validate_required_keys(
    config: Dict[str, Any],
    required_keys: List[str],
    separator: str = '.'
) -> List[str]:
    """
    验证配置中是否包含必需的键
    
    Args:
        config: 配置字典
        required_keys: 必需的键列表（支持点分隔路径）
        separator: 路径分隔符
        
    Returns:
        缺失的键列表
    """
    missing_keys = []
    
    for key in required_keys:
        value = get_config_value(config, key, separator=separator)
        if value is None:
            missing_keys.append(key)
    
    return missing_keys


def clear_config_cache() -> None:
    """清除全局配置缓存"""
    _global_loader.clear_all_cache()