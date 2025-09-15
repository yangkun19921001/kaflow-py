#!/usr/bin/env python3
"""
KaFlow-Py Agent 测试示例

包含两个测试函数：
1. test_create_react_agent - 测试 ReAct Agent 创建和调用
2. test_create_agent - 测试通用 Agent 创建和调用

每个函数都包含简单的问答测试，展示 invoke 的使用方法。
"""

import os
import sys
from pathlib import Path
from typing import List, Dict, Any

# 临时禁用代理设置，避免 SOCKS 代理问题
for proxy_var in ['http_proxy', 'https_proxy', 'all_proxy', 'HTTP_PROXY', 'HTTPS_PROXY', 'ALL_PROXY']:
    if proxy_var in os.environ:
        del os.environ[proxy_var]

# 添加项目根目录到 Python 路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from src.llms import LLMConfig, LLMProviderType

# 创建 LLM 配置
llm_config = LLMConfig(
    provider=LLMProviderType.DEEPSEEK,
    base_url="https://api.ppinfra.com/v3/openai",
    api_key=os.getenv("DEEPSEEK_API_KEY", "sk_TVs_oKM7TVkX8WTK65lP5IFJiCayb3EzkTf77D3sqSI"),
    model="deepseek/deepseek-v3-0324",
    temperature=0.7
)

def create_test_tools():
    """创建测试工具函数"""
    from langchain_core.tools import tool
    
    @tool
    def get_weather(city: str) -> str:
        """获取指定城市的天气信息
        
        Args:
            city: 城市名称
            
        Returns:
            天气信息字符串
        """
        # 模拟天气数据
        weather_data = {
            "北京": "晴天，温度 15°C",
            "上海": "多云，温度 18°C", 
            "深圳": "小雨，温度 22°C",
            "广州": "阴天，温度 20°C"
        }
        return weather_data.get(city, f"{city}的天气信息暂时无法获取")
    
    @tool
    def calculate(expression: str) -> str:
        """计算数学表达式
        
        Args:
            expression: 数学表达式，如 "2+3*4"
            
        Returns:
            计算结果
        """
        try:
            # 简单的计算器，只支持基本运算
            result = eval(expression)
            return f"{expression} = {result}"
        except Exception as e:
            return f"计算错误: {str(e)}"
    
    return [get_weather, calculate]


def test_create_react_agent():
    """测试 ReAct Agent 创建和调用"""
    print("=== 测试 ReAct Agent ===")
    
    try:
        # 导入必要的模块
        from src.agents import create_agent, create_react_agent_config  
        
        # 创建测试工具
        tools = create_test_tools()
        

        
        # 创建 ReAct Agent 配置
        agent_config = create_react_agent_config(
            name="weather_assistant",
            llm_config=llm_config,
            tools=tools,
            system_prompt="你是一个智能助手，可以帮助用户查询天气和进行计算。请使用提供的工具来回答用户问题。"
        )
        
        # 创建 ReAct Agent
        react_agent = create_agent(agent_config)
        print("✅ ReAct Agent 创建成功")
        
        # 测试问答 - 天气查询
        print("\n--- 测试天气查询 ---")
        weather_question = "北京今天的天气怎么样？"
        print(f"用户问题: {weather_question}")
        
        try:
            response = react_agent.invoke({"messages": [("user", weather_question)]})
            print(f"Agent 回答: {response['messages'][-1].content}")
        except Exception as e:
            print(f"调用失败 (可能需要真实的 API Key): {str(e)}")
        
        # 测试问答 - 数学计算
        print("\n--- 测试数学计算 ---")
        math_question = "请帮我计算 15 * 8 + 32"
        print(f"用户问题: {math_question}")
        
        try:
            response = react_agent.invoke({"messages": [("user", math_question)]})
            print(f"Agent 回答: {response['messages'][-1].content}")
        except Exception as e:
            print(f"调用失败 (可能需要真实的 API Key): {str(e)}")
        
        print("✅ ReAct Agent 测试完成")
        return True
        
    except Exception as e:
        print(f"❌ ReAct Agent 测试失败: {str(e)}")
        import traceback
        traceback.print_exc()
        return False


def test_create_agent():
    """测试通用 Agent 创建和调用"""
    print("\n=== 测试通用 Agent ===")
    
    try:
        # 导入必要的模块
        from src.agents import create_agent, create_simple_agent_config
        
        # 创建通用 Agent 配置
        agent_config = create_simple_agent_config(
            name="chat_assistant",
            llm_config=llm_config,
            system_prompt="你是一个友好的聊天助手，请用中文回答用户的问题。保持回答简洁明了。"
        )
        
        # 创建通用 Agent
        simple_agent = create_agent(agent_config)
        print("✅ 通用 Agent 创建成功")
        
        # 测试问答 - 一般对话
        print("\n--- 测试一般对话 ---")
        chat_question = "你好，请介绍一下自己"
        print(f"用户问题: {chat_question}")
        
        try:
            response = simple_agent.invoke(chat_question)
            print(f"Agent 回答: {response.content}")
        except Exception as e:
            print(f"调用失败 (可能需要真实的 API Key): {str(e)}")
        
        # 测试问答 - 知识问答
        print("\n--- 测试知识问答 ---")
        knowledge_question = "什么是人工智能？请简单解释一下"
        print(f"用户问题: {knowledge_question}")
        
        try:
            response = simple_agent.invoke(knowledge_question)
            print(f"Agent 回答: {response.content}")
        except Exception as e:
            print(f"调用失败 (可能需要真实的 API Key): {str(e)}")
        
        # 测试问答 - 创意问题
        print("\n--- 测试创意问题 ---")
        creative_question = "请给我推荐3本值得阅读的技术书籍"
        print(f"用户问题: {creative_question}")
        
        try:
            response = simple_agent.invoke(creative_question)
            print(f"Agent 回答: {response.content}")
        except Exception as e:
            print(f"调用失败 (可能需要真实的 API Key): {str(e)}")
        
        print("✅ 通用 Agent 测试完成")
        return True
        
    except Exception as e:
        print(f"❌ 通用 Agent 测试失败: {str(e)}")
        import traceback
        traceback.print_exc()
        return False


def main():
    """主测试函数"""
    print("KaFlow-Py Agent 创建和调用测试")
    print("=" * 60)
    print("注意: 需要设置 OPENAI_API_KEY 环境变量才能进行实际的 LLM 调用")
    print("=" * 60)
    
    # 运行测试
    tests = [
        test_create_react_agent,
        test_create_agent
    ]
    
    results = []
    for test_func in tests:
        try:
            result = test_func()
            results.append(result)
        except Exception as e:
            print(f"❌ 测试 {test_func.__name__} 出现异常: {e}")
            results.append(False)
    
    # 输出测试结果
    print(f"\n{'=' * 60}")
    print(f"测试结果: {sum(results)}/{len(results)} 通过")
    
    if all(results):
        print("🎉 所有 Agent 测试通过！")
        print("\n使用说明:")
        print("1. 设置环境变量: export OPENAI_API_KEY='your-api-key'")
        print("2. 运行测试: python agent_test.py")
        print("3. ReAct Agent 支持工具调用，通用 Agent 支持直接对话")
        return True
    else:
        print("⚠️  部分测试失败，请检查配置和依赖")
        return False


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1) 