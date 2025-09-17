# -*- coding: utf-8 -*-
"""
KaFlow-Py LangGraph 自动构建系统测试

测试重构后的基于真正 LangGraph API 的自动构建系统

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


def test_protocol_validation():
    """测试协议验证"""
    print("\n" + "="*50)
    print("🔍 测试协议验证")
    print("="*50)
    
    try:
        manager = get_graph_manager()
        
        # 测试 chat_agent_tools 模板
        config_path = project_root / "src/core/config/chat_agent_tools.yaml.template"
        errors = manager.validate_protocol_file(config_path)
        
        if not errors:
            print("✅ chat_agent_tools.yaml.template 验证通过")
        else:
            print("❌ chat_agent_tools.yaml.template 验证失败:")
            for error in errors:
                print(f"   - {error}")
        
        # 测试 chat_agent 模板
        config_path = project_root / "src/core/config/chat_agent.yaml.template"
        errors = manager.validate_protocol_file(config_path)
        
        if not errors:
            print("✅ chat_agent.yaml.template 验证通过")
        else:
            print("❌ chat_agent.yaml.template 验证失败:")
            for error in errors:
                print(f"   - {error}")
        
        return True
        
    except Exception as e:
        print(f"❌ 协议验证测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_graph_registration():
    """测试图注册"""
    print("\n" + "="*50)
    print("🔧 测试图注册")
    print("="*50)
    
    try:
        manager = get_graph_manager()
        
        # 注册 chat_agent_tools 图
        config_path = project_root / "src/core/config/chat_agent_tools.yaml.template"
        graph_id = manager.register_graph_from_file(config_path, "chat_agent_tools")
        
        print(f"✅ 成功注册图: {graph_id}")
        
        # 获取图信息
        graph_info = manager.get_graph_info(graph_id)
        if graph_info:
            print(f"   - 协议名称: {graph_info['protocol']['name']}")
            print(f"   - 工作流名称: {graph_info['workflow']['name']}")
            print(f"   - 节点数量: {len(graph_info['nodes'])}")
            print(f"   - 边数量: {len(graph_info['edges'])}")
            print(f"   - Agent 数量: {len(graph_info['agents'])}")
        
        # 列出所有图
        graphs = manager.list_graphs()
        print(f"✅ 当前注册的图: {list(graphs.keys())}")
        
        return True
        
    except Exception as e:
        print(f"❌ 图注册测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False


async def test_graph_execution():
    """测试图执行"""
    print("\n" + "="*50)
    print("🚀 测试图执行")
    print("="*50)
    
    try:
        manager = get_graph_manager()
        
        # 测试用例
        test_cases = [
            {
                "name": "简单对话测试",
                "input": "你好，请介绍一下你自己",
                "expected_keywords": ["助手", "帮助"]
            },
            {
                "name": "计算器测试",
                "input": "请帮我计算 (25 + 75) * 0.8 的结果",
                "expected_keywords": ["80", "计算"]
            },
            {
                "name": "时间查询测试", 
                "input": "现在几点了？",
                "expected_keywords": ["时间", "2025"]
            },
            {
                "name": "系统信息测试",
                "input": "获取当前系统的内存使用情况",
                "expected_keywords": ["内存", "GB", "%"]
            }
        ]
        
        for i, test_case in enumerate(test_cases, 1):
            print(f"\n--- 测试 {i}: {test_case['name']} ---")
            print(f"输入: {test_case['input']}")
            
            try:
                # 执行图
                result = await manager.execute_graph(
                    graph_id="chat_agent_tools",
                    user_input=test_case["input"]
                )
                
                print(f"状态: {result.status}")
                print(f"当前步骤: {result.current_step}")
                
                if result.is_success():
                    final_response = result.final_response
                    print(f"✅ 执行成功")
                    print(f"响应长度: {len(final_response)} 字符")
                    print(f"响应内容: {final_response[:200]}{'...' if len(final_response) > 200 else ''}")
                    
                    # 检查关键词
                    keywords_found = 0
                    for keyword in test_case['expected_keywords']:
                        if keyword in final_response:
                            keywords_found += 1
                    
                    print(f"🔍 关键词匹配: {keywords_found}/{len(test_case['expected_keywords'])}")
                    
                    # 显示节点输出
                    if result.node_outputs:
                        print(f"📊 节点执行状态:")
                        for node_name, node_output in result.node_outputs.items():
                            print(f"   - {node_name}: {node_output.get('status', 'unknown')}")
                    
                else:
                    print(f"❌ 执行失败")
                    print(f"错误: {result.error}")
                    
            except Exception as e:
                print(f"❌ 测试用例执行失败: {e}")
                import traceback
                traceback.print_exc()
            
            print("-" * 40)
        
    except Exception as e:
        print(f"❌ 图执行测试失败: {e}")
        import traceback
        traceback.print_exc()


async def test_complex_workflow():
    """测试复杂工作流"""
    print("\n" + "="*50)
    print("🔗 测试复杂工作流")
    print("="*50)
    
    try:
        manager = get_graph_manager()
        
        # 复杂的多工具使用场景
        complex_input = """
        请帮我完成以下任务：
        1. 获取当前时间和日期
        2. 计算 100 * 0.85 的结果
        3. 获取系统内存信息
        4. 将以上信息汇总写入 /tmp/kaflow_auto_summary.txt 文件
        5. 读取刚才写入的文件内容确认
        """
        
        print(f"复杂任务输入:\n{complex_input}")
        
        result = await manager.execute_graph(
            graph_id="chat_agent_tools",
            user_input=complex_input
        )
        
        print(f"状态: {result.status}")
        print(f"当前步骤: {result.current_step}")
        
        if result.is_success():
            final_response = result.final_response
            print(f"\n✅ 复杂任务执行成功")
            print(f"响应长度: {len(final_response)} 字符")
            print(f"响应摘要: {final_response[:400]}...")
            
            # 检查是否涉及多个工具
            tool_keywords = ["时间", "计算", "内存", "文件", "写入"]
            tools_mentioned = sum(1 for keyword in tool_keywords if keyword in final_response)
            print(f"🔧 涉及工具类型: {tools_mentioned}/{len(tool_keywords)}")
            
            # 检查文件是否被创建
            summary_file = Path("/tmp/kaflow_auto_summary.txt")
            if summary_file.exists():
                print(f"📁 成功创建汇总文件: {summary_file}")
                print(f"文件大小: {summary_file.stat().st_size} 字节")
            else:
                print(f"⚠️ 汇总文件未创建")
                
            # 显示详细的节点输出
            if result.node_outputs:
                print(f"\n📊 详细节点执行状态:")
                for node_name, node_output in result.node_outputs.items():
                    status = node_output.get('status', 'unknown')
                    print(f"   - {node_name}: {status}")
                    if 'outputs' in node_output:
                        outputs = node_output['outputs']
                        if isinstance(outputs, dict):
                            for key, value in outputs.items():
                                if isinstance(value, str) and len(value) > 100:
                                    value = value[:100] + "..."
                                print(f"     {key}: {value}")
        else:
            print(f"❌ 复杂任务执行失败")
            print(f"错误: {result.error}")
        
    except Exception as e:
        print(f"❌ 复杂任务测试失败: {e}")
        import traceback
        traceback.print_exc()


def test_graph_management():
    """测试图管理功能"""
    print("\n" + "="*50)
    print("📋 测试图管理功能")
    print("="*50)
    
    try:
        manager = get_graph_manager()
        
        # 注册多个图
        config_path1 = project_root / "src/core/config/chat_agent_tools.yaml.template"
        config_path2 = project_root / "src/core/config/chat_agent.yaml.template"
        
        graph_id1 = manager.register_graph_from_file(config_path1, "tools_agent")
        graph_id2 = manager.register_graph_from_file(config_path2, "simple_agent")
        
        print(f"✅ 注册了两个图: {graph_id1}, {graph_id2}")
        
        # 列出所有图
        graphs = manager.list_graphs()
        print(f"📝 图列表:")
        for graph_id, info in graphs.items():
            print(f"   - {graph_id}: {info.get('name', 'Unknown')} (节点: {info.get('nodes_count', 0)})")
        
        # 获取图信息
        for graph_id in [graph_id1, graph_id2]:
            info = manager.get_graph_info(graph_id)
            if info:
                print(f"\n📊 图 {graph_id} 详细信息:")
                print(f"   - 协议: {info['protocol']['name']}")
                print(f"   - 节点: {[node['name'] for node in info['nodes']]}")
                print(f"   - Agent: {list(info['agents'].keys())}")
        
        # 移除一个图
        success = manager.remove_graph(graph_id2)
        print(f"🗑️ 移除图 {graph_id2}: {'成功' if success else '失败'}")
        
        # 再次列出图
        graphs = manager.list_graphs()
        print(f"📝 移除后的图列表: {list(graphs.keys())}")
        
        return True
        
    except Exception as e:
        print(f"❌ 图管理测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False


async def main():
    """主测试函数"""
    print("🚀 KaFlow-Py LangGraph 自动构建系统测试开始")
    print("="*70)
    
    # 检查 API 密钥
    if not check_api_keys():
        return
    
    # 1. 测试协议验证
    if not test_protocol_validation():
        print("❌ 协议验证失败，终止测试")
        return
    
    # 2. 测试图注册
    if not test_graph_registration():
        print("❌ 图注册失败，终止测试")
        return
    
    # 3. 测试图管理
    if not test_graph_management():
        print("❌ 图管理测试失败")
    
    # 4. 测试图执行
    await test_graph_execution()
    
    # 5. 测试复杂工作流
    await test_complex_workflow()
    
    print("\n" + "="*70)
    print("🎉 LangGraph 自动构建系统测试完成！")
    print("="*70)


if __name__ == "__main__":
    asyncio.run(main()) 