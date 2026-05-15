import os

from fastapi import FastAPI
from nicegui import app, ui

from config import config
from core.auth_middleware import AuthMiddleware
from database import init_db
from ui_login import router as login_router

fastapi_app = FastAPI(title=config.APP_TITLE)

init_db()

from database import get_db
from core.models import Org

with get_db() as db:
    root = db.query(Org).filter(Org.org_type == "root").first()
    if not root:
        root = Org(name="系统根组织", org_type="root")
        db.add(root)
        db.commit()

app.add_middleware(AuthMiddleware)

upload_dir = config.absolute_upload_dir
os.makedirs(upload_dir, exist_ok=True)
app.add_static_files("/static/uploads", upload_dir)

app.include_router(login_router)

from pyq.views import router as pyq_router
from admin.views import router as admin_router

app.include_router(pyq_router)
app.include_router(admin_router)


@ui.page("/")
async def index():
    from core.auth import AuthManager

    if not AuthManager.is_authenticated():
        ui.navigate.to("/login")
    else:
        ui.navigate.to("/home")


ui.run_with(
    fastapi_app,
    title=config.APP_TITLE,
    storage_secret=config.SECRET_KEY,
    mount_path="/",
)
