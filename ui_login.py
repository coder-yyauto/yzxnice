import logging

from nicegui import APIRouter, app, ui
from starlette.requests import Request

from core.auth import AuthManager
from core.security import CaptchaManager

logger = logging.getLogger(__name__)

router = APIRouter()


@router.page("/login")
async def login_page(request: Request):
    if AuthManager.is_authenticated():
        ui.navigate.to("/home")
        return

    expired = request.query_params.get("reason") == "expired"

    with ui.column().classes("w-full min-h-screen items-center justify-center bg-gradient-to-br from-blue-50 to-indigo-100"):
        with ui.card().classes("w-96 p-8 shadow-xl"):
            ui.label("多学校朋友圈教学系统").classes("text-xl font-bold text-center mb-6 text-blue-700")

            if expired:
                ui.label("登录已过期，请重新登录").classes("text-amber-600 text-sm mb-4 text-center")

            username_input = (
                ui.input(label="用户名", placeholder="请输入用户名")
                .classes("w-full mb-3")
                .props("outlined dense")
            )
            password_input = (
                ui.input(label="密码", placeholder="请输入密码", password=True)
                .classes("w-full mb-3")
                .props("outlined dense type=password")
            )

            captcha_state = {"id": None}

            def refresh_captcha():
                captcha_id, _, image_data = CaptchaManager.generate()
                captcha_state["id"] = captcha_id
                captcha_img.set_source(image_data)

            with ui.row().classes("w-full items-center gap-3 mb-3"):
                captcha_input = (
                    ui.input(label="验证码", placeholder="请输入验证码")
                    .classes("w-32")
                    .props("outlined dense maxlength=4")
                )
                captcha_img = ui.image().classes("w-28 h-10 rounded cursor-pointer")
                ui.button(icon="refresh", on_click=refresh_captcha).props("flat dense")

            captcha_img.on("click", refresh_captcha)

            error_label = ui.label("").classes("text-red-500 text-sm mb-2 hidden")

            def handle_login():
                username = username_input.value.strip()
                password = password_input.value
                captcha = captcha_input.value.strip()

                if not username:
                    error_label.set_text("请输入用户名")
                    error_label.classes(remove="hidden")
                    return
                if not password:
                    error_label.set_text("请输入密码")
                    error_label.classes(remove="hidden")
                    return
                if not captcha:
                    error_label.set_text("请输入验证码")
                    error_label.classes(remove="hidden")
                    return

                if captcha_state["id"] and not CaptchaManager.verify(captcha_state["id"], captcha):
                    error_label.set_text("验证码错误")
                    error_label.classes(remove="hidden")
                    refresh_captcha()
                    return

                try:
                    submit_btn.props("loading")
                    user_info = AuthManager.login(username=username, password=password)
                    AuthManager.set_session(user_info)
                    ui.notify("登录成功", type="positive")
                    ui.navigate.to("/home")
                except ValueError as e:
                    error_label.set_text(str(e))
                    error_label.classes(remove="hidden")
                    refresh_captcha()
                    logger.warning("登录验证失败: %s", e)
                except Exception as e:
                    error_label.set_text(f"登录失败: {e}")
                    error_label.classes(remove="hidden")
                    refresh_captcha()
                    logger.error("登录异常", exc_info=True)
                finally:
                    submit_btn.props(remove="loading")

            submit_btn = ui.button("登录", on_click=handle_login).classes("w-full").props("color=primary")

            refresh_captcha()
