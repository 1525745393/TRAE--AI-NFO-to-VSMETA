
#!/usr/bin/env python3
# 启动服务器脚本

import sys
import os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from server.main import create_app, ServerConfig
import uvicorn


def main():
    config = ServerConfig(
        host="0.0.0.0",
        port=8000,
        debug=True,
        enable_request_logging=True
    )
    app = create_app(config)
    print(f"""
╔═══════════════════════════════════════════════════════════════╗
║                    NFO to VSMETA Server                       ║
║                                                               ║
║  API 文档:    http://{config.host}:{config.port}/docs          ║
║  健康检查:    http://{config.host}:{config.port}/health        ║
║                                                               ║
╚═══════════════════════════════════════════════════════════════╝
    """)
    uvicorn.run(
        app,
        host=config.host,
        port=config.port,
        reload=config.debug
    )


if __name__ == "__main__":
    main()

