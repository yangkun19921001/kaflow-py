"""
KaFlow-Py 基础工具函数

实现文件操作、系统信息查询、数学计算、时间查询等基础工具

Author: DevYK
WeChat: DevYK
Email: yang1001yk@gmail.com
Github: https://github.com/yangkun19921001
"""

import os
import platform
import psutil
import math
import json
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, Optional
from langchain_core.tools import tool


@tool
def file_reader(file_path: str) -> str:
    """
    读取指定文件的内容
    
    Args:
        file_path: 要读取的文件路径
        
    Returns:
        文件内容字符串
    """
    try:
        path = Path(file_path)
        if not path.exists():
            return f"错误：文件 '{file_path}' 不存在"
        
        if not path.is_file():
            return f"错误：'{file_path}' 不是一个文件"
            
        # 检查文件大小，避免读取过大的文件
        if path.stat().st_size > 10 * 1024 * 1024:  # 10MB
            return f"错误：文件 '{file_path}' 太大 (>10MB)，无法读取"
            
        with open(path, 'r', encoding='utf-8') as f:
            content = f.read()
            
        return f"文件 '{file_path}' 内容：\n{content}"
        
    except UnicodeDecodeError:
        try:
            with open(path, 'r', encoding='gbk') as f:
                content = f.read()
            return f"文件 '{file_path}' 内容（GBK编码）：\n{content}"
        except Exception as e:
            return f"错误：无法读取文件 '{file_path}'，编码问题：{str(e)}"
    except Exception as e:
        return f"错误：读取文件 '{file_path}' 失败：{str(e)}"


@tool
def file_writer(file_path: str, content: str, mode: str = "write") -> str:
    """
    将内容写入指定文件
    
    Args:
        file_path: 要写入的文件路径
        content: 要写入的内容
        mode: 写入模式，"write"(覆盖) 或 "append"(追加)
        
    Returns:
        操作结果描述
    """
    try:
        path = Path(file_path)
        
        # 创建目录（如果不存在）
        path.parent.mkdir(parents=True, exist_ok=True)
        
        # 确定写入模式
        write_mode = "w" if mode == "write" else "a"
        
        with open(path, write_mode, encoding='utf-8') as f:
            f.write(content)
            
        action = "写入" if mode == "write" else "追加"
        return f"成功{action}内容到文件 '{file_path}'，共 {len(content)} 个字符"
        
    except Exception as e:
        return f"错误：写入文件 '{file_path}' 失败：{str(e)}"


@tool
def system_info(info_type: str = "all") -> str:
    """
    获取系统信息
    
    Args:
        info_type: 信息类型 - platform, cpu, memory, disk, network, all
        
    Returns:
        系统信息字符串
    """
    try:
        result = {}
        
        if info_type in ["platform", "all"]:
            result["platform"] = {
                "system": platform.system(),
                "release": platform.release(),
                "version": platform.version(),
                "machine": platform.machine(),
                "processor": platform.processor(),
                "python_version": platform.python_version()
            }
            
        if info_type in ["cpu", "all"]:
            result["cpu"] = {
                "physical_cores": psutil.cpu_count(logical=False),
                "logical_cores": psutil.cpu_count(logical=True),
                "cpu_percent": f"{psutil.cpu_percent(interval=1):.1f}%",
                "frequency": f"{psutil.cpu_freq().current:.0f} MHz" if psutil.cpu_freq() else "N/A"
            }
            
        if info_type in ["memory", "all"]:
            memory = psutil.virtual_memory()
            result["memory"] = {
                "total": f"{memory.total / (1024**3):.2f} GB",
                "available": f"{memory.available / (1024**3):.2f} GB",
                "used": f"{memory.used / (1024**3):.2f} GB",
                "percentage": f"{memory.percent:.1f}%"
            }
            
        if info_type in ["disk", "all"]:
            disk = psutil.disk_usage('/')
            result["disk"] = {
                "total": f"{disk.total / (1024**3):.2f} GB",
                "used": f"{disk.used / (1024**3):.2f} GB", 
                "free": f"{disk.free / (1024**3):.2f} GB",
                "percentage": f"{(disk.used / disk.total) * 100:.1f}%"
            }
            
        if info_type in ["network", "all"]:
            network = psutil.net_io_counters()
            result["network"] = {
                "bytes_sent": f"{network.bytes_sent / (1024**2):.2f} MB",
                "bytes_received": f"{network.bytes_recv / (1024**2):.2f} MB",
                "packets_sent": network.packets_sent,
                "packets_received": network.packets_recv
            }
        
        # 格式化输出
        output_lines = []
        for category, data in result.items():
            output_lines.append(f"=== {category.upper()} ===")
            for key, value in data.items():
                output_lines.append(f"{key}: {value}")
            output_lines.append("")
            
        return "\n".join(output_lines)
        
    except Exception as e:
        return f"错误：获取系统信息失败：{str(e)}"


@tool
def calculator(expression: str) -> str:
    """
    执行数学计算
    
    Args:
        expression: 数学表达式
        
    Returns:
        计算结果
    """
    try:
        # 安全的数学函数和常量
        safe_dict = {
            "__builtins__": {},
            "abs": abs, "round": round, "min": min, "max": max,
            "sum": sum, "pow": pow, "divmod": divmod,
            "math": math, "pi": math.pi, "e": math.e,
            "sin": math.sin, "cos": math.cos, "tan": math.tan,
            "asin": math.asin, "acos": math.acos, "atan": math.atan,
            "sinh": math.sinh, "cosh": math.cosh, "tanh": math.tanh,
            "log": math.log, "log10": math.log10, "log2": math.log2,
            "sqrt": math.sqrt, "ceil": math.ceil, "floor": math.floor,
            "exp": math.exp, "factorial": math.factorial,
            "degrees": math.degrees, "radians": math.radians
        }
        
        # 执行计算
        result = eval(expression, safe_dict)
        
        # 格式化结果
        if isinstance(result, float):
            if result.is_integer():
                result = int(result)
            else:
                result = round(result, 10)  # 限制小数位数
                
        return f"计算结果：{expression} = {result}"
        
    except ZeroDivisionError:
        return f"错误：除零错误在表达式 '{expression}'"
    except ValueError as e:
        return f"错误：数值错误在表达式 '{expression}'：{str(e)}"
    except SyntaxError:
        return f"错误：语法错误在表达式 '{expression}'"
    except Exception as e:
        return f"错误：计算表达式 '{expression}' 失败：{str(e)}"


@tool
def current_time(format: str = "datetime", timezone: str = "local") -> str:
    """
    获取当前时间信息
    
    Args:
        format: 时间格式 - datetime, timestamp, iso
        timezone: 时区，如 UTC, Asia/Shanghai, local
        
    Returns:
        时间信息字符串
    """
    try:
        import pytz
        
        # 获取当前时间
        now = datetime.now()
        
        # 处理时区
        if timezone != "local":
            if timezone == "UTC":
                tz = pytz.UTC
            else:
                tz = pytz.timezone(timezone)
            now = now.replace(tzinfo=pytz.timezone('UTC')).astimezone(tz)
        
        # 格式化时间
        if format == "timestamp":
            result = str(int(now.timestamp()))
        elif format == "iso":
            result = now.isoformat()
        else:  # datetime
            result = now.strftime("%Y-%m-%d %H:%M:%S")
            if timezone != "local":
                result += f" ({timezone})"
                
        return f"当前时间：{result}"
        
    except pytz.exceptions.UnknownTimeZoneError:
        return f"错误：未知时区 '{timezone}'"
    except Exception as e:
        # 如果 pytz 不可用，使用基础功能
        try:
            now = datetime.now()
            if format == "timestamp":
                result = str(int(now.timestamp()))
            elif format == "iso":
                result = now.isoformat()
            else:
                result = now.strftime("%Y-%m-%d %H:%M:%S")
            return f"当前时间：{result}"
        except Exception as e2:
            return f"错误：获取时间失败：{str(e2)}" 