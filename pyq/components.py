from nicegui import app, ui


def render_navbar():
    from core.auth import AuthManager

    user_type = app.storage.user.get("user_type", "student")
    is_admin = app.storage.user.get("is_admin", False)
    display_name = app.storage.user.get("display_name", "") or app.storage.user.get("username", "")

    has_admin_page = app.storage.user.get("has_admin_page", False)

    with ui.row().classes(
        "w-full h-12 bg-white border-b border-gray-200 px-4 items-center justify-between sticky top-0 z-50"
    ):
        with ui.row().classes("items-center gap-2"):
            ui.icon("school").classes("text-xl text-blue-500")
            ui.label("校园动态").classes("text-lg font-bold text-blue-500")

        with ui.row().classes("items-center gap-2"):
            ui.label(display_name).classes("text-sm text-gray-500")
            ui.button(icon="lock", on_click=lambda: _show_change_password()).props(
                "flat dense size=sm color=grey-7"
            ).tooltip("修改密码")

            if has_admin_page or user_type == "admin":
                ui.button(icon="settings", on_click=lambda: ui.navigate.to("/admin")).props(
                    "flat dense size=sm color=grey-7"
                ).tooltip("管理后台")

            ui.button(icon="logout", on_click=_handle_logout).props(
                "flat dense size=sm color=grey-7 icon-only"
            ).tooltip("退出")


def render_admin_navbar(active=""):
    from core.auth import AuthManager

    display_name = app.storage.user.get("display_name", "") or app.storage.user.get("username", "")

    with ui.row().classes(
        "w-full h-12 bg-white border-b border-gray-200 px-4 items-center justify-between sticky top-0 z-50"
    ):
        with ui.row().classes("items-center gap-2"):
            ui.button(icon="arrow_back", on_click=lambda: ui.navigate.to("/home")).props(
                "flat dense size=sm color=grey-7"
            ).tooltip("返回朋友圈")
            ui.icon("admin_panel_settings").classes("text-xl text-blue-500")
            ui.label("管理后台").classes("text-lg font-bold text-blue-500")

        with ui.row().classes("items-center gap-2"):
            ui.label(display_name).classes("text-sm text-gray-500")
            ui.button(icon="lock", on_click=lambda: _show_change_password()).props(
                "flat dense size=sm color=grey-7"
            ).tooltip("修改密码")
            ui.button(icon="logout", on_click=_handle_logout).props(
                "flat dense size=sm color=grey-7 icon-only"
            ).tooltip("退出")

    with ui.row().classes("w-full bg-gray-50 border-b border-gray-200 px-4 gap-2 py-2"):
        _admin_tab("组织管理", "/admin/org", active)
        _admin_tab("用户管理", "/admin/users", active)
        _admin_tab("权限管理", "/admin/roles", active)


def _admin_tab(label, url, active):
    is_active = active == url
    btn = ui.button(label, on_click=lambda: ui.navigate.to(url)).props("flat dense no-caps")
    if is_active:
        btn.classes("text-blue-600 border-b-2 border-blue-600")
    else:
        btn.classes("text-gray-500")


def _handle_logout():
    from core.auth import AuthManager

    AuthManager.clear_session()
    ui.notify("已退出登录", type="info")
    ui.navigate.to("/login")


def _show_change_password():
    from core.security import PasswordManager

    with ui.dialog() as dialog, ui.card().classes("w-96 p-6"):
        ui.label("修改密码").classes("text-lg font-bold mb-4")
        old_input = ui.input(label="当前密码", password=True).classes("w-full").props("outlined dense")
        new_input = ui.input(label="新密码", password=True).classes("w-full").props("outlined dense")
        confirm_input = ui.input(label="确认新密码", password=True).classes("w-full").props("outlined dense")
        msg_label = ui.label("").classes("text-sm text-red-500 hidden")

        async def do_change():
            old_pwd = old_input.value
            new_pwd = new_input.value
            confirm_pwd = confirm_input.value

            if not old_pwd or not new_pwd:
                msg_label.set_text("请填写完整")
                msg_label.classes(remove="hidden")
                return
            if new_pwd != confirm_pwd:
                msg_label.set_text("两次密码不一致")
                msg_label.classes(remove="hidden")
                return
            if len(new_pwd) < 6:
                msg_label.set_text("密码至少6位")
                msg_label.classes(remove="hidden")
                return

            from database import get_db
            from core.models import User
            from core.auth import AuthManager

            user = AuthManager.get_current_user()
            with get_db() as db:
                user_obj = db.query(User).filter(User.id == user["user_id"]).first()
                if not user_obj:
                    msg_label.set_text("用户不存在")
                    msg_label.classes(remove="hidden")
                    return
                if not PasswordManager.verify_password(user_obj.password_hash, old_pwd):
                    msg_label.set_text("当前密码错误")
                    msg_label.classes(remove="hidden")
                    return
                user_obj.set_password(new_pwd)
                db.commit()

            ui.notify("密码修改成功", type="positive")
            dialog.close()

        with ui.row().classes("w-full justify-end gap-2 mt-4"):
            ui.button("取消", on_click=dialog.close).props("flat")
            ui.button("确认修改", on_click=do_change).props("color=primary")

    dialog.open()
