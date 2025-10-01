# KaFlow-Py 工厂循环功能指南

本指南介绍如何在 `factory.py` 中使用循环功能，该功能参考了 `nodes.py` 中的 `execute_react_loop` 实现。

## 功能概述

工厂循环功能允许 Agent 节点在满足特定条件前重复执行，提供两种退出方式：

1. **分析完成**: 检测到完成标志关键词
2. **达到最大次数**: 达到配置的最大迭代次数

## 配置说明

### 1. LoopConfig 配置

在协议配置中，每个 Agent 可以配置循环参数：

```python
from src.core.graph.parser import LoopInfo

loop_info = LoopInfo(
    enable=True,                           # 启用循环
    max_iterations=5,                      # 最大迭代次数
    force_exit_keywords=["任务完成", "分析完成"]  # 强制退出关键词
)
```

### 2. Agent 配置

```python
from src.core.graph.parser import AgentInfo

agent_info = AgentInfo(
    name="循环分析助手",
    type="agent",  # 或 "react_agent"
    system_prompt="你是一个分析助手。请逐步分析问题，完成后请说'分析完成'。",
    llm=llm_config,
    tools=[],
    mcp_servers=[],
    loop=loop_info  # 循环配置
)
```

## 循环执行逻辑

### 执行流程

1. **初始化**: 设置消息历史和循环计数器
2. **循环执行**: 
   - 调用 Agent 进行一次推理
   - 检查响应是否包含完成标志
   - 如果完成，退出循环；否则继续
3. **退出条件**:
   - 检测到完成关键词
   - 达到最大迭代次数
   - 发生执行错误

### 完成标志检测

系统会检测以下完成标志：

#### 明确完成标志
- 中文: `【最终答案】`, `【分析完成】`, `任务完成`, `分析结束` 等
- 英文: `【final answer】`, `task completed`, `analysis finished` 等

#### 自定义关键词
通过 `force_exit_keywords` 配置的自定义退出关键词

#### 上下文完成标志
智能检测包含"完成"、"结束"等词汇的上下文，排除误报情况

## 使用示例

### 示例 1: 基础循环配置

```python
# 创建循环配置
loop_config = LoopInfo(
    enable=True,
    max_iterations=3,
    force_exit_keywords=["分析完成", "任务结束"]
)

# 创建 Agent 配置
agent_info = AgentInfo(
    name="数据分析助手",
    type="agent",
    system_prompt="请逐步分析数据，完成后说'分析完成'",
    loop=loop_config
)
```

### 示例 2: ReAct Agent 循环

```python
# ReAct Agent 循环配置
loop_config = LoopInfo(
    enable=True,
    max_iterations=10,
    force_exit_keywords=["排查完成", "诊断结束"]
)

agent_info = AgentInfo(
    name="运维排查助手",
    type="react_agent",  # ReAct 类型
    system_prompt="你是运维专家，请使用工具排查问题，完成后说'排查完成'",
    tools=["system_info", "file_reader"],
    loop=loop_config
)
```

### 示例 3: 禁用循环

```python
# 单次执行配置
loop_config = LoopInfo(
    enable=False,  # 禁用循环
    max_iterations=1
)

agent_info = AgentInfo(
    name="简单问答助手",
    type="agent",
    system_prompt="请直接回答用户问题",
    loop=loop_config
)
```

## 执行结果

循环执行完成后，节点输出包含以下信息：

```python
{
    "status": "completed",
    "outputs": {
        "response": "最终响应内容",
        "agent_name": "Agent名称",
        "agent_type": "Agent类型",
        "loop_count": 3,           # 实际循环次数
        "max_iterations": 5        # 最大迭代次数
    }
}
```

## 最佳实践

### 1. 合理设置最大迭代次数

```python
# 根据任务复杂度设置
simple_task_loop = LoopInfo(enable=True, max_iterations=3)    # 简单任务
complex_task_loop = LoopInfo(enable=True, max_iterations=10)  # 复杂任务
analysis_task_loop = LoopInfo(enable=True, max_iterations=15) # 深度分析
```

### 2. 设计清晰的完成标志

```python
# 明确的完成关键词
loop_config = LoopInfo(
    enable=True,
    max_iterations=8,
    force_exit_keywords=[
        "分析完成",
        "排查结束", 
        "任务完成",
        "诊断完毕"
    ]
)
```

### 3. 优化系统提示词

```python
system_prompt = """
你是一个专业的数据分析师。请按以下步骤分析：

1. 数据概览和质量检查
2. 统计分析和模式识别  
3. 异常检测和趋势分析
4. 结论总结

完成所有分析后，请明确说明"分析完成"。
"""
```

### 4. 错误处理

循环执行过程中如果发生错误，系统会：
- 记录错误信息
- 返回错误响应
- 停止循环执行

### 5. 性能考虑

- 设置合理的最大迭代次数，避免无限循环
- 在循环间添加适当延迟（默认1秒）
- 监控循环执行时间和资源消耗

## 调试和监控

### 日志输出

循环执行过程中会输出详细日志：

```
🔄 启用循环执行，最大迭代次数: 5
🎯 执行循环 1/5
✅ 循环 1 执行成功
🎯 执行循环 2/5
🎉 检测到完成标志，循环在第 2 次迭代后结束
```

### 状态监控

通过节点输出监控循环状态：

```python
# 获取循环执行信息
node_output = result_state['node_outputs']['agent_node']
loop_count = node_output['outputs']['loop_count']
max_iterations = node_output['outputs']['max_iterations']

print(f"循环执行了 {loop_count}/{max_iterations} 次")
```

## 与原始实现的对比

| 特性 | nodes.py | factory.py |
|------|----------|------------|
| 循环控制 | ✅ | ✅ |
| 完成检测 | ✅ | ✅ |
| 自定义关键词 | ❌ | ✅ |
| Agent类型支持 | ReAct | ReAct + 普通 |
| 配置灵活性 | 固定 | 可配置 |
| 错误处理 | ✅ | ✅ |

## 故障排除

### 常见问题

1. **循环不退出**
   - 检查完成关键词是否正确
   - 确认 Agent 响应格式
   - 调整系统提示词

2. **过早退出**
   - 检查是否有误报的完成标志
   - 调整 `force_exit_keywords`
   - 优化完成检测逻辑

3. **性能问题**
   - 减少最大迭代次数
   - 优化 Agent 响应时间
   - 添加循环间隔

### 调试技巧

```python
# 启用详细日志
import logging
logging.getLogger("AgentNodeBuilder").setLevel(logging.DEBUG)

# 检查消息历史
messages = result_state.get('messages', [])
for i, msg in enumerate(messages):
    print(f"消息 {i}: {type(msg).__name__} - {msg.content[:100]}")
```

## 总结

工厂循环功能提供了灵活而强大的循环执行能力，支持多种退出条件和Agent类型。通过合理配置和使用，可以实现复杂的多轮推理和分析任务。

关键要点：
- 合理设置最大迭代次数
- 设计清晰的完成标志
- 优化系统提示词
- 做好错误处理和监控 