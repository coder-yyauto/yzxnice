import time

from fastapi import Request
from fastapi.responses import RedirectResponse
from nicegui import app
from starlette.middleware.base import BaseHTTPMiddleware

from config import config

UNRESTRICTED_ROUTES = {"/", "/login", "/api/uploads"}

STATIC_PREFIXES = (
    "/_nicegui",
    "/static",
    "/favicon",
)

SESSION_MAX_AGE = config.SESSION_EXPIRE_HOURS * 3600


class AuthMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        path = request.url.path
        if path in UNRESTRICTED_ROUTES:
            return await call_next(request)
        if any(path.startswith(prefix) for prefix in STATIC_PREFIXES):
            return await call_next(request)
        if not app.storage.user.get("user_id"):
            return RedirectResponse(f"/login?redirect_to={path}")

        login_time = app.storage.user.get("login_time", 0)
        if login_time and (time.time() - login_time > SESSION_MAX_AGE):
            app.storage.user.clear()
            return RedirectResponse(f"/login?redirect_to={path}&reason=expired")

        return await call_next(request)
