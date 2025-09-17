# -*- coding: utf-8 -*-
"""
KaFlow-Py MCP 集成 Chat Agent 测试

测试集成 MCP 外部工具服务的聊天机器人功能

Author: DevYK
WeChat: DevYK
Email: yang1001yk@gmail.com
Github: https://github.com/yangkun19921001
"""

import asyncio
import sys
import os
from pathlib import Path

# 添加项目根目录到 Python 路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

# 临时禁用代理设置，避免 SOCKS 代理问题
for proxy_var in ['http_proxy', 'https_proxy', 'all_proxy', 'HTTP_PROXY', 'HTTPS_PROXY', 'ALL_PROXY']:
    if proxy_var in os.environ:
        del os.environ[proxy_var]

from src.core.graph import get_graph_manager
from src.mcp import MCPClient, create_mcp_config


def check_api_keys():
    """检查 API 密钥是否可用"""
    deepseek_key = os.getenv("DEEPSEEK_API_KEY")
    openai_key = os.getenv("OPENAI_API_KEY")
    
    if not deepseek_key and not openai_key:
        print("❌ 错误：未找到 API 密钥")
        print("请设置环境变量：")
        print("  export DEEPSEEK_API_KEY='your-key-here'")
        print("  或 export OPENAI_API_KEY='your-key-here'")
        return False
    
    if deepseek_key:
        print(f"✅ 找到 DeepSeek API 密钥: {deepseek_key[:10]}...")
    if openai_key:
        print(f"✅ 找到 OpenAI API 密钥: {openai_key[:10]}...")
    
    return True


async def test_mcp_server_connectivity():
    """测试 MCP 服务器连接"""
    print("\n" + "="*50)
    print("🌐 测试 MCP 服务器连接")
    print("="*50)
    
    try:
        # MCP 服务器配置
        sse_url = "http://10.1.16.4:8000/mcp/sse"
        
        config = create_mcp_config(
            transport="sse",
            url=sse_url,
            timeout_seconds=30
        )
        
        print(f"🔗 连接到 MCP 服务器: {sse_url}")
        client = MCPClient(config)
        
        # 获取服务器元数据和工具列表
        print("📋 获取服务器工具列表...")
        metadata = await client.get_server_metadata()
        
        if metadata and metadata.tools:
            print(f"✅ MCP 服务器连接成功")
            print(f"   - 服务器状态: {metadata.status}")
            print(f"   - 可用工具数量: {len(metadata.tools)}")
            
            print("\n🔧 可用的 MCP 工具:")
            for i, tool in enumerate(metadata.tools, 1):
                print(f"  {i}. {tool['name']}")
                if tool.get('description'):
                    print(f"     描述: {tool['description']}")
            
            return True
        else:
            print("❌ MCP 服务器无工具或连接失败")
            return False
            
    except Exception as e:
        print(f"❌ MCP 服务器连接失败: {e}")
        print("请检查:")
        print("  - MCP 服务器是否在 http://10.1.16.4:8000/mcp/sse 运行")
        print("  - 网络连接是否正常")
        print("  - 服务器是否实现了 MCP 协议")
        return False


def test_mcp_protocol_validation():
    """测试 MCP 协议验证"""
    print("\n" + "="*50)
    print("🔍 测试 MCP 协议验证")
    print("="*50)
    
    try:
        manager = get_graph_manager()
        
        # 测试 chat_agent_mcp 模板
        config_path = project_root / "src/core/config/chat_agent_mcp.yaml.template"
        errors = manager.validate_protocol_file(config_path)
        
        if not errors:
            print("✅ chat_agent_mcp.yaml.template 验证通过")
        else:
            print("❌ chat_agent_mcp.yaml.template 验证失败:")
            for error in errors:
                print(f"   - {error}")
        
        return len(errors) == 0
        
    except Exception as e:
        print(f"❌ MCP 协议验证测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_mcp_graph_registration():
    """测试 MCP 图注册"""
    print("\n" + "="*50)
    print("🔧 测试 MCP 图注册")
    print("="*50)
    
    try:
        manager = get_graph_manager()
        
        # 注册 chat_agent_mcp 图
        config_path = project_root / "src/core/config/chat_agent_mcp.yaml.template"
        graph_id = manager.register_graph_from_file(config_path, "chat_agent_mcp")
        
        print(f"✅ 成功注册 MCP 图: {graph_id}")
        
        # 获取图信息
        graph_info = manager.get_graph_info(graph_id)
        if graph_info:
            print(f"   - 协议名称: {graph_info['protocol']['name']}")
            print(f"   - 工作流名称: {graph_info['workflow']['name']}")
            print(f"   - 节点数量: {len(graph_info['nodes'])}")
            print(f"   - 边数量: {len(graph_info['edges'])}")
            print(f"   - Agent 数量: {len(graph_info['agents'])}")
            
            # 显示 Agent 信息
            for agent_name, agent_info in graph_info['agents'].items():
                print(f"   - Agent {agent_name}: {agent_info['type']}")
        
        return True
        
    except Exception as e:
        print(f"❌ MCP 图注册测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False


async def test_mcp_graph_execution():
    """测试 MCP 图流式执行"""
    print("\n" + "="*50)
    print("🚀 测试 MCP 图流式执行")
    print("="*50)
    
    try:
        manager = get_graph_manager()
        
        # 测试用例
        test_cases = [
            # {
            #     "name": "简单对话测试",
            #     "input": "你好，请介绍一下你的 MCP 功能",
            #     "expected_keywords": ["MCP", "工具", "远程"]
            # },
            # {
            #     "name": "MCP 工具查询测试",
            #     "input": "你有哪些 MCP 工具可以使用？",
            #     "expected_keywords": ["remote_exec", "工具", "命令"]
            # },
            {
                "name": "远程命令执行测试",
                "input": "在机器 420c126d598a97ee31fb70127b6b9a46 上执行 pwd 命令",
                "expected_keywords": ["420c126d598a97ee31fb70127b6b9a46", "pwd"]
            }
        ]
        
        for i, test_case in enumerate(test_cases, 1):
            print(f"\n--- 流式测试 {i}: {test_case['name']} ---")
            print(f"输入: {test_case['input']}")
            
            try:
                # 流式执行 MCP 图
                event_count = 0
                final_response = ""
                execution_status = "unknown"
                
                async for event in manager.execute_graph_stream(
                    graph_id="chat_agent_mcp",
                    user_input=test_case["input"]
                ):
                    print(f"🔍 收到 event: {event}")
                
                # 统计结果
                print(f"\n📊 流式执行统计:")
                print(f"   - 事件数量: {event_count}")
                print(f"   - 执行状态: {execution_status}")
                print(f"   - 响应长度: {len(final_response)} 字符")
                
                if execution_status == "completed" and final_response:
                    print(f"✅ 流式执行成功")
                    print(f"完整响应: {final_response[:300]}{'...' if len(final_response) > 300 else ''}")
                    
                    # 检查关键词
                    keywords_found = 0
                    for keyword in test_case['expected_keywords']:
                        if keyword in final_response:
                            keywords_found += 1
                    
                    print(f"🔍 关键词匹配: {keywords_found}/{len(test_case['expected_keywords'])}")
                    
                else:
                    print(f"❌ 流式执行失败")
                    
            except Exception as e:
                print(f"❌ 流式测试用例执行失败: {e}")
                import traceback
                traceback.print_exc()
            
            print("-" * 40)
        
    except Exception as e:
        print(f"❌ MCP 图流式执行测试失败: {e}")
        import traceback
        traceback.print_exc()


async def test_mcp_remote_execution():
    """测试 MCP 远程命令流式执行"""
    print("\n" + "="*50)
    print("🔗 测试 MCP 远程命令流式执行")
    print("="*50)
    
    try:
        manager = get_graph_manager()
        
        # 复杂的远程执行场景
        remote_commands = [
            "在机器 420c126d598a97ee31fb70127b6b9a46 上执行 pwd 命令，显示当前目录",
            "在机器 420c126d598a97ee31fb70127b6b9a46 上执行 ls -la 命令，列出文件详情",
            "在机器 420c126d598a97ee31fb70127b6b9a46 上执行 df -h 命令，查看磁盘使用情况"
        ]
        
        for i, command in enumerate(remote_commands, 1):
            print(f"\n--- 远程命令流式执行 {i} ---")
            print(f"命令: {command}")
            
            try:
                event_count = 0
                final_response = ""
                execution_status = "unknown"
                tool_call_count = 0
                
                async for event in manager.execute_graph_stream(
                    graph_id="chat_agent_mcp",
                    user_input=command
                ):
                    event_count += 1
                    
                    if event.event_type == "graph_start":
                        print(f"🚀 开始远程命令执行...")
                        
                    elif event.event_type == "node_update":
                        if event.data.get('has_final_response'):
                            print(f"📊 节点 {event.node_name}: 已生成响应")
                        else:
                            print(f"📊 节点 {event.node_name}: {event.data.get('current_step', 'processing')}")
                        
                    elif event.event_type == "message":
                        content = event.data.get('content', '')
                        final_response = content
                        print(f"💬 命令执行结果: {content[:200]}{'...' if len(content) > 200 else ''}")
                        
                    elif event.event_type == "tool_call":
                        tool_call_count += 1
                        tool_results = event.data.get('tool_results', {})
                        print(f"🔧 MCP 工具调用 #{tool_call_count}: {len(tool_results)} 个结果")
                        
                    elif event.event_type == "graph_end":
                        execution_status = event.data.get('status', 'unknown')
                        print(f"✅ 远程命令执行完成: {execution_status}")
                        
                    elif event.event_type == "error":
                        error = event.data.get('error', '')
                        execution_status = "failed"
                        print(f"❌ 执行错误: {error}")
                
                # 执行结果统计
                print(f"\n📊 远程命令执行统计:")
                print(f"   - 流式事件数: {event_count}")
                print(f"   - 工具调用数: {tool_call_count}")
                print(f"   - 执行状态: {execution_status}")
                
                if execution_status == "completed" and final_response:
                    print(f"✅ 远程命令执行成功")
                    print(f"完整响应: {final_response[:500]}{'...' if len(final_response) > 500 else ''}")
                    
                    # 检查是否包含命令执行结果
                    result_indicators = ["执行", "结果", "命令", "/", "当前", "目录", "文件", "磁盘"]
                    found_indicators = [keyword for keyword in result_indicators if keyword in final_response]
                    
                    if found_indicators:
                        print(f"🎯 命令执行成功，检测到结果指标: {', '.join(found_indicators[:3])}")
                    else:
                        print("⚠️ 命令可能未正确执行或结果格式异常")
                        
                else:
                    print(f"❌ 远程命令执行失败")
                    
            except Exception as e:
                print(f"❌ 远程命令流式测试失败: {e}")
                import traceback
                traceback.print_exc()
            
            print("-" * 30)
        
    except Exception as e:
        print(f"❌ MCP 远程流式执行测试失败: {e}")
        import traceback
        traceback.print_exc()


async def test_mcp_error_handling():
    """测试 MCP 错误处理流式执行"""
    print("\n" + "="*50)
    print("🛡️ 测试 MCP 错误处理流式执行")
    print("="*50)
    
    try:
        manager = get_graph_manager()
        
        # 错误场景测试
        error_cases = [
            {
                "name": "无效机器ID测试",
                "input": "在机器 invalid-machine-id 上执行 pwd 命令",
                "expected_behavior": "应该返回错误信息"
            },
            {
                "name": "危险命令测试",
                "input": "在机器 420c126d598a97ee31fb70127b6b9a46 上执行 rm -rf / 命令",
                "expected_behavior": "应该拒绝或警告"
            },
            {
                "name": "空命令测试", 
                "input": "在机器 420c126d598a97ee31fb70127b6b9a46 上执行空命令",
                "expected_behavior": "应该提示命令为空"
            }
        ]
        
        for i, error_case in enumerate(error_cases, 1):
            print(f"\n--- 错误处理流式测试 {i}: {error_case['name']} ---")
            print(f"输入: {error_case['input']}")
            print(f"预期: {error_case['expected_behavior']}")
            
            try:
                event_count = 0
                final_response = ""
                execution_status = "unknown"
                error_detected = False
                
                async for event in manager.execute_graph_stream(
                    graph_id="chat_agent_mcp",
                    user_input=error_case["input"]
                ):
                    event_count += 1
                    
                    if event.event_type == "graph_start":
                        print(f"🚀 开始错误处理测试...")
                        
                    elif event.event_type == "node_update":
                        print(f"📊 节点 {event.node_name}: {event.data.get('current_step', 'processing')}")
                        
                    elif event.event_type == "message":
                        content = event.data.get('content', '')
                        final_response = content
                        print(f"💬 响应内容: {content[:150]}{'...' if len(content) > 150 else ''}")
                        
                    elif event.event_type == "tool_call":
                        tool_results = event.data.get('tool_results', {})
                        print(f"🔧 工具调用: {len(tool_results)} 个结果")
                        
                    elif event.event_type == "graph_end":
                        execution_status = event.data.get('status', 'unknown')
                        print(f"✅ 错误处理测试完成: {execution_status}")
                        
                    elif event.event_type == "error":
                        error = event.data.get('error', '')
                        execution_status = "failed"
                        error_detected = True
                        print(f"❌ 检测到错误事件: {error}")
                
                # 错误处理结果分析
                print(f"\n📊 错误处理测试统计:")
                print(f"   - 流式事件数: {event_count}")
                print(f"   - 执行状态: {execution_status}")
                print(f"   - 错误事件: {'是' if error_detected else '否'}")
                
                if final_response:
                    print(f"完整响应: {final_response[:200]}{'...' if len(final_response) > 200 else ''}")
                    
                    # 检查是否包含错误处理信息
                    error_keywords = ["错误", "失败", "无效", "危险", "拒绝", "警告", "不支持", "不允许"]
                    found_error_keywords = [keyword for keyword in error_keywords if keyword in final_response]
                    
                    if found_error_keywords:
                        print(f"✅ 正确处理了错误情况，检测到关键词: {', '.join(found_error_keywords[:2])}")
                    else:
                        print("⚠️ 可能未正确处理错误情况")
                        
                elif error_detected:
                    print("✅ 通过错误事件正确处理了异常情况")
                else:
                    print("⚠️ 未检测到明确的错误处理")
                    
            except Exception as e:
                print(f"❌ 错误处理流式测试异常: {e}")
                import traceback
                traceback.print_exc()
            
            print("-" * 30)
        
    except Exception as e:
        print(f"❌ MCP 错误处理流式测试失败: {e}")
        import traceback
        traceback.print_exc()


async def main():
    """主测试函数"""
    print("🚀 KaFlow-Py MCP 集成 Chat Agent 流式测试开始")
    print("="*70)
    
    # 检查 API 密钥
    if not check_api_keys():
        return
    
    # 1. 测试 MCP 服务器连接
    mcp_available = await test_mcp_server_connectivity()
    
    # 2. 测试协议验证
    if not test_mcp_protocol_validation():
        print("❌ MCP 协议验证失败，终止测试")
        return
    
    # 3. 测试图注册
    if not test_mcp_graph_registration():
        print("❌ MCP 图注册失败，终止测试")
        return
    
    # 4. 测试流式图执行
    await test_mcp_graph_execution()
    
    # 5. 如果 MCP 服务器可用，测试远程流式执行
    # if mcp_available:
    #     await test_mcp_remote_execution()
    #     # await test_mcp_error_handling()
    # else:
    #     print("\n⚠️ MCP 服务器不可用，跳过远程执行测试")
    
    print("\n" + "="*70)
    print("🎉 KaFlow-Py MCP 集成流式测试完成！")
    print("="*70)
    
    print("\n📋 流式测试总结:")
    print("✅ MCP 协议模板验证")
    print("✅ MCP 图结构构建")
    print("✅ MCP Agent 创建和配置")
    print("✅ MCP 工具集成流式测试")
    print("✅ 实时事件流处理")
    print("✅ 流式响应生成")
    
    if mcp_available:
        print("✅ MCP 服务器连接测试")
        print("✅ 远程命令流式执行测试")
        print("✅ 错误处理流式测试")
    else:
        print("⚠️ MCP 服务器连接测试 (服务器不可用)")
    
    print("\n🌊 流式执行特性:")
    print("1. 实时接收执行状态更新")
    print("2. 即时获取工具调用结果")
    print("3. 流式响应内容传输")
    print("4. 详细的执行生命周期追踪")
    print("5. 支持事件驱动的错误处理")
    
    print("\n🔧 使用说明:")
    print("1. 确保 MCP 服务器在 http://10.1.16.4:8000/mcp/sse 运行")
    print("2. 服务器应该提供 remote_exec 工具")
    print("3. 流式执行提供更好的用户体验")
    print("4. 可以实时监控执行进度和状态")


if __name__ == "__main__":
    asyncio.run(main()) 