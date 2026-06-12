import os
from typing import TYPE_CHECKING, Any

from nicegui import app, ui

from config import config
from core.auth_middleware import AuthMiddleware
from database import get_db, init_db

if TYPE_CHECKING:
    pass


def create_app() -> None:
    """Initialize the NiceGUI app with DB, auth, routes, and static files."""
    init_db()
    _ensure_root_org()

    app.add_middleware(AuthMiddleware)

    upload_dir = config.absolute_upload_dir
    os.makedirs(upload_dir, exist_ok=True)
    app.add_static_files("/static/uploads", upload_dir)

    app.include_router(_get_login_router())

    from admin.views import router as admin_router
    from pyq.views import router as pyq_router

    app.include_router(pyq_router)
    app.include_router(admin_router)

    @ui.page("/")  # type: ignore[misc]
    async def index() -> None:
        from core.auth import AuthManager

        if not AuthManager.is_authenticated():
            ui.navigate.to("/login")
        else:
            ui.navigate.to("/home")


def _get_login_router() -> Any:
    from ui_login import router as login_router

    return login_router


def _ensure_root_org() -> None:
    from core.models import Org

    with get_db() as db:
        root = db.query(Org).filter(Org.org_type == "root").first()
        if not root:
            root = Org(name="系统根组织", org_type="root")
            db.add(root)
            db.commit()
