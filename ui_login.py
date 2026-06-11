import logging

from nicegui import APIRouter, ui
from starlette.requests import Request

from core.auth import AuthManager
from core.security import CaptchaManager, LoginAttemptManager

logger = logging.getLogger(__name__)

router = APIRouter()


def _validate_login_form(username: str, password: str, captcha: str) -> str | None:
    """Return error message if any field is empty, else None."""
    if not username:
        return "请输入用户名"
    if not password:
        return "请输入密码"
    if not captcha:
        return "请输入验证码"
    return None


def _check_login_blocked(username: str, client_ip: str) -> str | None:
    """Return error message if login is blocked, else None."""
    if LoginAttemptManager.is_ip_blocked(client_ip):
        return "请求过于频繁，请15分钟后再试"
    if LoginAttemptManager.is_locked(username):
        remaining = LoginAttemptManager.get_lock_remaining(username)
        minutes = remaining // 60
        return f"密码错误次数过多，请 {minutes} 分 {remaining % 60} 秒后再试"
    return None


@router.page("/login")
async def login_page(request: Request):
    if AuthManager.is_authenticated():
        ui.navigate.to("/home")
        return

    expired = request.query_params.get("reason") == "expired"

    with ui.column().classes(
        "w-full min-h-screen items-center justify-center bg-gradient-to-br from-blue-50 to-indigo-100"
    ), ui.card().classes("w-96 p-8 shadow-xl"):
        ui.label("教学模拟平台").classes("text-xl font-bold text-center mb-6 text-blue-700")

        if expired:
            ui.label("登录已过期，请重新登录").classes("text-amber-600 text-sm mb-4 text-center")

        username_input = ui.input(placeholder="用户名").classes("w-full mb-3").props("outlined dense")
        password_input = (
            ui.input(placeholder="密码", password=True).classes("w-full mb-3").props("outlined dense type=password")
        )

        captcha_state = {"id": None}

        def refresh_captcha():
            captcha_id, _, image_data = CaptchaManager.generate()
            captcha_state["id"] = captcha_id
            captcha_img.set_source(image_data)

        with ui.row().classes("w-full items-center gap-3 mb-3"):
            captcha_input = ui.input(placeholder="验证码").classes("w-32").props("outlined dense maxlength=4")
            captcha_img = ui.image().classes("w-28 h-10 rounded cursor-pointer")
            ui.button(icon="refresh", on_click=refresh_captcha).props("flat dense")

        captcha_img.on("click", refresh_captcha)

        error_label = ui.label("").classes("text-red-500 text-sm mb-2 hidden")

        def _show_error(msg: str):
            error_label.set_text(msg)
            error_label.classes(remove="hidden")

        def handle_login():
            username = username_input.value.strip()
            password = password_input.value
            captcha = captcha_input.value.strip()

            validation_error = _validate_login_form(username, password, captcha)
            if validation_error:
                _show_error(validation_error)
                return

            client_ip = request.client.host if request.client else ""

            blocked_error = _check_login_blocked(username, client_ip)
            if blocked_error:
                _show_error(blocked_error)
                refresh_captcha()
                return

            if captcha_state["id"] and not CaptchaManager.verify(captcha_state["id"], captcha):
                _show_error("验证码错误")
                refresh_captcha()
                return

            try:
                submit_btn.props("loading")
                user_info = AuthManager.login(username=username, password=password)
                LoginAttemptManager.reset(username)
                AuthManager.set_session(user_info)
                ui.notify("登录成功", type="positive")
                ui.navigate.to("/home")
            except ValueError as e:
                remaining = LoginAttemptManager.record_failure(username, client_ip)
                msg = f"{e}，还剩 {remaining} 次尝试机会" if remaining > 0 else "密码错误次数过多，请 15 分钟后再试"
                _show_error(msg)
                refresh_captcha()
                logger.warning("登录验证失败: user=%s", username)
            except Exception as e:
                _show_error(f"登录失败: {e}")
                refresh_captcha()
                logger.error("登录异常", exc_info=True)
            finally:
                submit_btn.props(remove="loading")

        submit_btn = ui.button("登录", on_click=handle_login).classes("w-full").props("color=primary")

        refresh_captcha()
