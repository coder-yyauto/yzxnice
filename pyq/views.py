import os
import time
import uuid

from nicegui import APIRouter, app, ui

from config import config
from core.auth import AuthManager
from core.models import Org, Post, User
from core.org_utils import (
    get_classes,
    get_grades,
    get_manageable_org_ids,
    get_org_descendants,
    get_school_root,
    get_schools,
    get_user_school,
    get_visible_org_ids,
)
from database import get_db

router = APIRouter()


@router.page("/home")
async def home_page():
    if not AuthManager.is_authenticated():
        ui.navigate.to("/login")
        return

    from pyq.components import render_navbar
    from pyq.card import load_posts, render_post_card

    render_navbar()

    user = AuthManager.get_current_user()
    filter_state = {"org_id": None}
    post_container = None

    with ui.column().classes("w-full min-h-screen bg-[#ededed] items-center"):
        with ui.column().classes("w-full max-w-[428px] px-4 pt-4 pb-8"):

            with ui.row().classes("w-full items-center justify-between mb-3"):
                ui.label("朋友圈").classes("text-lg font-bold text-gray-800")
                with ui.row().classes("items-center gap-2"):
                    ui.button(icon="photo_camera", on_click=lambda: ui.navigate.to("/publish")).props(
                        "flat dense size=sm color=grey-7"
                    ).tooltip("发布动态")

                    if user.get("user_type") in ("teacher", "admin") or user.get("is_admin"):
                        with get_db() as db:
                            if user.get("school_id"):
                                school = db.query(Org).filter(Org.id == user["school_id"]).first()
                                if school:
                                    filter_label = ui.button("选择范围: 全部", on_click=lambda: _open_filter_dialog()).props(
                                        "flat no-caps dense size=sm color=grey-7"
                                    ).classes("text-xs")

                                    def _open_filter_dialog():
                                        with ui.dialog() as dialog, ui.card().classes("w-80 p-4"):
                                            ui.label("选择范围").classes("text-base font-bold mb-3")

                                            with ui.column().classes("w-full gap-0"):
                                                ui.button("全部", on_click=lambda: _do_select([], dialog)).props(
                                                    "flat no-caps dense align=left"
                                                ).classes("w-full text-left")

                                                grades = get_grades(db, school.id)
                                                for grade in grades:
                                                    classes = get_classes(db, grade.id)
                                                    with ui.expansion(grade.name, group="filter_tree").classes("w-full"):
                                                        ui.button(
                                                            f"{grade.name}(全选)",
                                                            on_click=lambda cls=classes: _do_select(
                                                                [c.id for c in cls], dialog
                                                            ),
                                                        ).props("flat no-caps dense align=left color=primary").classes(
                                                            "w-full text-left text-sm"
                                                        )
                                                        for cls_ in classes:
                                                            ui.button(
                                                                cls_.name,
                                                                on_click=lambda c=cls_: _do_select([c.id], dialog),
                                                            ).props("flat no-caps dense align=left").classes(
                                                                "w-full text-left text-sm"
                                                            )
                                        dialog.open()

                                    def _do_select(ids, dialog):
                                        if ids:
                                            filter_state["org_id"] = ids
                                            names = []
                                            for oid in ids:
                                                o = db.query(Org).filter(Org.id == oid).first()
                                                if o:
                                                    names.append(o.name)
                                            first = names[0] if names else ""
                                            if len(names) > 1:
                                                first_name = db.query(Org).filter(Org.id == ids[0]).first()
                                                if first_name:
                                                    parent = db.query(Org).filter(Org.id == first_name.parent_id).first()
                                                    if parent and parent.org_type == "grade":
                                                        filter_label.set_text(f"选择范围: {parent.name}")
                                                    else:
                                                        filter_label.set_text(f"选择范围: {first}等{len(names)}个班")
                                                else:
                                                    filter_label.set_text(f"选择范围: {first}等{len(names)}个班")
                                            else:
                                                filter_label.set_text(f"选择范围: {first}")
                                        else:
                                            filter_state["org_id"] = None
                                            filter_label.set_text("选择范围: 全部")
                                        dialog.close()
                                        refresh_posts()

            def refresh_posts():
                if post_container:
                    post_container.clear()
                    with post_container:
                        posts = load_posts(user, filter_state.get("org_id"))
                        if not posts:
                            ui.label("暂无内容").classes("text-gray-400 text-center py-8 w-full")
                        for pd in posts:
                            render_post_card(pd, user, refresh_posts)

            post_container = ui.column().classes("w-full")
            with post_container:
                posts = load_posts(user, filter_state.get("org_id"))
                if not posts:
                    ui.label("暂无内容").classes("text-gray-400 text-center py-8 w-full")
                for pd in posts:
                    render_post_card(pd, user, refresh_posts)


@router.page("/publish")
async def publish_page():
    if not AuthManager.is_authenticated():
        ui.navigate.to("/login")
        return

    user = AuthManager.get_current_user()

    with get_db() as db:
        user_obj = db.query(User).filter(User.id == user["user_id"]).first()
        if not user_obj:
            ui.navigate.to("/home")
            return

        if user_obj.user_type == "student":
            default_org_id = user_obj.default_org_id
            org_tree = _get_student_org_tree(db, user_obj)
        elif user_obj.user_type == "teacher":
            school = get_user_school(db, user_obj)
            default_org_id = school.id if school else user_obj.default_org_id
            org_tree = _get_teacher_org_tree(db, user_obj)
        elif user_obj.user_type == "admin":
            default_org_id = user_obj.default_org_id
            org_tree = _get_admin_org_tree(db)
        else:
            default_org_id = None
            org_tree = {}

    state = {
        "files": [],
        "show_location": True,
        "visibility": "public",
        "visible_to_orgs": [],
        "excluded_orgs": [],
    }

    async def handle_upload(e):
        ext = os.path.splitext(e.file.name)[1].lower()
        if ext.lstrip(".") not in {"png", "jpg", "jpeg", "gif", "webp"}:
            ui.notify("仅支持图片", type="warning")
            return
        ts = int(time.time())
        uid = uuid.uuid4().hex[:8]
        safe_name = f"{ts}_{uid}{ext}"
        upload_dir = config.absolute_upload_dir
        os.makedirs(upload_dir, exist_ok=True)
        await e.file.save(os.path.join(upload_dir, safe_name))
        state["files"].append(safe_name)
        refresh_preview()

    async def handle_publish():
        content = content_input.value.strip()
        if not content and not state["files"]:
            ui.notify("请输入内容或上传图片", type="warning")
            return

        with get_db() as db:
            u = db.query(User).filter(User.id == user["user_id"]).first()
            if not u:
                return
            org = db.query(Org).filter(Org.id == default_org_id).first()
            if org and org.org_type == "school":
                visible_org_id = org.id
            elif org:
                s = get_school_root(db, org.id)
                visible_org_id = s.id if s else default_org_id
            else:
                visible_org_id = default_org_id

            post = Post(
                user_id=u.id,
                content=content,
                images=",".join(state["files"]) if state["files"] else None,
                org_id=default_org_id,
                visible_org_id=visible_org_id,
                visibility=state["visibility"],
                show_location=state["show_location"],
                visible_to_orgs=",".join(state["visible_to_orgs"]) if state["visible_to_orgs"] else None,
                excluded_orgs=",".join(state["excluded_orgs"]) if state["excluded_orgs"] else None,
            )
            db.add(post)
            db.commit()

        ui.notify("发布成功", type="positive")
        ui.navigate.to("/home")

    with ui.column().classes("w-full min-h-screen bg-[#ededed] items-center"):
        with ui.column().classes("w-full max-w-[428px]"):
            with ui.row().classes(
                "w-full h-12 bg-white border-b border-gray-200 items-center justify-between px-4 sticky top-0 z-50"
            ):
                ui.button("取消", on_click=lambda: ui.navigate.to("/home")).props(
                    "flat no-caps color=grey-7 text-base"
                )
                ui.button("发表", on_click=handle_publish).props(
                    "flat no-caps color=green-600 text-green-600 text-base font-bold"
                )

            with ui.column().classes("w-full bg-white"):
                with ui.column().classes("w-full px-4 pt-4"):
                    preview_container = ui.row().classes("flex flex-wrap gap-2")

                    def refresh_preview():
                        preview_container.clear()
                        with preview_container:
                            for img in state["files"]:
                                with ui.element("div").classes("w-24 h-24 relative rounded overflow-hidden"):
                                    ui.image(f"/static/uploads/{img}").classes("w-full h-full object-cover")
                                    ui.button(
                                        icon="close",
                                        on_click=lambda i=img: _remove_image(i, state, refresh_preview),
                                    ).props("flat dense round size=xs color=white").classes(
                                        "absolute top-0 right-0 bg-black/40 rounded-full min-w-[20px] min-h-[20px]"
                                    )

                    refresh_preview()

                    ui.upload(
                        on_upload=handle_upload,
                        auto_upload=True,
                        multiple=True,
                    ).props("accept=image/* label=添加图片 color=grey-4 flat").classes("w-full").style(
                        "border: 2px dashed #d1d5db; border-radius: 8px;"
                    )

                content_input = ui.textarea(placeholder="这一刻的想法...").classes("w-full").props(
                    "borderless rows=4 dense"
                ).style("font-size: 15px; padding: 12px 16px;")

                ui.element("div").classes("h-2 bg-[#ededed]")

                with ui.row().classes(
                    "w-full items-center justify-between px-4 py-3 bg-white border-b border-gray-100 cursor-pointer"
                ).on("click", lambda: _show_location_dialog(state, location_label)):
                    ui.label("所在位置").classes("text-sm text-gray-800")
                    with ui.row().classes("items-center gap-1"):
                        location_label = ui.label("当前位置").classes("text-sm text-gray-500")
                        ui.icon("chevron_right").classes("text-gray-400 text-lg")

                with ui.row().classes(
                    "w-full items-center justify-between px-4 py-3 bg-white border-b border-gray-100 cursor-pointer"
                ).on("click", lambda: _show_visibility_dialog(state, vis_label, org_tree)):
                    ui.label("谁可以看").classes("text-sm text-gray-800")
                    with ui.row().classes("items-center gap-1"):
                        vis_label = ui.label("公开").classes("text-sm text-gray-500")
                        ui.icon("chevron_right").classes("text-gray-400 text-lg")

                with ui.row().classes(
                    "w-full items-center justify-between px-4 py-3 bg-white border-b border-gray-100 cursor-pointer"
                ).on("click", lambda: _show_exclusion_dialog(state, excl_label, org_tree)):
                    ui.label("不给谁看").classes("text-sm text-gray-800")
                    with ui.row().classes("items-center gap-1"):
                        excl_label = ui.label("不限").classes("text-sm text-gray-500")
                        ui.icon("chevron_right").classes("text-gray-400 text-lg")


def _remove_image(img_name, state, refresh_fn):
    if img_name in state["files"]:
        state["files"].remove(img_name)
        refresh_fn()


def _get_student_org_tree(db, user_obj):
    tree = {}
    cls = db.query(Org).filter(Org.id == user_obj.default_org_id).first()
    if cls:
        tree[cls.id] = cls.name
        from core.models import UserRole, User
        class_admins = (
            db.query(UserRole).filter(UserRole.scope_org_id == cls.id, UserRole.role == "class_admin").all()
        )
        for r in class_admins:
            t = db.query(User).filter(User.id == r.user_id).first()
            if t:
                tree[f"__user__{t.id}"] = f"  {t.display_name or t.username}（管理员）"
    return tree


def _get_teacher_org_tree(db, user_obj):
    tree = {}
    school = get_user_school(db, user_obj)
    if school:
        tree[school.id] = f"{school.name}(全校)"
        for g in get_grades(db, school.id):
            tree[g.id] = f"  {g.name}"
            for c in get_classes(db, g.id):
                tree[c.id] = f"    {c.name}"
    return tree


def _get_admin_org_tree(db):
    tree = {}
    for s in get_schools(db):
        tree[s.id] = f"{s.name}(全校)"
        for g in get_grades(db, s.id):
            tree[g.id] = f"  {g.name}"
            for c in get_classes(db, g.id):
                tree[c.id] = f"    {c.name}"
    return tree


def _show_location_dialog(state, label_elem):
    with ui.dialog() as dialog, ui.card().classes("w-80 p-4"):
        ui.label("所在位置").classes("text-base font-bold mb-3")
        opts = {"show": "显示位置", "hide": "不显示位置"}
        current = "show" if state["show_location"] else "hide"
        radio = ui.radio(opts, value=current).classes("w-full")

        async def confirm():
            state["show_location"] = radio.value == "show"
            label_elem.set_text("当前位置" if state["show_location"] else "不显示位置")
            dialog.close()

        with ui.row().classes("w-full justify-end gap-2 mt-4"):
            ui.button("取消", on_click=dialog.close).props("flat")
            ui.button("确定", on_click=confirm).props("color=primary")

    dialog.open()


def _show_visibility_dialog(state, label_elem, org_tree):
    with ui.dialog() as dialog, ui.card().classes("w-[360px] p-4"):
        ui.label("谁可以看").classes("text-base font-bold mb-3")
        vis_type = ui.radio(
            {"public": "公开", "private": "私密", "partial": "部分可见"},
            value=state["visibility"],
        ).classes("w-full")

        partial_container = ui.column().classes("w-full mt-2")

        def on_vis_change():
            partial_container.clear()
            if vis_type.value == "partial" and org_tree:
                with partial_container:
                    ui.label("选择可见范围:").classes("text-xs text-gray-500 mb-1")
                    selected = list(state["visible_to_orgs"])
                    checks = {}
                    for oid, name in org_tree.items():
                        checks[oid] = ui.checkbox(name, value=(oid in selected))

                    def collect():
                        return [oid for oid, cb in checks.items() if cb.value]

                    partial_container._collect = collect
            else:
                partial_container._collect = lambda: []

        vis_type.on("update:model-value", on_vis_change)
        on_vis_change()

        async def confirm():
            state["visibility"] = vis_type.value
            if vis_type.value == "partial":
                state["visible_to_orgs"] = partial_container._collect()
            else:
                state["visible_to_orgs"] = []
            label_map = {"public": "公开", "private": "私密", "partial": "部分可见"}
            label_elem.set_text(label_map.get(state["visibility"], "公开"))
            dialog.close()

        with ui.row().classes("w-full justify-end gap-2 mt-4"):
            ui.button("取消", on_click=dialog.close).props("flat")
            ui.button("确定", on_click=confirm).props("color=primary")

    dialog.open()


def _show_exclusion_dialog(state, label_elem, org_tree):
    with ui.dialog() as dialog, ui.card().classes("w-[360px] p-4"):
        ui.label("不给谁看").classes("text-base font-bold mb-3")
        selected = list(state["excluded_orgs"])
        checks = {}
        for oid, name in org_tree.items():
            checks[oid] = ui.checkbox(name, value=(oid in selected))

        async def confirm():
            result = [oid for oid, cb in checks.items() if cb.value]
            state["excluded_orgs"] = result
            label_elem.set_text("不限" if not result else f"已排除 {len(result)} 项")
            dialog.close()

        with ui.row().classes("w-full justify-end gap-2 mt-4"):
            ui.button("取消", on_click=dialog.close).props("flat")
            ui.button("确定", on_click=confirm).props("color=primary")

    dialog.open()
