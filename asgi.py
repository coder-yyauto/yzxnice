from fastapi import FastAPI
from nicegui import ui

from app_factory import create_app
from config import config

fastapi_app = FastAPI(title=config.APP_TITLE)

create_app()


ui.run_with(
    fastapi_app,
    title=config.APP_TITLE,
    storage_secret=config.SECRET_KEY,
    mount_path="/",
)
