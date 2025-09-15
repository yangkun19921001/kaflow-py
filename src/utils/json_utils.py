"""
KaFlow-Py JSON 处理工具模块

提供安全的JSON解析、生成和修复功能

Author: DevYK
WeChat: DevYK
Email: yang1001yk@gmail.com
Github: https://github.com/yangkun19921001
"""

import json
import re
from typing import Any, Dict, List, Optional, Union
from .logger import get_logger

logger = get_logger(__name__)

# 尝试导入 json_repair，如果不存在则提供基础修复功能
try:
    import json_repair
    HAS_JSON_REPAIR = True
except ImportError:
    HAS_JSON_REPAIR = False
    logger.warning("json_repair 库未安装，将使用基础JSON修复功能")


def safe_json_loads(
    content: str, 
    default: Any = None, 
    repair: bool = True,
    strict: bool = False
) -> Any:
    """
    安全的JSON解析函数
    
    Args:
        content: 要解析的JSON字符串
        default: 解析失败时的默认返回值
        repair: 是否尝试修复无效的JSON
        strict: 是否使用严格模式（不允许修复）
        
    Returns:
        解析后的Python对象，失败时返回default值
    """
    if not content or not isinstance(content, str):
        logger.debug(f"无效的JSON内容类型: {type(content)}")
        return default
    
    content = content.strip()
    if not content:
        logger.debug("空的JSON内容")
        return default
    
    try:
        # 直接尝试解析
        return json.loads(content)
    except (json.JSONDecodeError, ValueError) as e:
        logger.debug(f"JSON解析失败: {e}")
        
        if strict:
            logger.error(f"严格模式下JSON解析失败: {e}")
            return default
        
        if repair:
            try:
                # 尝试修复并解析
                repaired_content = repair_json_output(content)
                if repaired_content != content:
                    return json.loads(repaired_content)
            except Exception as repair_error:
                logger.warning(f"JSON修复失败: {repair_error}")
        
        return default


def safe_json_dumps(
    obj: Any,
    ensure_ascii: bool = False,
    indent: Optional[int] = None,
    sort_keys: bool = False,
    default: Optional[callable] = None
) -> str:
    """
    安全的JSON序列化函数
    
    Args:
        obj: 要序列化的Python对象
        ensure_ascii: 是否确保ASCII编码
        indent: 缩进空格数
        sort_keys: 是否排序键
        default: 默认序列化函数
        
    Returns:
        JSON字符串，失败时返回空字符串
    """
    try:
        return json.dumps(
            obj,
            ensure_ascii=ensure_ascii,
            indent=indent,
            sort_keys=sort_keys,
            default=default or _default_json_serializer
        )
    except (TypeError, ValueError) as e:
        logger.error(f"JSON序列化失败: {e}")
        return ""


def _default_json_serializer(obj: Any) -> Any:
    """默认的JSON序列化处理器"""
    if hasattr(obj, '__dict__'):
        return obj.__dict__
    elif hasattr(obj, 'isoformat'):  # datetime对象
        return obj.isoformat()
    elif hasattr(obj, '__str__'):
        return str(obj)
    else:
        raise TypeError(f"对象 {type(obj)} 不支持JSON序列化")


def repair_json_output(content: str) -> str:
    """
    修复和规范化JSON输出
    
    Args:
        content: 可能包含JSON的字符串内容
        
    Returns:
        修复后的JSON字符串，如果不是JSON则返回原内容
    """
    if not content or not isinstance(content, str):
        return content
    
    content = content.strip()
    if not content:
        return content
    
    # 如果有 json_repair 库，优先使用
    if HAS_JSON_REPAIR:
        return _repair_with_json_repair(content)
    else:
        return _basic_json_repair(content)


def _repair_with_json_repair(content: str) -> str:
    """使用 json_repair 库修复JSON"""
    try:
        repaired_content = json_repair.loads(content)
        if not isinstance(repaired_content, (dict, list)):
            logger.warning("修复后的内容不是有效的JSON对象或数组")
            return content
        return json.dumps(repaired_content, ensure_ascii=False)
    except Exception as e:
        logger.warning(f"json_repair 修复失败: {e}")
        return _basic_json_repair(content)


def _basic_json_repair(content: str) -> str:
    """基础JSON修复功能"""
    try:
        # 尝试直接解析
        parsed = json.loads(content)
        return json.dumps(parsed, ensure_ascii=False)
    except json.JSONDecodeError:
        pass
    
    # 基础修复策略
    repaired = content
    
    # 修复常见问题
    repaired = _fix_common_json_issues(repaired)
    
    try:
        # 再次尝试解析
        parsed = json.loads(repaired)
        return json.dumps(parsed, ensure_ascii=False)
    except json.JSONDecodeError as e:
        logger.warning(f"基础JSON修复失败: {e}")
        return content


def _fix_common_json_issues(content: str) -> str:
    """修复常见的JSON格式问题"""
    # 移除可能的markdown代码块标记
    content = re.sub(r'^```json\s*\n?', '', content, flags=re.MULTILINE)
    content = re.sub(r'\n?```\s*$', '', content, flags=re.MULTILINE)
    
    # 移除可能的注释
    content = re.sub(r'//.*$', '', content, flags=re.MULTILINE)
    content = re.sub(r'/\*.*?\*/', '', content, flags=re.DOTALL)
    
    # 修复单引号为双引号
    content = re.sub(r"'([^']*)':", r'"\1":', content)
    content = re.sub(r":\s*'([^']*)'", r': "\1"', content)
    
    # 修复尾随逗号
    content = re.sub(r',(\s*[}\]])', r'\1', content)
    
    # 修复缺失的引号
    content = re.sub(r'(\w+):', r'"\1":', content)
    
    return content


def extract_json_from_text(text: str) -> List[Dict[str, Any]]:
    """
    从文本中提取所有JSON对象
    
    Args:
        text: 包含JSON的文本
        
    Returns:
        提取到的JSON对象列表
    """
    json_objects = []
    
    # 寻找可能的JSON模式
    patterns = [
        r'\{[^{}]*\}',  # 简单对象
        r'\{.*?\}',     # 复杂对象
        r'\[.*?\]',     # 数组
    ]
    
    for pattern in patterns:
        matches = re.finditer(pattern, text, re.DOTALL)
        for match in matches:
            json_str = match.group()
            parsed = safe_json_loads(json_str, repair=True)
            if parsed is not None and isinstance(parsed, (dict, list)):
                json_objects.append(parsed)
    
    return json_objects


def validate_json_schema(data: Any, schema: Dict[str, Any]) -> bool:
    """
    简单的JSON模式验证
    
    Args:
        data: 要验证的数据
        schema: 简单的模式定义
        
    Returns:
        是否符合模式
    """
    try:
        return _validate_schema_recursive(data, schema)
    except Exception as e:
        logger.warning(f"模式验证失败: {e}")
        return False


def _validate_schema_recursive(data: Any, schema: Dict[str, Any]) -> bool:
    """递归验证模式"""
    if 'type' in schema:
        expected_type = schema['type']
        if expected_type == 'object' and not isinstance(data, dict):
            return False
        elif expected_type == 'array' and not isinstance(data, list):
            return False
        elif expected_type == 'string' and not isinstance(data, str):
            return False
        elif expected_type == 'number' and not isinstance(data, (int, float)):
            return False
        elif expected_type == 'boolean' and not isinstance(data, bool):
            return False
    
    if 'properties' in schema and isinstance(data, dict):
        for key, prop_schema in schema['properties'].items():
            if key in data:
                if not _validate_schema_recursive(data[key], prop_schema):
                    return False
            elif schema.get('required', []) and key in schema['required']:
                return False
    
    if 'items' in schema and isinstance(data, list):
        for item in data:
            if not _validate_schema_recursive(item, schema['items']):
                return False
    
    return True


def merge_json_objects(*objects: Dict[str, Any]) -> Dict[str, Any]:
    """
    合并多个JSON对象
    
    Args:
        *objects: 要合并的JSON对象
        
    Returns:
        合并后的JSON对象
    """
    result = {}
    
    for obj in objects:
        if not isinstance(obj, dict):
            continue
        
        for key, value in obj.items():
            if key in result and isinstance(result[key], dict) and isinstance(value, dict):
                result[key] = merge_json_objects(result[key], value)
            else:
                result[key] = value
    
    return result


def flatten_json(data: Dict[str, Any], separator: str = '.') -> Dict[str, Any]:
    """
    扁平化JSON对象
    
    Args:
        data: 要扁平化的JSON对象
        separator: 键的分隔符
        
    Returns:
        扁平化后的JSON对象
    """
    def _flatten_recursive(obj: Any, parent_key: str = '') -> Dict[str, Any]:
        items = []
        
        if isinstance(obj, dict):
            for key, value in obj.items():
                new_key = f"{parent_key}{separator}{key}" if parent_key else key
                items.extend(_flatten_recursive(value, new_key).items())
        elif isinstance(obj, list):
            for i, value in enumerate(obj):
                new_key = f"{parent_key}{separator}{i}" if parent_key else str(i)
                items.extend(_flatten_recursive(value, new_key).items())
        else:
            return {parent_key: obj}
        
        return dict(items)
    
    return _flatten_recursive(data)


def unflatten_json(data: Dict[str, Any], separator: str = '.') -> Dict[str, Any]:
    """
    反扁平化JSON对象
    
    Args:
        data: 扁平化的JSON对象
        separator: 键的分隔符
        
    Returns:
        反扁平化后的JSON对象
    """
    result = {}
    
    for key, value in data.items():
        keys = key.split(separator)
        current = result
        
        for i, k in enumerate(keys[:-1]):
            if k.isdigit():
                k = int(k)
                if not isinstance(current, list):
                    current = []
                while len(current) <= k:
                    current.append({})
                current = current[k]
            else:
                if k not in current:
                    # 判断下一个键是否为数字，决定创建字典还是列表
                    next_key = keys[i + 1]
                    current[k] = [] if next_key.isdigit() else {}
                current = current[k]
        
        final_key = keys[-1]
        if final_key.isdigit():
            final_key = int(final_key)
            if not isinstance(current, list):
                current = []
            while len(current) <= final_key:
                current.append(None)
            current[final_key] = value
        else:
            current[final_key] = value
    
    return result