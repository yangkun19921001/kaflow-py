#!/usr/bin/env python3
"""
KaFlow-Py 服务启动脚本

启动 FastAPI 服务器

Author: DevYK
微信公众号: DevYK
Email: yang1001yk@gmail.com
Github: https://github.com/yangkun19921001
"""

import os
import sys
import uvicorn
from pathlib import Path

# 添加项目根目录到Python路径
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

# 🎯 关键：加载 .env 文件中的环境变量
try:
    from dotenv import load_dotenv
    env_file = project_root / ".env"
    if env_file.exists():
        load_dotenv(env_file)
        print(f"✅ 已加载环境变量文件: {env_file}")
    else:
        print(f"⚠️  未找到 .env 文件: {env_file}")
except ImportError:
    print("⚠️  python-dotenv 未安装，跳过 .env 文件加载")

def main():
    """启动服务"""
    
    # 设置环境变量（如果需要）
    os.environ.setdefault("PYTHONPATH", str(project_root))
    
    # 启动参数
    host = os.getenv("KAFLOW_HOST", "0.0.0.0")
    port = int(os.getenv("KAFLOW_PORT", "8102"))
    # 生产环境默认关闭 reload（避免创建大量监控线程）
    reload = os.getenv("KAFLOW_RELOAD", "false").lower() == "true"
    log_level = os.getenv("KAFLOW_LOG_LEVEL", "info")
    
    print(f"""
🚀 KaFlow-Py 服务启动中...

配置信息:
- 主机: {host}
- 端口: {port}
- 重载: {reload}
- 日志级别: {log_level}
- 项目根目录: {project_root}

访问地址:
- API文档: http://{host}:{port}/docs
- 健康检查: http://{host}:{port}/health
- 配置列表: http://{host}:{port}/api/configs

""")
    
    try:
        # 启动服务
        uvicorn.run(
            "src.server.app:app",
            host=host,
            port=port,
            reload=reload,
            log_level=log_level,
            access_log=True
        )
    except KeyboardInterrupt:
        print("\n👋 KaFlow-Py 服务已停止")
    except Exception as e:
        print(f"❌ 服务启动失败: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main() 