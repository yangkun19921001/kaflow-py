# ============================================================================
# KaFlow-Py Dockerfile
# 基于配置驱动的 AI Agent 开发框架
# ============================================================================

FROM ghcr.io/astral-sh/uv:python3.12-bookworm

# Install uv
COPY --from=ghcr.io/astral-sh/uv:latest /uv /bin/uv

# 设置维护者信息
LABEL maintainer="DevYK <yang1001yk@gmail.com>"
LABEL description="KaFlow-Py - Configuration-driven AI Agent Development Framework"
LABEL version="1.0.0"

# 设置工作目录
WORKDIR /app

# 设置环境变量
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    KAFLOW_HOST=0.0.0.0 \
    KAFLOW_PORT=8102 \
    KAFLOW_LOG_LEVEL=info \
    PLAYWRIGHT_BROWSERS_PATH=/ms-playwright \
    PLAYWRIGHT_SKIP_BROWSER_DOWNLOAD=0

# 安装系统依赖和 Playwright 浏览器依赖
RUN apt-get update && apt-get install -y --no-install-recommends \
    wget \
    gnupg \
    ca-certificates \
    fonts-liberation \
    libasound2 \
    libatk-bridge2.0-0 \
    libatk1.0-0 \
    libatspi2.0-0 \
    libcups2 \
    libdbus-1-3 \
    libdrm2 \
    libgbm1 \
    libgtk-3-0 \
    libnspr4 \
    libnss3 \
    libwayland-client0 \
    libxcomposite1 \
    libxdamage1 \
    libxfixes3 \
    libxkbcommon0 \
    libxrandr2 \
    xdg-utils \
    && rm -rf /var/lib/apt/lists/*

# 预缓存依赖（利用 Docker 缓存层）
RUN --mount=type=cache,target=/root/.cache/uv \
    --mount=type=bind,source=uv.lock,target=uv.lock \
    --mount=type=bind,source=pyproject.toml,target=pyproject.toml \
    uv sync --locked --no-install-project

# 复制应用代码
COPY . /app

# 安装应用依赖
RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --locked

# 安装 Playwright 浏览器（Chromium）
# 创建浏览器目录并设置权限
RUN mkdir -p /ms-playwright && \
    chmod -R 755 /ms-playwright

# 先安装系统依赖，再安装浏览器
RUN uv run playwright install-deps chromium

# 安装 Chromium 浏览器
RUN uv run playwright install chromium

# 验证浏览器安装
RUN uv run python -c "from playwright.sync_api import sync_playwright; p = sync_playwright().start(); print('Browser installed:', p.chromium.executable_path); p.stop()"

# 创建日志目录
RUN mkdir -p /app/logs

# 暴露端口
EXPOSE 8102

# 健康检查
HEALTHCHECK --interval=30s --timeout=10s --start-period=40s --retries=3 \
    CMD curl -f http://localhost:8102/health || exit 1

# 启动命令
CMD ["uv", "run", "python", "server.py"]
