"""
KaFlow-Py Browser Use 工具

将 browser-use 开源库封装成 LangChain tool，支持浏览器自动化任务

Author: DevYK
微信公众号: DevYK
Email: yang1001yk@gmail.com
Github: https://github.com/yangkun19921001

Reference: https://github.com/co-browser/browser-use-mcp-server
"""

import asyncio
from typing import Optional, Dict, Any
from langchain_core.tools import tool
from ..utils.logger import get_logger
from ..llms.config import LLMProviderType

logger = get_logger("BrowserUseTool")


def _extract_llm_config(llm: Any) -> Dict[str, Any]:
    """
    从 LangChain LLM 对象中提取配置信息
    
    Args:
        llm: LangChain LLM 实例
        
    Returns:
        包含 api_key, base_url, model, temperature, provider 的字典
    """
    logger.info(f"📋 Extracting config from LLM type: {type(llm).__name__}")
    
    config = {}
    
    # 提取 API key (支持不同的属性名)
    api_key = (
        getattr(llm, "openai_api_key", None) or 
        getattr(llm, "anthropic_api_key", None) or 
        getattr(llm, "google_api_key", None) or 
        getattr(llm, "api_key", None)
    )
    
    # 提取 base_url
    base_url = (
        getattr(llm, "openai_api_base", None) or 
        getattr(llm, "base_url", None)
    )
    
    # 提取 model
    model = (
        getattr(llm, "model_name", None) or 
        getattr(llm, "model", None)
    )
    
    # 提取 temperature
    temperature = getattr(llm, "temperature", 0.0)
    
    # 处理 SecretStr 类型
    api_key_raw = api_key
    base_url_raw = base_url
    
    if api_key and hasattr(api_key, "get_secret_value"):
        api_key = api_key.get_secret_value()
        logger.debug(f"   ✓ Decoded SecretStr for api_key")
    
    if base_url and hasattr(base_url, "get_secret_value"):
        base_url = base_url.get_secret_value()
        logger.debug(f"   ✓ Decoded SecretStr for base_url")
    
    # 打印原始提取的值（用于调试）
    logger.info(f"   Raw extracted values:")
    logger.info(f"   - api_key type: {type(api_key_raw)}, has value: {bool(api_key)}, length: {len(api_key) if api_key else 0}")
    logger.info(f"   - base_url type: {type(base_url_raw)}, value: {base_url}")
    logger.info(f"   - model: {model}")
    logger.info(f"   - temperature: {temperature}")
    
    # 注意：不再裁剪模型名称！
    # 某些 API 代理（如 ppinfra）需要完整的模型名称（包括前缀）
    # 例如：deepseek/deepseek-v3-0324 而不是 deepseek-v3-0324
    logger.info(f"   ℹ️  Keeping full model name (no trimming): {model}")
    
    config = {
        "api_key": api_key,
        "base_url": base_url,
        "model": model,
        "temperature": temperature,
    }
    
    logger.info(f"   ✅ Final config: model={model}, base_url={base_url}, api_key={'***' + api_key[-4:] if api_key and len(api_key) > 4 else 'None'}")
    
    return config


def _detect_provider_type(llm: Any, config: Dict[str, Any]) -> LLMProviderType:
    """
    检测 LLM 的提供商类型
    
    优先级：
    1. 检查 LLM 对象的 _llm_config 属性（我们自己创建的 LLM 会有）
    2. 根据模型名称推断
    3. 根据 base_url 推断
    4. 根据 LangChain 类型推断
    
    Args:
        llm: LangChain LLM 实例
        config: 提取的配置字典
        
    Returns:
        LLMProviderType 枚举值
    """
    # 1. 检查是否有我们存储的原始配置
    if hasattr(llm, "_llm_config"):
        llm_config = getattr(llm, "_llm_config")
        if hasattr(llm_config, "provider"):
            provider = llm_config.provider
            logger.debug(f"✅ Provider detected from _llm_config: {provider}")
            return provider
    
    # 2. 根据模型名称推断
    model = config.get("model", "").lower()
    if "deepseek" in model:
        logger.debug(f"✅ Provider detected from model name: deepseek")
        return LLMProviderType.DEEPSEEK
    elif "claude" in model:
        logger.debug(f"✅ Provider detected from model name: claude")
        return LLMProviderType.CLAUDE
    elif "gpt" in model or "o1" in model:
        logger.debug(f"✅ Provider detected from model name: openai")
        return LLMProviderType.OPENAI
    
    # 3. 根据 base_url 推断
    base_url = config.get("base_url", "")
    if base_url:
        base_url_lower = base_url.lower()
        if "deepseek" in base_url_lower:
            logger.debug(f"✅ Provider detected from base_url: deepseek")
            return LLMProviderType.DEEPSEEK
        elif "anthropic" in base_url_lower:
            logger.debug(f"✅ Provider detected from base_url: claude")
            return LLMProviderType.CLAUDE
        elif "openai" in base_url_lower or "azure" in base_url_lower:
            logger.debug(f"✅ Provider detected from base_url: openai")
            return LLMProviderType.OPENAI
    
    # 4. 根据 LangChain 类型推断
    llm_type = type(llm).__name__
    if "Anthropic" in llm_type or "Claude" in llm_type:
        logger.debug(f"✅ Provider detected from class name: claude")
        return LLMProviderType.CLAUDE
    elif "Azure" in llm_type:
        logger.debug(f"✅ Provider detected from class name: azure_openai")
        return LLMProviderType.AZURE_OPENAI
    elif "OpenAI" in llm_type:
        logger.debug(f"✅ Provider detected from class name: openai")
        return LLMProviderType.OPENAI
    
    # 默认使用 OpenAI 兼容接口
    logger.warning(f"⚠️  Could not detect provider, defaulting to OpenAI-compatible")
    return LLMProviderType.OPENAI


def _create_browser_use_llm(llm: Any):
    """
    根据 LangChain LLM 创建 browser-use 的 LLM wrapper
    
    browser-use 有自己的 LLM wrapper，需要根据 provider 类型转换。
    
    Args:
        llm: LangChain LLM 实例
        
    Returns:
        browser-use 兼容的 LLM 实例
    """
    # 1. 提取配置
    config = _extract_llm_config(llm)
    
    # 2. 检测提供商类型
    provider = _detect_provider_type(llm, config)
    
    logger.info(f"🔄 Converting LangChain LLM to browser-use LLM")
    logger.info(f"   Provider: {provider.value}")
    logger.info(f"   Model: {config.get('model')}")
    logger.debug(f"   Base URL: {config.get('base_url')}")
    logger.debug(f"   API Key: {config.get('api_key')[:10] if config.get('api_key') else 'None'}...")
    
    try:
        # 3. 根据 provider 类型创建对应的 browser-use LLM
        if provider == LLMProviderType.DEEPSEEK:
            # DeepSeek: 使用 browser_use.llm.deepseek.chat.ChatDeepSeek
            try:
                from browser_use.llm.deepseek.chat import ChatDeepSeek as BrowserChatDeepSeek
            except ImportError:
                # 如果上面的导入失败，尝试旧版本的导入方式
                logger.warning("⚠️  Could not import ChatDeepSeek from browser_use.llm.deepseek.chat, trying OpenAI-compatible interface")
                from browser_use import ChatOpenAI as BrowserChatOpenAI
                fallback_base_url = config.get("base_url") or "https://api.deepseek.com/v1"
                logger.info(f"   Fallback to ChatOpenAI with:")
                logger.info(f"   - model: {config['model']}")
                logger.info(f"   - base_url: {fallback_base_url}")
                logger.info(f"   - api_key: ***{config['api_key'][-4:] if config.get('api_key') else 'None'}")
                return BrowserChatOpenAI(
                    model=config["model"],
                    api_key=config["api_key"],
                    base_url=fallback_base_url,
                    temperature=config.get("temperature", 0.0),
                )
            
            # 构建 DeepSeek 参数
            deepseek_kwargs = {
                "model": config["model"],
                "api_key": config["api_key"],
                "temperature": config.get("temperature", 0.0),
            }
            
            # 添加 base_url（如果提供了）
            if config.get("base_url"):
                deepseek_kwargs["base_url"] = config["base_url"]
                logger.info(f"   📍 Using custom base_url: {config['base_url']}")
            else:
                logger.info(f"   📍 Using default DeepSeek base_url (not set, will use ChatDeepSeek default)")
            
            logger.info(f"✅ Creating browser-use ChatDeepSeek with parameters:")
            logger.info(f"   - model: {deepseek_kwargs['model']}")
            logger.info(f"   - base_url: {deepseek_kwargs.get('base_url', 'https://api.deepseek.com/v1 (default)')}")
            logger.info(f"   - api_key: ***{deepseek_kwargs['api_key'][-4:] if deepseek_kwargs.get('api_key') else 'None'}")
            logger.info(f"   - temperature: {deepseek_kwargs['temperature']}")
            
            return BrowserChatDeepSeek(**deepseek_kwargs)
        
        elif provider == LLMProviderType.CLAUDE:
            # Claude: 使用 browser_use.ChatAnthropic
            from browser_use import ChatAnthropic as BrowserChatAnthropic
            
            logger.info(f"✅ Creating browser-use ChatAnthropic")
            return BrowserChatAnthropic(
                model=config.get("model", "claude-3-5-sonnet-20241022"),
                api_key=config["api_key"],
            )
        
        elif provider in (LLMProviderType.OPENAI, LLMProviderType.AZURE_OPENAI, LLMProviderType.CUSTOM):
            # OpenAI / Azure / Custom: 使用 browser_use.ChatOpenAI
            from browser_use import ChatOpenAI as BrowserChatOpenAI
            
            openai_kwargs = {
                "model": config.get("model", "gpt-4"),
                "api_key": config["api_key"],
                "temperature": config.get("temperature", 0.0),
            }
            
            # 添加 base_url（如果有）
            if config.get("base_url"):
                openai_kwargs["base_url"] = config["base_url"]
            
            logger.info(f"✅ Creating browser-use ChatOpenAI")
            return BrowserChatOpenAI(**openai_kwargs)
        
        else:
            # 其他类型：尝试 OpenAI 兼容接口
            logger.warning(f"⚠️  Unknown provider {provider}, trying OpenAI-compatible interface")
            from browser_use import ChatOpenAI as BrowserChatOpenAI
            
            return BrowserChatOpenAI(
                model=config.get("model", "gpt-4"),
                api_key=config["api_key"],
                base_url=config.get("base_url"),
                temperature=config.get("temperature", 0.0),
            )
    
    except Exception as e:
        logger.error(f"❌ Failed to convert LLM: {e}")
        import traceback
        logger.debug(traceback.format_exc())
        raise ValueError(f"Failed to create browser-use LLM for provider {provider.value}: {str(e)}")


def create_browser_use_tool(llm: Any, **browser_config):
    """
    创建 browser-use 工具的工厂函数
    
    Args:
        llm: LangChain LLM 实例（将被转换为 browser-use 的 LLM wrapper）
        **browser_config: 浏览器配置参数
            - headless: bool = False, 是否无头模式
            - disable_security: bool = False, 是否禁用安全特性
            - window_w: int = 1280, 窗口宽度
            - window_h: int = 1100, 窗口高度
            - save_recording_path: Optional[str] = None, 录屏保存路径
    
    Returns:
        LangChain tool 函数
        
    Examples:
        >>> from langchain_openai import ChatOpenAI
        >>> llm = ChatOpenAI(model="gpt-4")
        >>> browser_tool = create_browser_use_tool(llm, headless=False)
        >>> result = await browser_tool.ainvoke({"task": "访问 github.com 并获取首页内容"})
    """
    
    # 转换 LLM 为 browser-use 的 wrapper
    browser_llm = _create_browser_use_llm(llm)
    
    # 浏览器配置
    config = {
        "headless": browser_config.get("headless", False),
        "disable_security": browser_config.get("disable_security", False),
        "window_w": browser_config.get("window_w", 1280),
        "window_h": browser_config.get("window_h", 1100),
        "save_recording_path": browser_config.get("save_recording_path", None),
    }
    
    @tool
    async def browser_use(task: str) -> str:
        """
        使用 AI 控制浏览器执行自动化任务
        
        此工具可以：
        - 访问网站并提取信息
        - 填写表单和执行网页操作
        - 网页导航和搜索
        - 数据抓取和信息收集
        - 截图和记录操作过程
        
        Args:
            task: 要执行的浏览器任务描述，例如：
                - "访问 github.com/browser-use/browser-use，获取项目的 star 数量"
                - "在 Google 上搜索 'Python web scraping'，获取前 3 个结果"
                - "访问股票网站，获取特斯拉的最新股价"
        
        Returns:
            任务执行结果的文本描述
        """
        try:
            from browser_use import Agent, Browser
            
            logger.info(f"🌐 Starting browser task: {task[:100]}...")
            
            # 创建浏览器实例 (Browser 在 0.7.10 中已经包含配置)
            browser = Browser(
                headless=config["headless"],
                disable_security=config["disable_security"],
            )
            
            # 创建 Agent（使用 browser-use 的 LLM wrapper）
            agent = Agent(
                task=task,
                llm=browser_llm,
                browser=browser,
            )
            
            # 执行任务
            try:
                result = await agent.run()
            except Exception as e:
                logger.error(f"❌ browser-use agent.run() failed: {type(e).__name__}: {str(e)}")
                import traceback
                logger.debug(f"Traceback: {traceback.format_exc()}")
                raise
            
            # 保存录屏（如果配置了）
            if config["save_recording_path"]:
                try:
                    history = agent.history()
                    save_path = config["save_recording_path"]
                    logger.info(f"💾 Saving recording to: {save_path}")
                    # 这里可以添加保存逻辑
                except Exception as e:
                    logger.warning(f"Failed to save recording: {e}")
            
            logger.info(f"✅ Browser task completed successfully")
            
            # 返回结果
            return str(result)
            
        except ImportError as e:
            error_msg = (
                "❌ browser-use is not installed.\n"
                "Please install it with:\n"
                "  uv pip install browser-use playwright\n"
                "  uvx playwright install chromium --with-deps --no-shell"
            )
            logger.error(error_msg)
            return error_msg
            
        except Exception as e:
            error_msg = f"❌ Browser task failed: {str(e)}"
            logger.error(error_msg)
            return error_msg
    
    # 存储配置信息到 tool 的元数据
    browser_use._browser_config = config
    browser_use._browser_llm = browser_llm
    browser_use._original_llm = llm
    
    return browser_use


def create_browser_use_with_context_tool(llm: Any, **browser_config):
    """
    创建带上下文的 browser-use 工具（支持多步骤任务）
    
    这个版本支持在同一个浏览器会话中执行多个步骤，保持页面状态。
    适合需要连续操作的场景，如：登录、导航、填表单等。
    
    Args:
        llm: LangChain LLM 实例
        **browser_config: 浏览器配置参数
    
    Returns:
        LangChain tool 函数
    """
    
    # 转换 LLM 为 browser-use 的 wrapper
    browser_llm = _create_browser_use_llm(llm)
    
    # 共享的浏览器实例
    browser_instance = {"browser": None, "agent": None}
    
    @tool
    async def browser_use_with_context(
        task: str, 
        action: str = "execute"
    ) -> str:
        """
        使用 AI 控制浏览器执行任务（支持会话保持）
        
        Args:
            task: 要执行的浏览器任务描述
            action: 操作类型
                - "execute": 执行任务（默认）
                - "reset": 重置浏览器会话
                - "close": 关闭浏览器
        
        Returns:
            任务执行结果
        """
        try:
            from browser_use import Agent, Browser
            
            # 处理特殊操作
            if action == "close":
                if browser_instance["browser"]:
                    # await browser_instance["browser"].close()
                    browser_instance["browser"] = None
                    browser_instance["agent"] = None
                    logger.info("🔒 Browser closed")
                return "Browser closed successfully"
            
            if action == "reset":
                if browser_instance["browser"]:
                    # await browser_instance["browser"].close()
                    browser_instance["browser"] = None
                    browser_instance["agent"] = None
                logger.info("🔄 Browser session reset")
                return "Browser session reset successfully"
            
            # 创建或复用浏览器实例
            if browser_instance["browser"] is None:
                browser_instance["browser"] = Browser(
                    headless=browser_config.get("headless", False),
                    disable_security=browser_config.get("disable_security", False),
                )
                logger.info("🌐 New browser instance created")
            
            # 执行任务
            logger.info(f"▶️  Executing task: {task[:100]}...")
            
            agent = Agent(
                task=task,
                llm=browser_llm,
                browser=browser_instance["browser"],
            )
            
            result = await agent.run()
            logger.info(f"✅ Task completed")
            
            return str(result)
            
        except Exception as e:
            error_msg = f"❌ Browser task failed: {str(e)}"
            logger.error(error_msg)
            return error_msg
    
    return browser_use_with_context


# 便捷函数：创建默认配置的 browser-use 工具
def get_browser_use_tool(llm: Any, headless: bool = False) -> Any:
    """
    快速创建默认配置的 browser-use 工具
    
    Args:
        llm: LangChain LLM 实例
        headless: 是否使用无头模式（默认 False，显示浏览器窗口）
    
    Returns:
        browser-use tool
    
    Examples:
        >>> from langchain_openai import ChatOpenAI
        >>> llm = ChatOpenAI(model="gpt-4")
        >>> browser_tool = get_browser_use_tool(llm)
        >>> 
        >>> # 在 Agent 中使用
        >>> tools = [browser_tool, other_tool]
        >>> agent = create_react_agent(model=llm, tools=tools)
    """
    return create_browser_use_tool(llm, headless=headless)


# 工具配置辅助类
class BrowserUseToolConfig:
    """Browser Use Tool 配置类"""
    
    @staticmethod
    def default() -> Dict[str, Any]:
        """默认配置"""
        return {
            "headless": False,
            "disable_security": False,
            "window_w": 1280,
            "window_h": 1100,
            "save_recording_path": None,
        }
    
    @staticmethod
    def headless() -> Dict[str, Any]:
        """无头模式配置（服务器环境）"""
        return {
            "headless": True,
            "disable_security": False,
            "window_w": 1920,
            "window_h": 1080,
            "save_recording_path": None,
        }
    
    @staticmethod
    def debug() -> Dict[str, Any]:
        """调试模式配置（慢速、可见窗口）"""
        return {
            "headless": False,
            "disable_security": True,
            "window_w": 1280,
            "window_h": 1100,
            "save_recording_path": "./browser_recordings/",
        }


__all__ = [
    "create_browser_use_tool",
    "create_browser_use_with_context_tool",
    "get_browser_use_tool",
    "BrowserUseToolConfig",
] 