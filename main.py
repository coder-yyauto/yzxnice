from nicegui import ui

from app_factory import create_app
from config import config

create_app()

if __name__ == "__main__":
    ui.run(
        title=config.APP_TITLE,
        port=8080,
        reload=False,
        show=False,
        storage_secret=config.SECRET_KEY,
    )
