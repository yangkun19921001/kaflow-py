# ============================================================================
# KaFlow-Py Dockerfile
# 基于配置驱动的 AI Agent 开发框架
# ============================================================================

FROM ghcr.io/astral-sh/uv:python3.13-bookworm

# Install uv (already included in base image)
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
    KAFLOW_PORT=8101 \
    KAFLOW_RELOAD=false \
    KAFLOW_LOG_LEVEL=info \
    PLAYWRIGHT_BROWSERS_PATH=/ms-playwright \
    PLAYWRIGHT_SKIP_BROWSER_DOWNLOAD=0 \
    UV_PYTHON=3.13

# 使用国内镜像源（提高下载速度和稳定性）
RUN sed -i 's/deb.debian.org/mirrors.aliyun.com/g' /etc/apt/sources.list.d/debian.sources || \
    sed -i 's/deb.debian.org/mirrors.ustc.edu.cn/g' /etc/apt/sources.list || true

# 安装系统依赖和 Playwright 浏览器依赖（带重试机制）
RUN apt-get update && \
    apt-get install -y --no-install-recommends --fix-missing \
    wget \
    vim \
    curl \
    && rm -rf /var/lib/apt/lists/*

# 配置 PyPI 国内镜像源（提高下载速度）
RUN mkdir -p /root/.config/pip && \
    echo "[global]" > /root/.config/pip/pip.conf && \
    echo "index-url = https://mirrors.aliyun.com/pypi/simple/" >> /root/.config/pip/pip.conf && \
    echo "trusted-host = mirrors.aliyun.com" >> /root/.config/pip/pip.conf && \
    echo "timeout = 120" >> /root/.config/pip/pip.conf

# 🎯 优化构建缓存：先复制依赖文件
# 只有当 pyproject.toml 或 uv.lock 改变时才重新安装依赖
COPY pyproject.toml uv.lock ./
COPY src ./src
COPY server.py ./
COPY .env ./

RUN --mount=type=cache,target=/root/.cache/uv \
    UV_INDEX_URL=https://mirrors.aliyun.com/pypi/simple/ \
    UV_EXTRA_INDEX_URL=https://pypi.tuna.tsinghua.edu.cn/simple \
    UV_HTTP_TIMEOUT=300 \
    uv sync




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
EXPOSE 8101

# 健康检查
HEALTHCHECK --interval=30s --timeout=10s --start-period=40s --retries=3 \
    CMD curl -f http://localhost:8101/health || exit 1

# 启动命令
CMD ["uv", "run", "python", "server.py", "--host", "0.0.0.0", "--port", "8101"] 