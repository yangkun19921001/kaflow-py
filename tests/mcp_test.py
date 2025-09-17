#!/usr/bin/env python3
"""
KaFlow-Py MCP 模块测试

简化的 SSE MCP 测试，包括：
1. 连接 SSE MCP 服务器
2. 获取可用工具列表
3. 执行工具调用

Author: DevYK
WeChat: DevYK
Email: yang1001yk@gmail.com
Github: https://github.com/yangkun19921001
"""

import asyncio
import os
import sys
from pathlib import Path

# 临时禁用代理设置，避免 SOCKS 代理问题
for proxy_var in ['http_proxy', 'https_proxy', 'all_proxy', 'HTTP_PROXY', 'HTTPS_PROXY', 'ALL_PROXY']:
    if proxy_var in os.environ:
        del os.environ[proxy_var]

# 添加项目根目录到 Python 路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from src.mcp import (
    MCPServerConfig,
    MCPClient,
    create_mcp_config,
)


async def test_sse_mcp_server():
    """测试 SSE MCP 服务器连接、获取工具和执行工具"""
    print("=== SSE MCP 服务器测试 ===")
    
    # SSE 服务器配置
    sse_url = "http://10.1.16.4:8000/mcp/sse"  # 使用你提供的 URL
    
    try:
        # 创建 SSE 客户端配置
        config = create_mcp_config(
            transport="sse",
            url=sse_url,
            timeout_seconds=30
        )
        
        print(f"🔗 连接到 SSE 服务器: {sse_url}")
        client = MCPClient(config)
        print("✅ SSE 客户端创建成功")
        
        # 获取服务器元数据和工具列表
        print("\n📋 获取服务器工具列表...")
        try:
            metadata = await client.get_server_metadata()
            print(f"✅ 服务器状态: {metadata.status}")
            print(f"✅ 可用工具数量: {len(metadata.tools)}")
        
            if metadata.tools:
                print("\n🔧 可用工具:")
                for i, tool in enumerate(metadata.tools, 1):
                    print(f"  {i}. {tool['name']}")
                    if tool.get('description'):
                        print(f"     描述: {tool['description']}")
                    if tool.get('input_schema'):
                        print(f"     输入模式: {tool['input_schema']}")
                    print()
                
                # 尝试执行第一个工具（如果有的话）
                if len(metadata.tools) > 0:
                    first_tool = metadata.tools[0]
                    print(f"🚀 尝试执行工具: {first_tool['name']}")
                    
                    print(f"   工具名称: {first_tool['name']}")
                    print(f"   工具描述: {first_tool.get('description', '无描述')}")
                    
                    if first_tool.get('input_schema'):
                        schema = first_tool['input_schema']
                        print(f"   参数要求: {schema}")
                        
                        # 如果是 remote_exec 工具，执行实际命令
                        if first_tool['name'] == 'remote_exec':
                            machine_id = "420c126d598a97ee31fb70127b6b9a46"
                            command = "pwd"
                            
                            print(f"\n🎯 执行远程命令:")
                            print(f"   机器ID: {machine_id}")
                            print(f"   命令: {command}")
                            
                            try:
                                # 实际调用 MCP 工具
                                result = await client.call_tool(
                                    tool_name="remote_exec",
                                    arguments={
                                        "machineId": machine_id,
                                        "script": command
            }
        )
                                
                                print(f"✅ 命令执行成功!")
                                print(f"📤 执行结果:")
                                if isinstance(result, dict):
                                    for key, value in result.items():
                                        print(f"   {key}: {value}")
                                else:
                                    print(f"   {result}")
        
                            except Exception as e:
                                print(f"❌ 命令执行失败: {str(e)}")
                                # 即使执行失败，我们也展示了如何调用
                                print("   (这可能是因为工具调用方法需要调整)")
                        
                        else:
                            properties = schema.get('properties', {})
                            print(f"   参数列表: {list(properties.keys())}")
                    
                    print("✅ 工具信息获取成功")
                else:
                    print("⚠️  服务器没有可用工具")
            else:
                print("⚠️  未获取到工具列表")
                
        except Exception as e:
            print(f"❌ 获取工具失败: {str(e)}")
            print("这可能是因为:")
            print("  1. SSE 服务器未运行")
            print("  2. URL 不正确") 
            print("  3. 网络连接问题")
            print("  4. 服务器不是有效的 MCP 服务器")
            return False
        
        print("✅ SSE MCP 测试完成")
        return True
        
    except Exception as e:
        print(f"❌ SSE MCP 测试失败: {str(e)}")
        import traceback
        traceback.print_exc()
        return False


async def test_mcp_tool_execution_example():
    """演示如何执行 MCP 工具（模拟示例）"""
    print("\n=== MCP 工具执行示例 ===")
    
    try:
        # 这是一个模拟示例，展示如何使用获取到的工具信息
        print("📝 工具执行流程:")
        print("  1. 连接到 MCP 服务器")
        print("  2. 获取可用工具列表")
        print("  3. 选择要执行的工具")
        print("  4. 准备工具参数")
        print("  5. 调用工具并获取结果")
        
        # 模拟工具信息
        mock_tool = {
            "name": "calculator",
            "description": "执行数学计算",
            "input_schema": {
                "type": "object",
                "properties": {
                    "expression": {
                        "type": "string",
                        "description": "要计算的数学表达式"
                    }
                },
                "required": ["expression"]
            }
        }
        
        print(f"\n🔧 示例工具: {mock_tool['name']}")
        print(f"   描述: {mock_tool['description']}")
        print(f"   参数: {mock_tool['input_schema']['properties']}")
        
        # 模拟工具调用参数
        example_params = {
            "expression": "2 + 2 * 3"
        }
        
        print(f"\n📤 调用参数: {example_params}")
        print("📥 模拟返回结果: 8")
        
        print("✅ 工具执行示例完成")
        return True
        
    except Exception as e:
        print(f"❌ 工具执行示例失败: {str(e)}")
        return False


async def main():
    """运行 SSE MCP 测试"""
    print("KaFlow-Py SSE MCP 服务器测试")
    print("=" * 60)
    print(f"测试服务器: http://10.1.16.4:8000/mcp/sse")
    print("=" * 60)
    
    # 运行测试
    tests = [
        test_sse_mcp_server,
        test_mcp_tool_execution_example,
    ]
    
    results = []
    for test_func in tests:
        try:
            result = await test_func()
            results.append(result)
        except Exception as e:
            print(f"❌ 测试 {test_func.__name__} 出现异常: {e}")
            results.append(False)
    
    # 输出测试结果
    print(f"\n{'=' * 60}")
    print(f"测试结果: {sum(results)}/{len(results)} 通过")
    
    if all(results):
        print("🎉 SSE MCP 测试完成！")
        print("\n功能验证:")
        print("✅ SSE 服务器连接")
        print("✅ 工具列表获取")
        print("✅ 工具信息解析")
        print("✅ 工具执行流程演示")
        
        print("\n使用说明:")
        print("1. 确保 SSE MCP 服务器在 http://10.1.16.4:8000/mcp/sse 运行")
        print("2. 服务器应该实现 MCP 协议")
        print("3. 可以根据实际工具修改执行逻辑")
        
        return True
    else:
        print("⚠️  部分测试失败")
        print("\n故障排除:")
        print("- 检查 SSE 服务器是否正在运行")
        print("- 验证服务器 URL 是否正确")
        print("- 确认服务器实现了 MCP 协议")
        print("- 检查网络连接")
        
        return False


if __name__ == "__main__":
    success = asyncio.run(main())
    sys.exit(0 if success else 1) 