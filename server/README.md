# Server 架构
## 概述
完整的服务器架构，提供API分层设计、WebSocket支持、错误处理和重试机制。

## 目录结构
```
server/
├── __init__.py         # 模块入口
├── app.py              # 主应用
├── core/               # 核心组件
│   ├── __init__.py
│   ├── config.py       # 服务器配置
│   ├── errors.py       # 错误处理
│   ├── retry.py        # 重试机制
│   └── middleware.py   # 中间件
├── api/                # API层
│   ├── __init__.py
│   └── v1/             # API v1
│       ├── __init__.py
│       ├── router.py   # 路由
│       ├── converter.py
│       ├── system.py
│       └── config.py
├── ws/                 # WebSocket
│   ├── __init__.py
│   ├── manager.py      # 连接管理
│   └── handlers.py     # 消息处理
├── services/           # 业务服务层
│   ├── __init__.py
│   └── converter_service.py
└── utils/              # 工具函数
    ├── __init__.py
    └── validators.py
```
