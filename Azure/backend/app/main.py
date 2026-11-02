import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.api.routes import router
from app.core.config import get_settings
from app.core.errors import PlatformError, platform_error_handler

logging.basicConfig(level=get_settings().log_level)


@asynccontextmanager
async def lifespan(_: FastAPI):
    yield


app = FastAPI(title=get_settings().app_name, version="0.1.0", lifespan=lifespan)
app.add_exception_handler(PlatformError, platform_error_handler)
app.include_router(router)

