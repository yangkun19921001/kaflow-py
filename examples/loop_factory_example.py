# -*- coding: utf-8 -*-
"""
工厂循环功能测试示例

测试 factory.py 中的循环功能实现

Author: DevYK
"""

import asyncio
import sys
import os
from pathlib import Path

# 添加项目根目录到 Python 路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from src.core.graph.factory import AgentNodeBuilder, GraphState
from src.core.graph.parser import ParsedProtocol, WorkflowNode, AgentInfo, LoopInfo
from src.llms.config import LLMConfig
from src.agents.config import AgentType

# 创建测试用的协议配置
def create_test_protocol():
    """创建测试协议"""
    
    # LLM 配置
    llm_config = {
        "provider": "deepseek",
        "model": "deepseek/deepseek-v3-0324",
        "api_key": os.getenv("DEEPSEEK_API_KEY", "sk_TVs_oKM7TVkX8WTK65lP5IFJiCayb3EzkTf77D3sqSI"),
        "base_url": "https://api.ppinfra.com/v3/openai"
    }
    
    # 循环配置
    loop_info = LoopInfo(
        enable=True,
        max_iterations=3,
        force_exit_keywords=["任务完成", "分析完成", "结束"]
    )
    
    # Agent 配置
    agent_info = AgentInfo(
        name="测试循环助手",
        type="agent",
        system_prompt="你是一个测试助手。请逐步分析问题，当你认为分析完成时，请在回答中包含'分析完成'。",
        llm=llm_config,
        tools=[],
        mcp_servers=[],
        loop=loop_info
    )
    
    # 工作流节点
    workflow_node = WorkflowNode(
        name="test_agent_node",
        type="agent",
        agent_ref="test_agent",
        inputs=[],
        outputs=[],
        conditions={}
    )
    
    # 协议
    protocol = ParsedProtocol(
        name="测试循环协议",
        description="测试循环功能",
        version="1.0.0",
        llm_config=llm_config,
        agents={"test_agent": agent_info},
        workflow=type('Workflow', (), {'nodes': [workflow_node]})()
    )
    
    return protocol, workflow_node


async def test_loop_functionality():
    """测试循环功能"""
    print("=== 测试循环功能 ===")
    
    try:
        # 创建测试协议
        protocol, workflow_node = create_test_protocol()
        
        # 创建 Agent 节点构建器
        builder = AgentNodeBuilder(protocol)
        
        # 构建节点函数
        node_function = builder.build(workflow_node)
        
        # 创建测试状态
        test_state = GraphState(
            messages=[],
            user_input="请帮我分析一下人工智能的发展趋势，分步骤进行分析",
            current_step="",
            tool_results={},
            final_response="",
            context={},
            node_outputs={}
        )
        
        print(f"输入: {test_state['user_input']}")
        print("开始执行循环...")
        
        # 执行节点函数
        result_state = await node_function.func(test_state)
        
        # 输出结果
        print(f"\n执行完成!")
        print(f"最终响应: {result_state['final_response']}")
        print(f"当前步骤: {result_state['current_step']}")
        
        # 输出节点执行信息
        node_output = result_state['node_outputs'].get('test_agent_node', {})
        if node_output:
            outputs = node_output.get('outputs', {})
            print(f"\n节点执行信息:")
            print(f"  状态: {node_output.get('status', 'unknown')}")
            print(f"  Agent 名称: {outputs.get('agent_name', 'unknown')}")
            print(f"  Agent 类型: {outputs.get('agent_type', 'unknown')}")
            print(f"  循环次数: {outputs.get('loop_count', 'N/A')}")
            print(f"  最大迭代次数: {outputs.get('max_iterations', 'N/A')}")
        
        # 输出消息历史
        messages = result_state.get('messages', [])
        if messages:
            print(f"\n消息历史 ({len(messages)} 条):")
            for i, msg in enumerate(messages, 1):
                msg_type = type(msg).__name__
                content = getattr(msg, 'content', str(msg))
                print(f"  {i}. [{msg_type}]: {content[:100]}...")
        
    except Exception as e:
        print(f"❌ 测试失败: {e}")
        import traceback
        traceback.print_exc()


async def test_single_execution():
    """测试单次执行"""
    print("\n=== 测试单次执行 ===")
    
    try:
        # 创建测试协议（禁用循环）
        protocol, workflow_node = create_test_protocol()
        
        # 禁用循环
        protocol.agents["test_agent"].loop.enable = False
        
        # 创建 Agent 节点构建器
        builder = AgentNodeBuilder(protocol)
        
        # 构建节点函数
        node_function = builder.build(workflow_node)
        
        # 创建测试状态
        test_state = GraphState(
            messages=[],
            user_input="请简单介绍一下机器学习",
            current_step="",
            tool_results={},
            final_response="",
            context={},
            node_outputs={}
        )
        
        print(f"输入: {test_state['user_input']}")
        print("开始单次执行...")
        
        # 执行节点函数
        result_state = await node_function.func(test_state)
        
        # 输出结果
        print(f"\n执行完成!")
        print(f"最终响应: {result_state['final_response']}")
        
        # 输出节点执行信息
        node_output = result_state['node_outputs'].get('test_agent_node', {})
        if node_output:
            outputs = node_output.get('outputs', {})
            print(f"\n节点执行信息:")
            print(f"  状态: {node_output.get('status', 'unknown')}")
            print(f"  Agent 名称: {outputs.get('agent_name', 'unknown')}")
            print(f"  Agent 类型: {outputs.get('agent_type', 'unknown')}")
            print(f"  循环次数: {outputs.get('loop_count', '单次执行')}")
        
    except Exception as e:
        print(f"❌ 测试失败: {e}")
        import traceback
        traceback.print_exc()


async def main():
    """主函数"""
    print("工厂循环功能测试")
    print("=" * 50)
    
    # 测试循环功能
    await test_loop_functionality()
    
    # 测试单次执行
    await test_single_execution()
    
    print("\n所有测试完成！")


if __name__ == "__main__":
    asyncio.run(main()) 