# KaFlow-Py

<div align="center">

![KaFlow-Py Logo](https://img.shields.io/badge/KaFlow--Py-v1.0.0-blue)
![Python](https://img.shields.io/badge/Python-3.13+-green)
![LangGraph](https://img.shields.io/badge/LangGraph-0.6.7+-orange)
![License](https://img.shields.io/badge/License-MIT-yellow)

**基于配置驱动的 AI Agent 轻量级开发框架**

[English](./README_EN.md) | 简体中文

</div>

## 📖 简介

KaFlow-Py 是一个**配置驱动**的 AI Agent 可视化开发框架，灵感来源于 n8n、Dify 等低代码平台。通过简单的 YAML 配置文件定义节点和连线，即可自动生成对应的 LangGraph 执行图，无需编写复杂代码。

### 核心特性

- 🎯 **配置驱动** - 通过 YAML 配置即可构建复杂的 AI Agent 工作流
- 🔧 **模块化设计** - 支持多种节点类型（Agent、Tool、MCP 等）
- 🚀 **开箱即用** - 内置多个常用场景模板（聊天、翻译、搜索、浏览器自动化等）
- 🔌 **MCP 协议支持** - 完整支持 Model Context Protocol，轻松集成外部工具服务
- 📊 **流式输出** - 基于 SSE 的实时流式响应
- 🎨 **可视化界面** - 配套 Web 界面，支持场景选择和实时对话
- 🐳 **容器化部署** - 提供完整的 Docker 部署方案

### 技术栈

- **AI 框架**: LangChain 0.3+ / LangGraph 0.6+
- **大模型**: 支持 OpenAI、Anthropic、DeepSeek 等主流 LLM
- **协议支持**: MCP (Model Context Protocol) 1.0+
- **Web 框架**: FastAPI + Uvicorn
- **浏览器自动化**: Playwright + Browser-Use

## 🏗️ 架构设计

### 整体架构图

```
┌────────────────────────────────────────────────────────────────────────────┐
│                          KaFlow-Py 整体架构                                 │
└────────────────────────────────────────────────────────────────────────────┘

┌────────────────────────────────────────────────────────────────────────────┐
│                         前端界面层 (Frontend Layer)                         │
├────────────────────────────────────────────────────────────────────────────┤
│  ┌──────────────┐   ┌──────────────┐   ┌──────────────┐                   │
│  │ 场景选择器   │   │  聊天界面    │   │ 流式输出     │                   │
│  │ Scenario     │   │  Chat UI     │   │ SSE Stream   │                   │
│  │ Selector     │   │              │   │              │                   │
│  └──────────────┘   └──────────────┘   └──────────────┘                   │
│                                                                             │
│  技术：React 19 + TypeScript + Ant Design                                 │
└────────────────────────────────────────────────────────────────────────────┘
                                    │
                                    │ HTTP/SSE
                                    ▼
┌────────────────────────────────────────────────────────────────────────────┐
│                         API 服务层 (API Layer)                              │
├────────────────────────────────────────────────────────────────────────────┤
│  ┌──────────────┐   ┌──────────────┐   ┌──────────────┐                    │
│  │ /api/chat    │   │ /api/configs │   │ /health      │                    │
│  │ /stream      │   │              │   │ /version     │                    │
│  └──────────────┘   └──────────────┘   └──────────────┘                    │
│                                                                            │
│  技术：FastAPI + Uvicorn + CORS                                             │
└────────────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌────────────────────────────────────────────────────────────────────────────┐
│                       配置管理层 (Config Management)                         │
├────────────────────────────────────────────────────────────────────────────┤
│  ┌──────────────┐   ┌──────────────┐   ┌──────────────┐                    │
│  │ YAML Parser  │   │ Config Cache │   │ Hot Reload   │                    │
│  │ 配置解析器     │   │ 配置缓存      │   │ 热更新        │                    │
│  └──────────────┘   └──────────────┘   └──────────────┘                    │
│                                                                            │
│  特性：按需加载、配置验证、Schema 校验                                          │
└────────────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌────────────────────────────────────────────────────────────────────────────┐
│                       图构建层 (Graph Building Layer)                       │
├────────────────────────────────────────────────────────────────────────────┤
│  ┌──────────────┐   ┌──────────────┐   ┌──────────────┐                    │
│  │ Auto Builder │   │ Node Factory │   │ Edge Manager │                    │
│  │ 自动构建器   │   │ 节点工厂     │   │ 边管理器     │                        │
│  └──────────────┘   └──────────────┘   └──────────────┘                    │
│                                                                            │
│  核心：Protocol Parser → Graph Builder → LangGraph Compiler                 │
└────────────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌────────────────────────────────────────────────────────────────────────────┐
│                       节点执行层 (Node Execution Layer)                     │
├────────────────────────────────────────────────────────────────────────────┤
│                                                                            │
│  ┌────────────────────────────────────────────────────────────────────┐   │
│  │ Agent 节点 (Agent Nodes)                                            │   │
│  ├────────────────────────────────────────────────────────────────────┤   │
│  │ • ReAct Agent    • Simple Agent    • Custom Agent                  │   │
│  └────────────────────────────────────────────────────────────────────┘   │
│                                                                             │
│  ┌────────────────────────────────────────────────────────────────────┐   │
│  │ Tool 节点 (Tool Nodes)                                              │   │
│  ├────────────────────────────────────────────────────────────────────┤   │
│  │ • File Operations  • Browser    • Search    • SSH Remote Exec      │   │
│  └────────────────────────────────────────────────────────────────────┘   │
│                                                                             │
│  ┌────────────────────────────────────────────────────────────────────┐   │
│  │ MCP 节点 (MCP Nodes)                                                │   │
│  ├────────────────────────────────────────────────────────────────────┤   │
│  │ • Remote Exec                   • External Services                │   │
│  └────────────────────────────────────────────────────────────────────┘   │
│                                                                             │
│  ┌────────────────────────────────────────────────────────────────────┐   │
│  │ 浏览器节点 (Browser Nodes)                                          │   │
│  ├────────────────────────────────────────────────────────────────────┤   │
│  │ • Browser Use Agent  • Web Automation  • Data Extraction           │   │
│  └────────────────────────────────────────────────────────────────────┘   │
│                                                                             │
└────────────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌────────────────────────────────────────────────────────────────────────────┐
│                       执行引擎层 (Execution Engine)                         │
├────────────────────────────────────────────────────────────────────────────┤
│  ┌──────────────┐   ┌──────────────┐   ┌──────────────┐                   │
│  │ LangGraph    │   │ State Manager│   │ Event System │                   │
│  │ 图执行引擎   │   │ 状态管理     │   │ 事件系统     │                   │
│  └──────────────┘   └──────────────┘   └──────────────┘                   │
│                                                                             │
│  ┌──────────────┐   ┌──────────────┐   ┌──────────────┐                   │
│  │ Memory Store │   │ Checkpointer │   │ Stream Output│                   │
│  │ 记忆存储     │   │ 检查点       │   │ 流式输出     │                   │
│  └──────────────┘   └──────────────┘   └──────────────┘                   │
│                                                                             │
│  特性：动态路由、条件跳转、并行执行、错误恢复                            │
└────────────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌────────────────────────────────────────────────────────────────────────────┐
│                       基础服务层 (Foundation Services)                       │
├────────────────────────────────────────────────────────────────────────────┤
│                                                                            │
│  ┌───────────────────────────────┐   ┌───────────────────────────────┐     │
│  │ LLM Services                  │   │ Vector Database               │     │
│  ├───────────────────────────────┤   ├───────────────────────────────┤     │
│  │ • OpenAI                      │   │ •                             │     │
│  │ • Anthropic (Claude)          │   │ •                             │     │
│  │ • DeepSeek                    │   │ •                             │     │
│  └───────────────────────────────┘   └───────────────────────────────┘     │
│                                                                            │
│  ┌───────────────────────────────┐   ┌───────────────────────────────┐     │
│  │ MCP Protocol                  │   │ External Services             │     │
│  ├───────────────────────────────┤   ├───────────────────────────────┤     │
│  │ • MCP Client                  │   │ • RAGFlow SDK                 │     │
│  │ • Tool Discovery              │   │ • Browser-Use                 │     │
│  │ • SSE Transport               │   │ • DuckDuckGo Search           │     │
│  └───────────────────────────────┘   └───────────────────────────────┘     │
│                                                                             │
└────────────────────────────────────────────────────────────────────────────┘
```

### 核心设计理念

#### 配置驱动 (Configuration-Driven)

```yaml
# 示例：简单的聊天机器人配置
id: 4
protocol:
  name: "智能聊天助手"
  version: "1.0.0"

agents:
  chat_agent:
    type: "react_agent"
    llm:
      provider: "deepseek"
      model: "deepseek-v3"
    tools: []

workflow:
  nodes:
    - name: "start_node"
      type: "start"
    - name: "chat_agent"
      type: "agent"
      agent_ref: "chat_agent"
    - name: "end_node"
      type: "end"
  
  edges:
    - from: "start_node"
      to: "chat_agent"
    - from: "chat_agent"
      to: "end_node"
```

## 📦 功能清单

### 节点类型

- `start` - 开始节点
- `end` - 结束节点  
- `agent` - Agent 节点（ReAct Agent、Simple Agent）


### 内置工具

- 📁 文件操作（file_reader, file_writer）
- 💻 系统信息（system_info）
- 🔍 搜索工具（duckduckgo_search）
- 🌐 浏览器自动化（browser_use）
- 🔐 SSH 远程执行（ssh_remote_exec, ssh_batch_exec）支持私钥登录
  - 支持密码认证和公私钥认证
  - 支持批量服务器操作
  - **SSH 服务器端公钥配置步骤**：
    1. **客户端获取公钥**：
       ```bash
       # 在客户端执行，获取公钥内容
       cat ~/.ssh/id_rsa.pub
       ```
    2. **服务端配置 SSH 支持公钥认证**：
       ```bash
       # 编辑 SSH 配置文件
       sudo vim /etc/ssh/sshd_config
       
       # 确保以下配置项已启用
       PubkeyAuthentication yes
       AuthorizedKeysFile .ssh/authorized_keys
       
       # 重启 SSH 服务
       sudo systemctl restart sshd
       ```
    3. **服务端添加客户端公钥**：
       ```bash
       # 在目标用户家目录下创建 .ssh 目录（如果不存在）
       mkdir -p ~/.ssh
       chmod 700 ~/.ssh
       
       # 将客户端公钥添加到 authorized_keys 文件
       echo "客户端公钥内容" >> ~/.ssh/authorized_keys
       chmod 600 ~/.ssh/authorized_keys
       ```



### MCP 协议支持

- ✅ Stdio 传输
- ✅ SSE 传输
- ✅ 工具自动发现
- ✅ 异步调用
- ✅ 错误处理和重试

### 预置场景

1. **智能聊天助手** - 基础聊天机器人
2. **翻译助手** - 多语言翻译
3. **搜索助手** - 联网搜索
4. **浏览器助手** - 浏览器自动化
5. **运维助手** - 设备故障排查（需集成 SSH MCP）

### 记忆
1. **内存**: 通过内存缓存历史消息，为 agent 增加记忆功能，能快速找到上下文，提供优化的交互体验。

## 🚀 快速开始

### 1. 克隆项目

```bash
git clone https://github.com/yangkun19921001/kaflow-py.git
cd kaflow-py
```

### 2. 安装依赖

```bash
# 使用 uv（推荐）
uv sync

```

### 3. 配置环境变量

```bash
# 复制环境变量模板
cp docker/env.example .env

# 编辑 .env 文件，至少配置一个 API Key
# DEEPSEEK_API_KEY=sk-xxx
# OPENAI_API_KEY=sk-xxx
# ANTHROPIC_API_KEY=sk-xxx
```

### 4. 运行

```bash
 
 #目前只测试了 deepseek,需要在yaml 配置 openai 
 export DEEPSEEK_API_KEY="*****" && uv run server.py

```

### 4. Docker 部署（推荐）

#### 准备环境变量

```bash
# 进入 docker 目录
cd docker

# 复制环境变量模板
cp env.example .env

# 编辑 .env 文件，配置至少一个 LLM API Key
vim .env
```

**环境变量配置示例**：
```bash
# 必填：至少配置一个 API Key
DEEPSEEK_API_KEY=sk-your-deepseek-api-key-here
# OPENAI_API_KEY=sk-your-openai-api-key-here
# ANTHROPIC_API_KEY=sk-your-anthropic-api-key-here

# 服务配置（可选，使用默认值）
KAFLOW_HOST=0.0.0.0
KAFLOW_PORT=8102
KAFLOW_LOG_LEVEL=info
```

#### 构建和启动服务

```bash
# 返回项目根目录
cd ..

# 首次部署：构建镜像并启动服务
# --build: 构建镜像（包含浏览器等依赖，需要 5-10 分钟）
# -d: 后台运行
docker compose up --build -d

# 后续启动：直接使用已构建的镜像
docker compose up -d
```

#### 查看服务状态

```bash
# 查看运行状态
docker compose ps

# 查看实时日志（Ctrl+C 退出）
docker compose logs -f

# 查看指定服务日志
docker compose logs -f kaflow-py
```

#### 验证服务

```bash
# 健康检查
curl http://localhost:8102/health

# 查看配置列表
curl http://localhost:8102/api/configs

# 访问 API 文档
open http://localhost:8102/docs
```

#### 停止和清理

```bash
# 停止服务（保留容器）
docker compose stop

# 停止并删除容器
docker compose down

# 停止并删除容器、镜像
docker compose down --rmi all

# 完全清理（包括数据卷）
docker compose down -v --rmi all
```

#### 常用操作

```bash
# 重启服务
docker compose restart

# 查看容器资源使用情况
docker stats kaflow-py

# 进入容器（用于调试）
docker exec -it kaflow-py bash

# 查看浏览器是否安装成功
docker exec -it kaflow-py uv run python -c \
  "from playwright.sync_api import sync_playwright; \
   p = sync_playwright().start(); \
   print('✅ Browser:', p.chromium.executable_path); \
   p.stop()"

# 更新代码后重新构建
docker compose build --no-cache
docker compose up -d
```

#### 故障排查

**问题 1: 端口被占用**
```bash
# 检查端口占用
lsof -i :8102

# 修改端口：编辑 docker-compose.yml
# ports:
#   - "8103:8102"  # 改用其他端口
```

**问题 2: 浏览器启动失败**
```bash
# 确保镜像重新构建（包含浏览器）
docker compose down
docker rmi kaflow-py
docker compose build --no-cache
docker compose up -d
```

**问题 3: API Key 未生效**
```bash
# 检查环境变量
docker compose exec kaflow-py env | grep API_KEY

# 重启服务使环境变量生效
docker compose restart
```


## 📄 License

本项目采用 [MIT License](./LICENSE) 开源协议。

## 🙏 感谢

感谢以下开源项目的支持：

- [LangChain](https://github.com/langchain-ai/langchain) - AI 应用开发框架
- [LangGraph](https://github.com/langchain-ai/langgraph) - 图执行引擎
- [FastAPI](https://github.com/tiangolo/fastapi) - 现代 Web 框架
- [Model Context Protocol](https://modelcontextprotocol.io/) - MCP 协议

---

<div align="center">

**如果觉得项目不错，请给个 ⭐️ Star 支持一下！**

Made with ❤️ by DevYK

</div>
