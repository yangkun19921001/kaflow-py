"""
KaFlow-Py 网络搜索工具

基于 DuckDuckGo Search API 实现网络搜索功能，支持普通搜索和新闻搜索

Author: DevYK
微信公众号: DevYK
Email: yang1001yk@gmail.com
Github: https://github.com/yangkun19921001
"""

from typing import Optional, Literal
from langchain_core.tools import tool
from langchain_community.tools import DuckDuckGoSearchResults
from langchain_community.utilities import DuckDuckGoSearchAPIWrapper


@tool
def web_search(
    query: str,
    max_results: int = 5,
    search_type: Literal["general", "news"] = "general"
) -> str:
    """
    使用 DuckDuckGo 进行网络搜索
    
    Args:
        query: 搜索查询关键词
        max_results: 返回的最大结果数量，默认为 5
        search_type: 搜索类型，"general"(普通搜索) 或 "news"(新闻搜索)
        
    Returns:
        搜索结果字符串，包含标题、链接和摘要
    """
    try:
        # 根据搜索类型配置后端
        backend = "news" if search_type == "news" else "general"
        
        # 创建搜索工具
        search_tool = DuckDuckGoSearchResults(
            name="duckduckgo_search",
            max_results=max_results,
            # backend=backend,
            output_format="list"  # 返回列表格式便于处理
        )
        
        # 执行搜索
        results = search_tool.invoke(query)
        
        if not results:
            return f"未找到关于 '{query}' 的搜索结果"
        
        # 格式化输出
        output_lines = [f"=== 搜索结果：{query} ===\n"]
        
        for idx, result in enumerate(results, 1):
            output_lines.append(f"【结果 {idx}】")
            output_lines.append(f"标题：{result.get('title', 'N/A')}")
            output_lines.append(f"链接：{result.get('link', 'N/A')}")
            output_lines.append(f"摘要：{result.get('snippet', 'N/A')}")
            
            # 如果是新闻搜索，可能包含日期和来源
            if search_type == "news":
                if result.get('date'):
                    output_lines.append(f"日期：{result['date']}")
                if result.get('source'):
                    output_lines.append(f"来源：{result['source']}")
            
            output_lines.append("")  # 空行分隔
        
        return "\n".join(output_lines)
        
    except Exception as e:
        return f"错误：搜索 '{query}' 失败：{str(e)}"


@tool
def web_search_advanced(
    query: str,
    max_results: int = 5,
    region: str = "wt-wt",
    time_range: Optional[str] = None,
    search_type: Literal["general", "news"] = "general"
) -> str:
    """
    高级网络搜索，支持更多自定义参数
    
    Args:
        query: 搜索查询关键词
        max_results: 返回的最大结果数量，默认为 5
        region: 搜索区域代码，如 "wt-wt"(全球), "us-en"(美国), "cn-zh"(中国)
        time_range: 时间范围，如 "d"(一天), "w"(一周), "m"(一个月), "y"(一年)
        search_type: 搜索类型，"general"(普通搜索) 或 "news"(新闻搜索)
        
    Returns:
        搜索结果字符串，包含标题、链接和摘要
    """
    try:
        # 根据搜索类型配置后端
        backend = "news" if search_type == "news" else "text"
        
        # 创建自定义的搜索包装器
        wrapper = DuckDuckGoSearchAPIWrapper(
            region=region,
            time=time_range,
            max_results=max_results,
            backend=backend
        )
        
        # 创建搜索工具
        search_tool = DuckDuckGoSearchResults(
            api_wrapper=wrapper,
            output_format="list"
        )
        
        # 执行搜索
        results = search_tool.invoke(query)
        
        if not results:
            return f"未找到关于 '{query}' 的搜索结果"
        
        # 格式化输出
        output_lines = [f"=== 高级搜索结果：{query} ==="]
        output_lines.append(f"区域：{region}，时间范围：{time_range or '不限'}，类型：{search_type}\n")
        
        for idx, result in enumerate(results, 1):
            output_lines.append(f"【结果 {idx}】")
            output_lines.append(f"标题：{result.get('title', 'N/A')}")
            output_lines.append(f"链接：{result.get('link', 'N/A')}")
            output_lines.append(f"摘要：{result.get('snippet', 'N/A')}")
            
            # 新闻搜索的额外信息
            if search_type == "news":
                if result.get('date'):
                    output_lines.append(f"日期：{result['date']}")
                if result.get('source'):
                    output_lines.append(f"来源：{result['source']}")
            
            output_lines.append("")  # 空行分隔
        
        return "\n".join(output_lines)
        
    except Exception as e:
        return f"错误：高级搜索 '{query}' 失败：{str(e)}"


@tool
def news_search(
    query: str,
    max_results: int = 5,
    region: str = "wt-wt"
) -> str:
    """
    专门用于新闻搜索的便捷工具
    
    Args:
        query: 搜索查询关键词
        max_results: 返回的最大结果数量，默认为 5
        region: 搜索区域代码，如 "wt-wt"(全球), "us-en"(美国), "cn-zh"(中国)
        
    Returns:
        新闻搜索结果字符串
    """
    try:
        # 创建自定义的搜索包装器，专门用于新闻
        wrapper = DuckDuckGoSearchAPIWrapper(
            region=region,
            max_results=max_results,
            backend="news"
        )
        
        # 创建搜索工具
        search_tool = DuckDuckGoSearchResults(
            api_wrapper=wrapper,
            output_format="list"
        )
        
        # 执行搜索
        results = search_tool.invoke(query)
        
        if not results:
            return f"未找到关于 '{query}' 的新闻"
        
        # 格式化输出
        output_lines = [f"=== 新闻搜索：{query} ==="]
        output_lines.append(f"区域：{region}\n")
        
        for idx, result in enumerate(results, 1):
            output_lines.append(f"📰 【新闻 {idx}】")
            output_lines.append(f"标题：{result.get('title', 'N/A')}")
            output_lines.append(f"链接：{result.get('link', 'N/A')}")
            output_lines.append(f"摘要：{result.get('snippet', 'N/A')}")
            
            if result.get('date'):
                output_lines.append(f"发布时间：{result['date']}")
            if result.get('source'):
                output_lines.append(f"新闻来源：{result['source']}")
            
            output_lines.append("")  # 空行分隔
        
        return "\n".join(output_lines)
        
    except Exception as e:
        return f"错误：新闻搜索 '{query}' 失败：{str(e)}"


# 导出所有工具
__all__ = ["web_search", "web_search_advanced", "news_search"]

