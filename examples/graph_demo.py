"""
KaFlow-Py Graph 系统使用示例

演示如何使用 Graph 系统构建和执行智能对话流程

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


async def demo_simple_chat():
    """演示简单聊天 Agent"""
    print("🤖 简单聊天 Agent 演示")
    print("=" * 40)
    
    manager = get_graph_manager()
    
    # 创建简单的聊天配置
    simple_chat_config = {
        "id": "demo_simple_chat",
        "name": "演示聊天助手",
        "version": "1.0.0",
        "description": "用于演示的简单聊天助手",
        "variables": {
            "model": "gpt-4o-mini",
            "temperature": 0.7
        },
        "nodes": [
            {
                "id": "start",
                "name": "开始",
                "type": "start",
                "description": "对话开始"
            },
            {
                "id": "chat_agent",
                "name": "聊天助手",
                "type": "agent",
                "description": "智能聊天助手",
                "agent_type": "simple",
                "system_prompt": "你是一个友好的AI助手，请用中文简洁地回答用户的问题。",
                "llm_config": {
                    "provider": "openai",
                    "api_key": "test-key",  # 这里使用测试密钥，实际使用时请替换
                    "model": "${model}",
                    "temperature": "${temperature}"
                },
                "timeout": 30
            },
            {
                "id": "end",
                "name": "结束",
                "type": "end",
                "description": "对话结束"
            }
        ],
        "edges": [
            {
                "id": "start_to_chat",
                "source": "start",
                "target": "chat_agent",
                "type": "normal"
            },
            {
                "id": "chat_to_end",
                "source": "chat_agent",
                "target": "end",
                "type": "normal"
            }
        ],
        "start_node": "start",
        "end_nodes": ["end"]
    }
    
    # 注册并执行图
    try:
        graph_config = manager.register_graph_from_dict(simple_chat_config)
        print(f"✅ 图注册成功: {graph_config.name}")
        
        # 准备多个测试问题
        test_questions = [
            "你好！",
            "你能做什么？",
            "今天天气怎么样？",
            "请介绍一下人工智能",
            "谢谢你的帮助"
        ]
        
        for i, question in enumerate(test_questions, 1):
            print(f"\n💬 问题 {i}: {question}")
            
            # 执行图
            execution_result = await manager.execute_graph(
                graph_config.id,
                {"message": question}
            )
            
            print(f"📊 执行状态: {execution_result.status}")
            print(f"⏱️  执行时长: {execution_result.duration:.2f}秒")
            
            # 获取聊天 Agent 的输出
            for node_exec in execution_result.node_executions:
                if node_exec.node_id == "chat_agent" and node_exec.output_data:
                    output = node_exec.output_data
                    if "response" in output:
                        print(f"🤖 回答: {output['response']}")
                    elif "error" in output:
                        print(f"❌ 错误: {output['error']}")
                    break
            
            print("-" * 40)
    
    except Exception as e:
        print(f"❌ 演示失败: {e}")
        import traceback
        traceback.print_exc()


async def demo_yaml_config():
    """演示 YAML 配置文件的使用"""
    print("\n📄 YAML 配置文件演示")
    print("=" * 40)
    
    manager = get_graph_manager()
    
    # 从 YAML 文件加载配置
    yaml_path = project_root / "examples" / "graphs" / "simple_chat.yaml"
    
    try:
        if yaml_path.exists():
            graph_config = manager.register_graph_from_yaml(yaml_path, "yaml_demo")
            print(f"✅ YAML 配置加载成功: {graph_config.name}")
            print(f"📝 描述: {graph_config.description}")
            print(f"🔧 变量: {graph_config.variables}")
            print(f"📊 节点数: {len(graph_config.nodes)}")
            print(f"🔗 边数: {len(graph_config.edges)}")
            
            # 执行图
            print(f"\n🚀 执行图...")
            execution_result = await manager.execute_graph(
                graph_config.id,
                {"message": "请用一句话介绍你自己"}
            )
            
            print(f"✅ 执行完成: {execution_result.status}")
            print(f"⏱️  执行时长: {execution_result.duration:.2f}秒")
            
        else:
            print(f"⚠️  YAML 文件不存在: {yaml_path}")
            
    except Exception as e:
        print(f"❌ YAML 演示失败: {e}")


def demo_graph_validation():
    """演示图验证功能"""
    print("\n🔍 图验证演示")
    print("=" * 40)
    
    manager = get_graph_manager()
    
    # 创建一个有问题的图配置
    invalid_config = {
        "id": "invalid_graph",
        "name": "无效图",
        "version": "1.0.0",
        "nodes": [
            {
                "id": "start",
                "name": "开始",
                "type": "start"
            },
            {
                "id": "missing_end",
                "name": "缺少结束节点",
                "type": "agent"
            }
        ],
        "edges": [
            {
                "id": "start_to_missing",
                "source": "start",
                "target": "nonexistent_node",  # 不存在的节点
                "type": "normal"
            }
        ],
        "start_node": "start",
        "end_nodes": ["nonexistent_end"]  # 不存在的结束节点
    }
    
    try:
        # 尝试构建无效图
        graph_config = manager.register_graph_from_dict(invalid_config)
        print("❌ 应该验证失败但却成功了")
    except ValueError as e:
        print(f"✅ 验证失败（预期）: {e}")
    
    # 创建一个有效的图
    valid_config = {
        "id": "valid_graph",
        "name": "有效图",
        "version": "1.0.0",
        "nodes": [
            {"id": "start", "name": "开始", "type": "start"},
            {"id": "end", "name": "结束", "type": "end"}
        ],
        "edges": [
            {"id": "start_to_end", "source": "start", "target": "end", "type": "normal"}
        ],
        "start_node": "start",
        "end_nodes": ["end"]
    }
    
    try:
        graph_config = manager.register_graph_from_dict(valid_config)
        print(f"✅ 有效图构建成功: {graph_config.name}")
        
        # 验证图
        validation_result = manager.validate_graph(graph_config.id)
        if validation_result.is_valid:
            print("✅ 图验证通过")
        else:
            print(f"❌ 图验证失败: {validation_result.errors}")
            
    except Exception as e:
        print(f"❌ 有效图构建失败: {e}")


def demo_graph_management():
    """演示图管理功能"""
    print("\n📊 图管理演示")
    print("=" * 40)
    
    manager = get_graph_manager()
    
    # 获取所有注册的图
    graphs = manager.list_graphs()
    print(f"📋 当前注册的图数量: {len(graphs)}")
    
    for graph in graphs:
        print(f"   🔹 {graph.id}: {graph.name} (v{graph.version})")
        print(f"      描述: {graph.description or '无描述'}")
        print(f"      节点: {len(graph.nodes)} 个")
        print(f"      边: {len(graph.edges)} 个")
        print(f"      标签: {graph.tags}")
        print()
    
    # 获取统计信息
    stats = manager.get_graph_statistics()
    print(f"📈 统计信息:")
    print(f"   总图数: {stats['total_graphs']}")
    print(f"   总执行数: {stats['total_executions']}")
    
    if stats['execution_status_counts']:
        print(f"   执行状态分布:")
        for status, count in stats['execution_status_counts'].items():
            print(f"      {status}: {count}")
    
    if stats['graph_execution_counts']:
        print(f"   图执行次数:")
        for graph_id, count in stats['graph_execution_counts'].items():
            print(f"      {graph_id}: {count}")


async def demo_custom_node_types():
    """演示自定义节点类型"""
    print("\n🔧 自定义节点类型演示")
    print("=" * 40)
    
    manager = get_graph_manager()
    
    # 注册自定义节点执行器
    async def custom_greeting_executor(node_config, graph_execution):
        """自定义问候节点执行器"""
        user_name = graph_execution.execution_context.get('input_data', {}).get('user_name', '朋友')
        greeting = f"你好，{user_name}！欢迎使用 KaFlow-Py Graph 系统！"
        return {"greeting": greeting, "timestamp": "2025-09-15"}
    
    # 注册自定义执行器（使用字符串类型）
    manager.register_node_executor("greeting", custom_greeting_executor)
    
    # 创建使用自定义节点的图
    custom_graph_config = {
        "id": "custom_demo",
        "name": "自定义节点演示",
        "version": "1.0.0",
        "nodes": [
            {"id": "start", "name": "开始", "type": "start"},
            {
                "id": "greeting",
                "name": "问候节点",
                "type": "greeting",  # 自定义类型
                "description": "自定义问候节点"
            },
            {"id": "end", "name": "结束", "type": "end"}
        ],
        "edges": [
            {"id": "start_to_greeting", "source": "start", "target": "greeting", "type": "normal"},
            {"id": "greeting_to_end", "source": "greeting", "target": "end", "type": "normal"}
        ],
        "start_node": "start",
        "end_nodes": ["end"]
    }
    
    try:
        graph_config = manager.register_graph_from_dict(custom_graph_config)
        print(f"✅ 自定义图注册成功: {graph_config.name}")
        
        # 执行自定义图
        execution_result = await manager.execute_graph(
            graph_config.id,
            {"user_name": "DevYK"}
        )
        
        print(f"✅ 执行完成: {execution_result.status}")
        
        # 显示自定义节点的输出
        for node_exec in execution_result.node_executions:
            if node_exec.node_id == "greeting" and node_exec.output_data:
                output = node_exec.output_data
                print(f"🎉 问候信息: {output.get('greeting')}")
                break
                
    except Exception as e:
        print(f"❌ 自定义节点演示失败: {e}")


async def main():
    """主演示函数"""
    print("🚀 KaFlow-Py Graph 系统完整演示")
    print("=" * 50)
    
    # 1. 简单聊天演示
    await demo_simple_chat()
    
    # 2. YAML 配置演示
    await demo_yaml_config()
    
    # 3. 图验证演示
    demo_graph_validation()
    
    # 4. 图管理演示
    demo_graph_management()
    
    # 5. 自定义节点类型演示
    await demo_custom_node_types()
    
    print("\n🎉 所有演示完成！")
    print("\n💡 使用建议:")
    print("   1. 使用 YAML 配置文件来定义复杂的图结构")
    print("   2. 利用变量替换功能来提高配置的灵活性")
    print("   3. 通过自定义节点执行器来扩展系统功能")
    print("   4. 使用图验证功能来确保配置的正确性")
    print("   5. 利用图管理器来统一管理多个图")


if __name__ == "__main__":
    asyncio.run(main()) 