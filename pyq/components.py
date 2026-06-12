from typing import Any, cast

from nicegui import app, ui


def render_navbar() -> None:
    user_type = app.storage.user.get("user_type", "student")
    nickname = app.storage.user.get("nickname", "")
    display_name = nickname or app.storage.user.get("display_name", "") or app.storage.user.get("username", "")

    has_admin_page = app.storage.user.get("has_admin_page", False)
    has_seat_access = app.storage.user.get("has_seat_access", False)

    with ui.row().classes(
        "w-full h-12 bg-white border-b border-gray-200 px-4 items-center justify-between sticky top-0 z-50"
    ):
        with ui.row().classes("items-center gap-2"):
            ui.icon("school").classes("text-xl text-blue-500")
            ui.label("校园动态").classes("text-lg font-bold text-blue-500")

        with ui.row().classes("items-center gap-2"):
            ui.label(display_name).classes("text-sm text-gray-500")
            ui.button(icon="person", on_click=lambda: _show_my_info()).props("flat dense size=sm color=grey-7").tooltip(
                "我的信息"
            )

            if has_admin_page or has_seat_access or user_type == "admin":
                ui.button(icon="settings", on_click=lambda: ui.navigate.to("/admin")).props(
                    "flat dense size=sm color=grey-7"
                ).tooltip("管理后台")

            ui.button(icon="logout", on_click=_handle_logout).props(
                "flat dense size=sm color=grey-7 icon-only"
            ).tooltip("退出")


def render_admin_navbar(active: str = "") -> None:
    nickname = app.storage.user.get("nickname", "")
    display_name = nickname or app.storage.user.get("display_name", "") or app.storage.user.get("username", "")

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
            ui.button(icon="person", on_click=lambda: _show_my_info()).props("flat dense size=sm color=grey-7").tooltip(
                "我的信息"
            )
            ui.button(icon="logout", on_click=_handle_logout).props(
                "flat dense size=sm color=grey-7 icon-only"
            ).tooltip("退出")

    with ui.row().classes("w-full bg-gray-50 border-b border-gray-200 px-4 gap-2 py-2"):
        user_type = app.storage.user.get("user_type", "")
        if user_type == "admin" or app.storage.user.get("has_admin_page", False):
            _admin_tab("组织管理", "/admin/org", active)
            _admin_tab("用户管理", "/admin/users", active)
            _admin_tab("权限管理", "/admin/roles", active)
        _admin_tab("席位管理", "/admin/seats", active)


def _admin_tab(label: str, url: str, active: str) -> None:
    is_active = active == url
    btn = ui.button(label, on_click=lambda: ui.navigate.to(url)).props("flat dense no-caps")
    if is_active:
        btn.classes("text-blue-600 border-b-2 border-blue-600")
    else:
        btn.classes("text-gray-500")


def _handle_logout() -> None:
    from core.auth import AuthManager

    AuthManager.clear_session()
    ui.notify("已退出登录", type="info")
    ui.navigate.to("/login")


def _show_msg(msg_label: Any, text: str) -> None:
    """Display a message in the dialog's error label."""
    msg_label.set_text(text)
    msg_label.classes(remove="hidden")


def _apply_password_change(u: Any, old_pwd: str, new_pwd: str, confirm_pwd: str, msg_label: Any) -> bool | None:
    """Validate inputs and update the user's password.

    Returns True if the password was changed, False if the user provided no
    password inputs, or None if validation failed (msg_label is updated in that case).
    """
    from core.security import PasswordManager

    if not (old_pwd or new_pwd or confirm_pwd):
        return False
    if not old_pwd:
        _show_msg(msg_label, "请输入当前密码")
        return None
    if not new_pwd:
        _show_msg(msg_label, "请输入新密码")
        return None
    if new_pwd != confirm_pwd:
        _show_msg(msg_label, "两次密码不一致")
        return None
    if len(new_pwd) < 6:
        _show_msg(msg_label, "密码至少6位")
        return None
    if not PasswordManager.verify_password(u.password_hash, old_pwd):
        _show_msg(msg_label, "当前密码错误")
        return None
    u.set_password(new_pwd)
    return True


def _show_my_info() -> None:
    from core.auth import AuthManager
    from core.models import User
    from database import get_db

    user = cast(dict[str, Any], AuthManager.get_current_user())
    with get_db() as db:
        user_obj = db.query(User).filter(User.id == user["user_id"]).first()
        current_nickname = user_obj.nickname if user_obj else ""

    with ui.dialog() as dialog, ui.card().classes("w-96 p-6"):
        ui.label("我的信息").classes("text-lg font-bold mb-4")

        ui.label("昵称").classes("text-sm text-gray-500 mb-1")
        nickname_input = ui.input(placeholder="输入昵称").classes("w-full").props("outlined dense")
        nickname_input.value = current_nickname or ""

        ui.element("div").classes("h-4")
        ui.label("修改密码（留空则不修改）").classes("text-sm text-gray-500 mb-2")

        old_input = ui.input(placeholder="当前密码", password=True).classes("w-full").props("outlined dense")
        new_input = ui.input(placeholder="新密码", password=True).classes("w-full").props("outlined dense")
        confirm_input = ui.input(placeholder="确认新密码", password=True).classes("w-full").props("outlined dense")
        msg_label = ui.label("").classes("text-sm text-red-500 hidden")

        async def do_save() -> None:
            new_nickname = nickname_input.value.strip()
            old_pwd = old_input.value
            new_pwd = new_input.value
            confirm_pwd = confirm_input.value

            with get_db() as db:
                u = db.query(User).filter(User.id == user["user_id"]).first()
                if not u:
                    _show_msg(msg_label, "用户不存在")
                    return

                changed = False
                if new_nickname and new_nickname != (u.nickname or ""):
                    u.nickname = new_nickname
                    changed = True

                pwd_ok = _apply_password_change(u, old_pwd, new_pwd, confirm_pwd, msg_label)
                if pwd_ok is None:
                    return
                if pwd_ok:
                    changed = True

                if not changed:
                    _show_msg(msg_label, "没有变更")
                    return

                db.commit()

            ui.notify("信息已更新", type="positive")
            dialog.close()

        with ui.row().classes("w-full justify-end gap-2 mt-4"):
            ui.button("取消", on_click=dialog.close).props("flat")
            ui.button("保存", on_click=do_save).props("color=primary")

    dialog.open()
