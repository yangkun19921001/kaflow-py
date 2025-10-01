"""
图构建器使用示例

展示如何使用图构建器创建和执行工作流，包括：
1. 基础图构建
2. 任务规划工作流
3. 自定义节点和流程

Author: DevYK
WeChat: DevYK
Email: yang1001yk@gmail.com
Github: https://github.com/yangkun19921001
"""

import asyncio
import sys
import os

# 添加 src 目录到路径
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from builder import (
    GraphBuilder, TaskPlanningGraphBuilder, 
    create_graph_builder, create_task_planning_graph,
    GraphExecutionMode
)
from nodes import (
    create_start_node, create_task_planning_node,
    create_subtask_execution_node, create_completion_node
)
from agents import AgentConfig, AgentType
from llms import LLMConfig, LLMProviderType
from tools import calculator, current_time, system_info


def example_1_basic_graph():
    """示例 1: 基础图构建"""
    print("=== 示例 1: 基础图构建 ===")
    
    # 创建图构建器
    builder = create_graph_builder(
        name="基础工作流",
        description="演示基础图构建功能"
    )
    
    # 创建节点
    start_node = create_start_node()
    completion_node = create_completion_node()
    
    # 添加节点和连接
    builder.add_node(start_node)
    builder.add_node(completion_node)
    builder.add_edge("start", "completion")
    
    # 构建图
    builder.build()
    
    # 查看图信息
    info = builder.get_graph_info()
    print(f"图名称: {info['name']}")
    print(f"节点数量: {info['node_count']}")
    print(f"边数量: {info['edge_count']}")
    
    # 可视化图结构
    print("\n图结构:")
    print(builder.visualize())
    print()


async def example_2_task_planning_workflow():
    """示例 2: 任务规划工作流"""
    print("=== 示例 2: 任务规划工作流 ===")
    
    # 配置 LLM
    llm_config = LLMConfig(
        provider=LLMProviderType.DEEPSEEK,
        api_key="your-deepseek-api-key",  # 请替换为实际的 API Key
        model="deepseek-chat",
        temperature=0.7
    )
    
    # 配置各个阶段的 Agent
    planning_agent_config = AgentConfig(
        name="任务规划师",
        agent_type=AgentType.REACT_AGENT,
        llm_config=llm_config,
        system_prompt="你是一个任务规划专家，擅长将复杂任务分解为可执行的子任务。",
        tools=[current_time]
    )
    
    execution_agent_config = AgentConfig(
        name="任务执行者",
        agent_type=AgentType.REACT_AGENT,
        llm_config=llm_config,
        system_prompt="你是一个任务执行专家，能够高效完成各种子任务。",
        tools=[calculator, system_info, current_time]
    )
    
    completion_agent_config = AgentConfig(
        name="报告生成器",
        llm_config=llm_config,
        system_prompt="你是一个报告生成专家，能够整理和总结执行结果。"
    )
    
    # 创建任务规划图
    graph_builder = create_task_planning_graph(
        name="智能任务处理系统",
        description="基于AI的任务规划和执行系统",
        planning_agent_config=planning_agent_config,
        execution_agent_config=execution_agent_config,
        completion_agent_config=completion_agent_config
    )
    
    # 查看图结构
    builder = graph_builder.get_builder()
    print("图结构:")
    print(builder.visualize())
    
    # 执行工作流
    user_input = "请帮我分析当前系统状态，并计算从现在到今天结束还有多少小时"
    
    print(f"\n用户输入: {user_input}")
    print("开始执行工作流...")
    
    try:
        result = await graph_builder.execute(user_input)
        
        print(f"\n执行结果:")
        print(f"成功: {result.success}")
        print(f"执行时间: {result.execution_time:.2f}s")
        print(f"执行路径: {' -> '.join(result.execution_path)}")
        print(f"\n最终输出:\n{result.final_output}")
        
        # 显示各节点结果
        print(f"\n各节点执行结果:")
        for node_id, node_result in result.node_results.items():
            print(f"  {node_id}: {len(str(node_result))} 字符的输出")
        
    except Exception as e:
        print(f"执行失败: {e}")
    
    print()


async def example_3_custom_workflow():
    """示例 3: 自定义工作流"""
    print("=== 示例 3: 自定义工作流 ===")
    
    # 配置 LLM
    llm_config = LLMConfig(
        provider=LLMProviderType.DEEPSEEK,
        api_key="your-deepseek-api-key",
        model="deepseek-chat"
    )
    
    # 创建自定义图构建器
    builder = create_graph_builder(
        name="自定义分析流程",
        description="自定义的数据分析工作流"
    )
    
    # 创建节点
    start_node = create_start_node("start", "开始分析")
    
    # 数据收集节点
    data_collection_config = AgentConfig(
        name="数据收集器",
        llm_config=llm_config,
        system_prompt="你是一个数据收集专家，负责收集和整理相关信息。",
        tools=[system_info, current_time]
    )
    data_node = create_task_planning_node(
        "data_collection", "数据收集", data_collection_config
    )
    
    # 数据分析节点
    analysis_config = AgentConfig(
        name="数据分析师",
        llm_config=llm_config,
        system_prompt="你是一个数据分析专家，能够深入分析数据并得出结论。",
        tools=[calculator]
    )
    analysis_node = create_subtask_execution_node(
        "data_analysis", "数据分析", analysis_config
    )
    
    # 报告生成节点
    report_config = AgentConfig(
        name="报告生成器",
        llm_config=llm_config,
        system_prompt="你是一个报告撰写专家，能够生成专业的分析报告。"
    )
    report_node = create_completion_node(
        "report_generation", "报告生成", report_config
    )
    
    # 构建图结构
    builder.add_node(start_node)
    builder.add_node(data_node)
    builder.add_node(analysis_node)
    builder.add_node(report_node)
    
    # 定义执行流程
    builder.add_edge("start", "data_collection")
    builder.add_edge("data_collection", "data_analysis")
    builder.add_edge("data_analysis", "report_generation")
    
    # 构建并执行
    builder.build()
    
    print("自定义工作流结构:")
    print(builder.visualize())
    
    # 执行工作流
    user_input = "请分析当前计算机的性能状态，包括CPU、内存等信息"
    
    print(f"\n用户输入: {user_input}")
    print("开始执行自定义工作流...")
    
    try:
        result = await builder.execute(user_input)
        
        print(f"\n执行结果:")
        print(f"成功: {result.success}")
        print(f"执行时间: {result.execution_time:.2f}s")
        print(f"会话ID: {result.session_id}")
        print(f"\n最终输出:\n{result.final_output}")
        
    except Exception as e:
        print(f"执行失败: {e}")
    
    print()


def example_4_conditional_workflow():
    """示例 4: 条件工作流（演示）"""
    print("=== 示例 4: 条件工作流 ===")
    
    # 创建带条件分支的图构建器
    builder = create_graph_builder(
        name="条件分支流程",
        description="演示条件分支的工作流",
        execution_mode=GraphExecutionMode.CONDITIONAL
    )
    
    # 创建节点
    start_node = create_start_node()
    planning_node = create_task_planning_node()
    execution_node = create_subtask_execution_node()
    completion_node = create_completion_node()
    
    # 添加节点
    builder.add_node(start_node)
    builder.add_node(planning_node)
    builder.add_node(execution_node)
    builder.add_node(completion_node)
    
    # 添加基本边
    builder.add_edge("start", "task_planning")
    builder.add_edge("subtask_execution", "completion")
    
    # 添加条件边（示例）
    def planning_condition(state):
        """规划后的条件判断"""
        # 这里可以根据规划结果决定下一步
        # 示例：如果有子任务则执行，否则直接完成
        subtasks = state.global_context.get("subtasks", [])
        if subtasks and len(subtasks) > 0:
            return "subtask_execution"
        else:
            return "completion"
    
    builder.add_conditional_edge("task_planning", planning_condition)
    
    # 构建图
    builder.build()
    
    print("条件工作流结构:")
    print(builder.visualize())
    
    # 显示图信息
    info = builder.get_graph_info()
    print(f"\n图信息:")
    print(f"- 节点数: {info['node_count']}")
    print(f"- 普通边数: {info['edge_count']}")
    print(f"- 条件边数: {info['conditional_edge_count']}")
    print(f"- 执行模式: {info['execution_mode']}")
    print()


def example_5_graph_management():
    """示例 5: 图管理功能"""
    print("=== 示例 5: 图管理功能 ===")
    
    # 创建任务规划图
    graph_builder = create_task_planning_graph(
        name="项目管理系统",
        description="用于项目任务管理的工作流系统"
    )
    
    # 获取底层构建器
    builder = graph_builder.get_builder()
    
    # 查看详细信息
    info = builder.get_graph_info()
    
    print("图详细信息:")
    print(f"名称: {info['name']}")
    print(f"描述: {info['description']}")
    print(f"构建状态: {info['is_built']}")
    print(f"执行模式: {info['execution_mode']}")
    
    print(f"\n节点列表:")
    for node in info['nodes']:
        print(f"  - {node['id']}: {node['name']} ({node['type']})")
        print(f"    状态: {node['status']}")
        print(f"    输入: {node['inputs']}")
        print(f"    输出: {node['outputs']}")
    
    print(f"\n连接列表:")
    for edge in info['edges']:
        print(f"  {edge['from']} -> {edge['to']}")
    
    # 可视化
    print(f"\n图可视化:")
    print(builder.visualize())
    print()


async def main():
    """主函数 - 运行所有示例"""
    print("图构建器使用示例集合\n")
    
    # 基础示例
    example_1_basic_graph()
    example_4_conditional_workflow()
    example_5_graph_management()
    
    # 需要 API Key 的示例（注释掉以避免错误）
    print("注意: 以下示例需要配置真实的 API Key 才能运行")
    print("请在代码中替换 'your-deepseek-api-key' 为实际的 API Key\n")
    
    # await example_2_task_planning_workflow()
    # await example_3_custom_workflow()
    
    print("所有示例展示完成！")
    print("\n💡 使用提示:")
    print("1. 配置真实的 API Key 后可以运行完整的工作流")
    print("2. 可以根据需要自定义节点和流程")
    print("3. 支持条件分支和并行执行")
    print("4. 所有节点函数都可以自定义实现")


if __name__ == "__main__":
    # 运行示例
    asyncio.run(main()) 