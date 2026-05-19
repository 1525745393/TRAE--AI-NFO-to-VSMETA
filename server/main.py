
# NFO to VSMETA Server - 主入口

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager

from .core import (
    ServerConfig,
    error_handler,
    request_logger,
    success_response
)
from .api.v1 import router as api_v1_router
from .websocket import router as websocket_router


@asynccontextmanager
async def lifespan(app: FastAPI):
    print("🚀 服务器启动中...")
    yield
    print("👋 服务器关闭中...")


def create_app(config: ServerConfig = None) -&gt; FastAPI:
    if config is None:
        config = ServerConfig()
    app = FastAPI(
        title=config.app_name,
        description=config.description,
        version=config.version,
        lifespan=lifespan
    )
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    if config.enable_request_logging:
        app.middleware("http")(request_logger)
    app.add_exception_handler(Exception, error_handler)
    app.include_router(api_v1_router)
    app.include_router(websocket_router)

    @app.get("/")
    async def root():
        return success_response(
            data={
                "app_name": config.app_name,
                "version": config.version,
                "status": "running"
            },
            message="欢迎使用 NFO to VSMETA Server!"
        )

    @app.get("/health")
    async def health():
        return success_response(data={"status": "healthy"})

    return app


app = create_app()


if __name__ == "__main__":
    import uvicorn
    config = ServerConfig()
    uvicorn.run(
        "server.main:app",
        host=config.host,
        port=config.port,
        reload=config.debug
    )

