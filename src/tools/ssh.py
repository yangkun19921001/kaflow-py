"""
KaFlow-Py SSH 远程执行工具

提供 SSH 远程命令执行功能，支持密码和公私钥两种认证方式

Author: DevYK
微信公众号: DevYK
Email: yang1001yk@gmail.com
Github: https://github.com/yangkun19921001
"""

import os
import socket
import time
from datetime import datetime
from pathlib import Path
from typing import Optional, Literal
from langchain_core.tools import tool

try:
    import paramiko
except ImportError:
    raise ImportError(
        "请安装 paramiko 库以使用 SSH 功能: pip install paramiko"
    )


@tool
def ssh_remote_exec(
    host: str,
    command: str,
    username: str = "root",
    password: Optional[str] = None,
    port: int = 22,
    key_filename: Optional[str] = None,
    key_passphrase: Optional[str] = None,
    timeout: int = 30,
    max_retries: int = 3
) -> str:
    """
    通过 SSH 连接远程服务器并执行命令
    
    Args:
        host: 远程主机 IP 地址或域名，例如：192.168.1.100, example.com
        command: 要执行的命令，例如：ls -la, df -h, ps aux
        username: SSH 用户名，默认为 root
        password: SSH 密码（可选）。如果不提供，将使用私钥认证
        port: SSH 端口号，默认为 22
        key_filename: SSH 私钥文件路径（可选）。如果不提供密码，将使用 ~/.ssh/id_rsa
        key_passphrase: 私钥密码短语（可选），用于加密的私钥
        timeout: 连接和命令执行超时时间（秒），默认 30 秒
        max_retries: 最大重试次数，默认 3 次
        
    Returns:
        命令执行结果字符串，包含输出和错误信息
        
    Examples:
        # 使用密码登录
        ssh_remote_exec("192.168.1.100", "ls -la /tmp", password="your_password")
        
        # 使用默认私钥登录
        ssh_remote_exec("192.168.1.100", "df -h")
        
        # 使用指定私钥登录
        ssh_remote_exec("192.168.1.100", "whoami", key_filename="~/.ssh/my_key")
    """
    
    # 记录开始时间
    start_time = datetime.now()
    
    # 创建 SSH 客户端
    ssh = paramiko.SSHClient()
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    
    # 确定认证方式
    auth_method = "密码" if password else "公钥"
    
    # 处理私钥路径
    if not password:
        if key_filename:
            # 展开用户目录路径
            key_path = Path(key_filename).expanduser()
            if not key_path.exists():
                return f"❌ 错误：私钥文件不存在：{key_path}"
        else:
            # 使用默认私钥
            default_keys = [
                Path.home() / ".ssh" / "id_rsa",
                Path.home() / ".ssh" / "id_ed25519",
                Path.home() / ".ssh" / "id_ecdsa"
            ]
            key_path = None
            for key in default_keys:
                if key.exists():
                    key_path = key
                    break
            
            if not key_path:
                return f"❌ 错误：未找到默认私钥文件（{', '.join(str(k) for k in default_keys)}），且未提供密码"
        
        key_filename = str(key_path)
    
    # 重试逻辑
    last_error = None
    retry_delay = 2  # 重试间隔（秒）
    
    for retry in range(max_retries):
        try:
            if retry > 0:
                print(f"正在重试连接... (第 {retry + 1}/{max_retries} 次)")
                time.sleep(retry_delay)
            
            # 构建连接参数
            connect_kwargs = {
                "hostname": host,
                "port": port,
                "username": username,
                "timeout": timeout,
                "look_for_keys": False,  # 不自动搜索密钥
                "allow_agent": False     # 不使用 SSH agent
            }
            
            # 添加认证信息
            if password:
                connect_kwargs["password"] = password
            else:
                connect_kwargs["key_filename"] = key_filename
                if key_passphrase:
                    connect_kwargs["passphrase"] = key_passphrase
            
            # 连接到服务器
            ssh.connect(**connect_kwargs)
            
            # 执行命令
            stdin, stdout, stderr = ssh.exec_command(command, timeout=timeout)
            
            # 获取输出
            output = stdout.read().decode('utf-8', errors='ignore').strip()
            error = stderr.read().decode('utf-8', errors='ignore').strip()
            
            # 获取退出状态码
            exit_status = stdout.channel.recv_exit_status()
            
            # 关闭连接
            ssh.close()
            
            # 记录结束时间
            end_time = datetime.now()
            duration = (end_time - start_time).total_seconds()
            
            # 构建结果
            result_lines = []
            
            # 状态头
            if exit_status == 0:
                result_lines.append("✅ SSH 命令执行成功")
            else:
                result_lines.append(f"❌ SSH 命令执行失败 (退出码: {exit_status})")
            
            # 连接信息
            result_lines.extend([
                "",
                "=== 连接信息 ===",
                f"主机: {username}@{host}:{port}",
                f"认证方式: {auth_method}",
                f"执行时间: {duration:.2f} 秒",
                f"退出状态: {exit_status}"
            ])
            
            # 命令和输出
            result_lines.extend([
                "",
                "=== 执行命令 ===",
                command
            ])
            
            if output:
                result_lines.extend([
                    "",
                    "=== 标准输出 ===",
                    output
                ])
            
            if error:
                result_lines.extend([
                    "",
                    "=== 错误输出 ===",
                    error
                ])
            
            return "\n".join(result_lines)
            
        except socket.timeout:
            last_error = f"连接超时（{timeout}秒），请检查主机地址和网络连接"
            
        except socket.gaierror:
            last_error = f"无法解析主机名 '{host}'，请检查主机地址"
            
        except paramiko.AuthenticationException:
            last_error = f"认证失败，请检查{auth_method}是否正确"
            
        except paramiko.SSHException as e:
            last_error = f"SSH 连接错误：{str(e)}"
            
        except FileNotFoundError as e:
            last_error = f"文件未找到：{str(e)}"
            
        except Exception as e:
            last_error = f"执行出错：{str(e)}"
            
        finally:
            try:
                ssh.close()
            except:
                pass
    
    # 所有重试都失败
    end_time = datetime.now()
    duration = (end_time - start_time).total_seconds()
    
    result_lines = [
        f"❌ SSH 连接失败（已重试 {max_retries} 次）",
        "",
        "=== 连接信息 ===",
        f"主机: {username}@{host}:{port}",
        f"认证方式: {auth_method}",
        f"总耗时: {duration:.2f} 秒",
        "",
        "=== 错误详情 ===",
        last_error,
        "",
        "=== 尝试执行的命令 ===",
        command,
        "",
        "=== 故障排查建议 ===",
    ]
    
    # 添加故障排查建议
    if "timeout" in last_error.lower():
        result_lines.extend([
            "1. 检查主机 IP 地址是否正确",
            "2. 检查网络连接是否正常（ping 测试）",
            "3. 检查防火墙是否允许 SSH 连接",
            "4. 检查 SSH 服务是否在运行"
        ])
    elif "authentication" in last_error.lower():
        if password:
            result_lines.extend([
                "1. 检查用户名和密码是否正确",
                "2. 检查用户账户是否被锁定",
                "3. 检查 SSH 服务是否允许密码认证（PasswordAuthentication yes）"
            ])
        else:
            result_lines.extend([
                "1. 检查私钥文件路径是否正确",
                "2. 检查私钥文件权限（应为 600）",
                "3. 检查公钥是否已添加到远程服务器的 ~/.ssh/authorized_keys",
                "4. 如果私钥有密码，请提供 key_passphrase 参数"
            ])
    elif "gaierror" in last_error.lower():
        result_lines.extend([
            "1. 检查主机名是否正确",
            "2. 检查 DNS 解析是否正常",
            "3. 尝试使用 IP 地址代替主机名"
        ])
    else:
        result_lines.extend([
            "1. 检查所有连接参数是否正确",
            "2. 检查远程服务器状态",
            "3. 查看详细错误信息排查问题"
        ])
    
    return "\n".join(result_lines)


@tool
def ssh_batch_exec(
    hosts: str,
    command: str,
    username: str = "root",
    password: Optional[str] = None,
    port: int = 22,
    key_filename: Optional[str] = None,
    timeout: int = 30
) -> str:
    """
    批量在多台服务器上执行相同的命令
    
    Args:
        hosts: 主机列表，用逗号分隔，例如：192.168.1.100,192.168.1.101,example.com
        command: 要执行的命令
        username: SSH 用户名，默认为 root
        password: SSH 密码（可选）
        port: SSH 端口号，默认为 22
        key_filename: SSH 私钥文件路径（可选）
        timeout: 连接和命令执行超时时间（秒），默认 30 秒
        
    Returns:
        所有主机的执行结果汇总
        
    Examples:
        # 批量检查磁盘空间
        ssh_batch_exec("192.168.1.100,192.168.1.101", "df -h")
    """
    
    # 解析主机列表
    host_list = [h.strip() for h in hosts.split(',') if h.strip()]
    
    if not host_list:
        return "❌ 错误：未提供有效的主机列表"
    
    # 记录开始时间
    start_time = datetime.now()
    
    # 执行结果
    results = []
    success_count = 0
    failed_count = 0
    
    results.append(f"=== 批量执行 SSH 命令 ===")
    results.append(f"主机数量: {len(host_list)}")
    results.append(f"执行命令: {command}")
    results.append("")
    
    for idx, host in enumerate(host_list, 1):
        results.append(f"{'='*60}")
        results.append(f"主机 {idx}/{len(host_list)}: {host}")
        results.append(f"{'='*60}")
        
        # 执行命令（重试次数设为1，因为批量执行时不需要过多重试）
        result = ssh_remote_exec(
            host=host,
            command=command,
            username=username,
            password=password,
            port=port,
            key_filename=key_filename,
            timeout=timeout,
            max_retries=1
        )
        
        results.append(result)
        results.append("")
        
        # 统计成功/失败
        if "✅" in result:
            success_count += 1
        else:
            failed_count += 1
    
    # 记录结束时间
    end_time = datetime.now()
    duration = (end_time - start_time).total_seconds()
    
    # 添加汇总
    results.append(f"{'='*60}")
    results.append("=== 执行汇总 ===")
    results.append(f"总主机数: {len(host_list)}")
    results.append(f"成功: {success_count}")
    results.append(f"失败: {failed_count}")
    results.append(f"总耗时: {duration:.2f} 秒")
    results.append(f"{'='*60}")
    
    return "\n".join(results)


# 导出所有工具
__all__ = ["ssh_remote_exec", "ssh_batch_exec"]

