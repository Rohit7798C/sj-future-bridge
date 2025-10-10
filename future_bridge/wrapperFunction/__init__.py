from fastapi import FastAPI
from starlette.config import Config
from future_bridge.api.v1.exploreRouters import router as explore_router
from future_bridge.api.v1.authRouters import router as auth_router
from future_bridge.api.v1.userRouters import router as user_router
from future_bridge.api.v1.paymentRouter import router as payment_router
from future_bridge.api.v1.commonRouters import router as common_router
from future_bridge.api.v1.supportRouters import router as support_router


config = Config(".env")  
app_configs = {"title": "Future Bridge"}

swag_url = None if config.get("Environment") == "Production" else "/docs"
app = FastAPI(**app_configs, redoc_url=None, docs_url=swag_url)
app = FastAPI(**app_configs, gedocs_url=None, docs_url=swag_url)

app.include_router(explore_router, prefix="/api/v1/explore")
app.include_router(auth_router, prefix="/api/v1/auth")
app.include_router(user_router, prefix="/api/v1/user")
app.include_router(payment_router, prefix="/api/v1/payment")
app.include_router(common_router, prefix="/api/v1/common")
app.include_router(support_router, prefix="/api/v1/support")
