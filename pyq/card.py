import os
from datetime import datetime

from nicegui import app, ui

from config import config
from core.models import Comment, Like, Org, Post, Reply, User
from core.org_utils import get_org_descendants, get_user_school, get_visible_org_ids
from core.permissions import can_delete_post, can_manage_comment, can_manage_post
from database import get_db


def render_post_card(post_data: dict, current_user: dict, refresh_fn=None):
    is_author = post_data.get("user_id") == current_user["user_id"]
    can_del = is_author
    can_hide = False

    if not is_author:
        with get_db() as db:
            u = db.query(User).filter(User.id == current_user["user_id"]).first()
            p = db.query(Post).filter(Post.id == post_data["id"]).first()
            if u and p:
                can_del = can_delete_post(u, p)
                if u.user_type in ("teacher", "admin"):
                    can_hide = can_manage_post(u, p)

    if post_data.get("is_hidden_by_admin") and not is_author and not can_hide:
        return

    with ui.element("div").classes("w-full bg-white rounded-lg shadow-sm mb-4 overflow-hidden"):
        if post_data.get("is_hidden_by_admin"):
            with ui.row().classes("w-full px-4 py-2 bg-red-50 items-center gap-2 border-b-2 border-red-300"):
                ui.icon("block", color="red").classes("text-lg")
                ui.label("此内容已被管理员屏蔽").classes("text-sm text-red-600 font-bold")

        with ui.row().classes("w-full p-4 gap-3"):
            is_teacher = post_data.get("user_type") == "teacher"
            avatar_color = "bg-blue-500" if is_teacher else "bg-gray-400"
            avatar_icon = "school" if is_teacher else "person"
            with ui.element("div").classes(
                f"w-10 h-10 rounded-full flex items-center justify-center text-white flex-shrink-0 {avatar_color}"
            ):
                ui.icon(avatar_icon).classes("text-xl")

            with ui.column().classes("flex-1 gap-0 min-w-0"):
                name_cls = "text-blue-500 font-bold" if is_teacher else "text-gray-800 font-medium"
                ui.label(post_data.get("author_name", "未知")).classes(f"text-sm {name_cls}")
                with ui.row().classes("items-center gap-2"):
                    ui.label(post_data.get("time_ago", "")).classes("text-xs text-gray-400")
                    if post_data.get("show_location", True) and post_data.get("org_name"):
                        ui.label(post_data.get("org_name", "")).classes("text-xs text-blue-400")

        with ui.column().classes("px-4 pb-2"):
            ui.label(post_data.get("content", "")).classes(
                "text-sm text-gray-800 leading-relaxed whitespace-pre-wrap"
            )

        images = post_data.get("images", [])
        if images:
            _render_image_grid(images)

        with ui.column().classes("px-4 pb-4"):
            with ui.row().classes("w-full items-center gap-6 pt-2 border-t border-gray-100 mt-2"):
                like_count = post_data.get("like_count", 0)
                is_liked = post_data.get("is_liked", False)
                like_icon = "star" if is_liked else "star_border"
                like_color = "text-blue-500" if is_liked else "text-gray-400"
                like_text = str(like_count) if like_count > 0 else "点赞"

                ui.button(
                    icon=like_icon,
                    text=like_text,
                    on_click=lambda pid=post_data["id"]: _toggle_like(pid, refresh_fn),
                ).props("flat dense no-caps size=sm").classes(f"{like_color}")

                comment_count = post_data.get("comment_count", 0)
                comment_text = str(comment_count) if comment_count > 0 else "评论"
                ui.button(
                    icon="chat_bubble_outline",
                    text=comment_text,
                    on_click=lambda pid=post_data["id"]: _toggle_comment_box(pid),
                ).props("flat dense no-caps size=sm").classes("text-gray-400")

                with ui.row().classes("ml-auto gap-1"):
                    if can_hide:
                        if post_data.get("is_hidden_by_admin"):
                            ui.button(
                                icon="visibility",
                                on_click=lambda pid=post_data["id"]: _unhide_post(pid, refresh_fn),
                            ).props("flat dense size=sm color=green")
                        else:
                            ui.button(
                                icon="visibility_off",
                                on_click=lambda pid=post_data["id"]: _hide_post(pid, refresh_fn),
                            ).props("flat dense size=sm color=orange")
                    if can_del:
                        ui.button(
                            icon="delete_outline",
                            on_click=lambda pid=post_data["id"]: _delete_post(pid, refresh_fn),
                        ).props("flat dense size=sm color=red")

            _render_comments(post_data, current_user, refresh_fn, can_hide)


def _render_image_grid(images):
    count = len(images)
    if count == 0:
        return

    if count == 1:
        grid_cols = "grid-cols-1"
        max_w = "max-w-[66%]"
    elif count == 2:
        grid_cols = "grid-cols-2"
        max_w = ""
    elif count == 4:
        grid_cols = "grid-cols-2"
        max_w = ""
    else:
        grid_cols = "grid-cols-3"
        max_w = ""

    with ui.element("div").classes(f"grid {grid_cols} gap-1 px-4 mt-2 {max_w}"):
        for img in images:
            if img:
                with ui.element("div").classes(
                    "aspect-square overflow-hidden rounded bg-gray-100 cursor-pointer"
                ).on("click", lambda img_name=img: _show_image_viewer(img_name)):
                    ui.image(f"/static/uploads/{img}").classes(
                        "w-full h-full object-cover"
                    )


def _show_image_viewer(img_name):
    with ui.dialog() as dialog:
        with ui.element("div").classes(
            "fixed inset-0 bg-black/95 flex items-center justify-center"
        ).style("width: 100vw; height: 100vh; position: fixed; top: 0; left: 0; right: 0; bottom: 0; z-index: 9999;"):
            ui.button(
                icon="close",
                on_click=dialog.close,
            ).props("flat round dense color=white size=lg").classes(
                "absolute top-4 right-4"
            ).style("z-index: 10001;")
            ui.image(f"/static/uploads/{img_name}").classes(
                "object-contain"
            ).style(
                "max-width: 90vw; max-height: 90vh; user-select: none; -webkit-user-drag: none;"
            )

    dialog.props("full-width seamless")
    dialog.open()


_comment_boxes = {}


def _toggle_comment_box(post_id):
    if post_id in _comment_boxes:
        box = _comment_boxes[post_id]
        box.set_value(not box.value)


def _render_comments(post_data, current_user, refresh_fn, post_can_manage=False):
    comments = post_data.get("comments", [])

    with ui.column().classes("w-full"):
        if comments:
            with ui.element("div").classes("bg-[#f7f7f7] rounded mt-3 px-3 py-2"):
                for c in comments:
                    if c.get("is_deleted_by_author"):
                        continue

                    c_is_author = c.get("user_id") == current_user["user_id"]
                    if c.get("is_hidden_by_admin") and not c_is_author and not post_can_manage:
                        continue

                    with ui.row().classes("w-full text-sm leading-relaxed"):
                        is_t = c.get("user_type") == "teacher"
                        name_cls = "text-blue-500 font-bold" if is_t else "text-blue-500"

                        if c.get("is_hidden_by_admin"):
                            with ui.element("span").classes(
                                "inline-flex items-center bg-red-100 text-red-600 text-xs px-2 py-0.5 rounded-full font-bold mr-1"
                            ):
                                ui.icon("block", size="xs").classes("mr-1")
                                ui.label("被屏蔽")

                        ui.html(
                            f'<span class="{name_cls}">{c.get("author_name", "?")}'
                            f'</span><span class="text-gray-600">：{c["content"]}</span>'
                        )

                        with ui.row().classes("ml-auto gap-1 items-center"):
                            c_can_del = c_is_author or post_can_manage
                            c_can_hide = post_can_manage and not c_is_author

                            if c_can_hide and not c.get("is_hidden_by_admin"):
                                ui.button(
                                    icon="visibility_off",
                                    on_click=lambda cid=c["id"]: _hide_comment(cid, refresh_fn),
                                ).props("flat dense size=sm color=orange icon-only")

                            if c_can_hide and c.get("is_hidden_by_admin"):
                                ui.button(
                                    icon="visibility",
                                    on_click=lambda cid=c["id"]: _unhide_comment(cid, refresh_fn),
                                ).props("flat dense size=sm color=green icon-only")

                            if c_can_del:
                                ui.button(
                                    icon="close",
                                    on_click=lambda cid=c["id"], pid=post_data["id"]: _delete_comment_by_author(
                                        cid, pid, refresh_fn
                                    ),
                                ).props("flat dense size=sm color=red icon-only")

                            ui.button(
                                icon="reply",
                                on_click=lambda cid=c["id"]: _toggle_reply_box(cid),
                            ).props("flat dense size=sm color=blue icon-only")

                    replies = c.get("replies", [])
                    if replies:
                        with ui.column().classes("ml-4 mt-2"):
                            for r in replies:
                                if r.get("is_deleted_by_author"):
                                    continue

                                r_is_author = r.get("user_id") == current_user["user_id"]
                                if r.get("is_hidden_by_admin") and not r_is_author and not post_can_manage:
                                    continue

                                with ui.row().classes("w-full text-xs leading-relaxed"):
                                    is_tr = r.get("user_type") == "teacher"
                                    r_name_cls = "text-blue-500 font-bold" if is_tr else "text-blue-500"

                                    if r.get("is_hidden_by_admin"):
                                        with ui.element("span").classes(
                                            "inline-flex items-center bg-red-100 text-red-600 text-xs px-2 py-0.5 rounded-full font-bold mr-1"
                                        ):
                                            ui.icon("block", size="xs").classes("mr-1")
                                            ui.label("被屏蔽")

                                    ui.html(
                                        f'<span class="{r_name_cls}">{r.get("author_name", "?")}'
                                        f'</span><span class="text-gray-600">：{r["content"]}</span>'
                                    )

                                    with ui.row().classes("ml-auto gap-1"):
                                        if r_is_author:
                                            ui.button(
                                                icon="close",
                                                on_click=lambda rid=r["id"]: _delete_reply_by_author(
                                                    rid, refresh_fn
                                                ),
                                            ).props("flat dense size=sm color=red icon-only")

                    reply_box = ui.expansion("回复...", value=False).classes("w-full mt-1").props("dense")
                    with reply_box:
                        with ui.row().classes("w-full items-center gap-2"):
                            reply_inp = ui.input(placeholder="回复...").classes("flex-1").props("outlined dense")
                            ui.button(
                                "发送",
                                on_click=lambda cid=c["id"], ri=reply_inp: _add_reply(cid, ri, refresh_fn),
                            ).props("dense size=sm color=primary")
                    _reply_boxes[c["id"]] = reply_box

        comment_box = ui.expansion("写评论...", value=False).classes("w-full mt-2").props("dense")
        with comment_box:
            with ui.row().classes("w-full items-center gap-2"):
                inp = ui.input(placeholder="评论...").classes("flex-1").props("outlined dense")
                ui.button(
                    "发送",
                    on_click=lambda pid=post_data["id"]: _add_comment(pid, inp, refresh_fn),
                ).props("dense size=sm color=primary")

        _comment_boxes[post_data["id"]] = comment_box


def _toggle_like(post_id, refresh_fn):
    from core.auth import AuthManager

    user = AuthManager.get_current_user()
    if not user:
        return
    with get_db() as db:
        existing = db.query(Like).filter(Like.post_id == post_id, Like.user_id == user["user_id"]).first()
        if existing:
            db.delete(existing)
        else:
            db.add(Like(post_id=post_id, user_id=user["user_id"]))
        db.commit()
    if refresh_fn:
        refresh_fn()


def _add_comment(post_id, input_elem, refresh_fn):
    from core.auth import AuthManager

    user = AuthManager.get_current_user()
    if not user:
        return
    content = input_elem.value.strip()
    if not content:
        ui.notify("请输入评论内容", type="warning")
        return
    with get_db() as db:
        db.add(Comment(post_id=post_id, user_id=user["user_id"], content=content))
        db.commit()
    input_elem.set_value("")
    ui.notify("评论成功", type="positive")
    if refresh_fn:
        refresh_fn()


def _delete_comment(comment_id, post_id, refresh_fn):
    with get_db() as db:
        c = db.query(Comment).filter(Comment.id == comment_id).first()
        if c:
            db.delete(c)
            db.commit()
    ui.notify("已删除", type="info")
    if refresh_fn:
        refresh_fn()


def _delete_post(post_id, refresh_fn):
    with get_db() as db:
        db.query(Comment).filter(Comment.post_id == post_id).delete()
        db.query(Like).filter(Like.post_id == post_id).delete()
        post = db.query(Post).filter(Post.id == post_id).first()
        if post and post.images:
            for img in post.images.split(","):
                path = os.path.join(config.absolute_upload_dir, img)
                if os.path.exists(path):
                    os.remove(path)
        db.query(Post).filter(Post.id == post_id).delete()
        db.commit()
    ui.notify("已删除", type="info")
    if refresh_fn:
        refresh_fn()


def load_posts(user: dict, filter_org_id=None) -> list[dict]:
    with get_db() as db:
        user_obj = db.query(User).filter(User.id == user["user_id"]).first()
        if not user_obj:
            return []

        visible_ids = get_visible_org_ids(db, user_obj)

        query = db.query(Post).filter(Post.is_hidden == False, Post.org_id.in_(visible_ids))
        if filter_org_id:
            if isinstance(filter_org_id, list):
                valid = [oid for oid in filter_org_id if oid in visible_ids]
                if valid:
                    query = query.filter(Post.org_id.in_(valid))
                else:
                    return []
            elif filter_org_id in visible_ids:
                query = query.filter(Post.org_id == filter_org_id)
            else:
                return []

        posts = query.order_by(Post.created_at.desc()).limit(100).all()

        user_org_ids = set()
        if user_obj.user_type == "student":
            user_org_ids.add(user_obj.default_org_id)
            cur = db.query(Org).filter(Org.id == user_obj.default_org_id).first()
            while cur and cur.parent_id:
                user_org_ids.add(cur.parent_id)
                cur = db.query(Org).filter(Org.id == cur.parent_id).first()
        elif user_obj.user_type == "teacher":
            school = get_user_school(db, user_obj)
            if school:
                user_org_ids.update(get_org_descendants(db, school.id))
                user_org_ids.add(school.id)
        elif user_obj.user_type == "admin":
            user_org_ids = set(visible_ids)

        result = []
        for post in posts:
            if post.visibility == "private" and post.user_id != user["user_id"]:
                continue

            if post.visibility == "partial" and post.user_id != user["user_id"]:
                post_vis = set(post.visible_to_orgs.split(",")) if post.visible_to_orgs else set()
                if not (user_org_ids & post_vis):
                    continue

            if post.excluded_orgs and post.user_id != user["user_id"]:
                excl = set(post.excluded_orgs.split(","))
                if user_org_ids & excl:
                    continue

            author = db.query(User).filter(User.id == post.user_id).first()
            org = db.query(Org).filter(Org.id == post.org_id).first()
            like_count = db.query(Like).filter(Like.post_id == post.id).count()
            is_liked = (
                db.query(Like)
                .filter(Like.post_id == post.id, Like.user_id == user["user_id"])
                .first()
                is not None
            )
            comments = (
                db.query(Comment)
                .filter(Comment.post_id == post.id)
                .order_by(Comment.created_at.asc())
                .all()
            )
            comments_data = []
            for c in comments:
                ca = db.query(User).filter(User.id == c.user_id).first()
                replies = (
                    db.query(Reply)
                    .filter(Reply.comment_id == c.id)
                    .order_by(Reply.created_at.asc())
                    .all()
                )
                replies_data = []
                for r in replies:
                    ra = db.query(User).filter(User.id == r.user_id).first()
                    replies_data.append(
                        {
                            "id": r.id,
                            "user_id": r.user_id,
                            "user_type": ra.user_type if ra else "",
                            "content": r.content,
                            "author_name": (ra.display_name or ra.username) if ra else "未知",
                            "is_hidden_by_admin": r.is_hidden_by_admin,
                            "is_deleted_by_author": r.is_deleted_by_author,
                        }
                    )

                comments_data.append(
                    {
                        "id": c.id,
                        "user_id": c.user_id,
                        "user_type": ca.user_type if ca else "",
                        "content": c.content,
                        "author_name": (ca.display_name or ca.username) if ca else "未知",
                        "is_hidden_by_admin": c.is_hidden_by_admin,
                        "is_deleted_by_author": c.is_deleted_by_author,
                        "replies": replies_data,
                    }
                )

            result.append(
                {
                    "id": post.id,
                    "user_id": post.user_id,
                    "user_type": author.user_type if author else "",
                    "author_name": (author.display_name or author.username) if author else "未知",
                    "content": post.content,
                    "images": post.images.split(",") if post.images else [],
                    "org_id": post.org_id,
                    "org_name": org.name if org else "",
                    "like_count": like_count,
                    "is_liked": is_liked,
                    "comment_count": len(comments_data),
                    "comments": comments_data,
                    "is_hidden_by_admin": post.is_hidden_by_admin,
                    "visibility": post.visibility or "public",
                    "show_location": post.show_location if post.show_location is not None else True,
                    "time_ago": _time_ago(post.created_at),
                }
            )
        return result


def _time_ago(dt) -> str:
    if not dt:
        return ""
    now = datetime.utcnow()
    diff = now - dt
    seconds = int(diff.total_seconds())
    if seconds < 60:
        return "刚刚"
    elif seconds < 3600:
        return f"{seconds // 60}分钟前"
    elif seconds < 86400:
        return f"{seconds // 3600}小时前"
    elif seconds < 604800:
        return f"{seconds // 86400}天前"
    else:
        return dt.strftime("%Y-%m-%d")


def _hide_post(post_id, refresh_fn):
    with get_db() as db:
        post = db.query(Post).filter(Post.id == post_id).first()
        if post:
            post.is_hidden_by_admin = True
            db.commit()
    ui.notify("已屏蔽此内容", type="info")
    if refresh_fn:
        refresh_fn()


def _unhide_post(post_id, refresh_fn):
    with get_db() as db:
        post = db.query(Post).filter(Post.id == post_id).first()
        if post:
            post.is_hidden_by_admin = False
            db.commit()
    ui.notify("已解除屏蔽", type="positive")
    if refresh_fn:
        refresh_fn()


def _hide_comment(comment_id, refresh_fn):
    with get_db() as db:
        comment = db.query(Comment).filter(Comment.id == comment_id).first()
        if comment:
            comment.is_hidden_by_admin = True
            db.commit()
    ui.notify("已屏蔽此评论", type="info")
    if refresh_fn:
        refresh_fn()


def _unhide_comment(comment_id, refresh_fn):
    with get_db() as db:
        comment = db.query(Comment).filter(Comment.id == comment_id).first()
        if comment:
            comment.is_hidden_by_admin = False
            db.commit()
    ui.notify("已解除屏蔽", type="positive")
    if refresh_fn:
        refresh_fn()


def _delete_comment_by_author(comment_id, post_id, refresh_fn):
    with get_db() as db:
        comment = db.query(Comment).filter(Comment.id == comment_id).first()
        if comment:
            comment.is_deleted_by_author = True
            db.commit()
    ui.notify("评论已删除", type="info")
    if refresh_fn:
        refresh_fn()


def _delete_comment(comment_id, post_id, refresh_fn):
    with get_db() as db:
        c = db.query(Comment).filter(Comment.id == comment_id).first()
        if c:
            db.delete(c)
            db.commit()
    ui.notify("已删除", type="info")
    if refresh_fn:
        refresh_fn()


_reply_boxes = {}


def _toggle_reply_box(comment_id):
    if comment_id in _reply_boxes:
        box = _reply_boxes[comment_id]
        box.set_value(not box.value)


def _add_reply(comment_id, input_elem, refresh_fn):
    from core.auth import AuthManager

    user = AuthManager.get_current_user()
    if not user:
        return
    content = input_elem.value.strip()
    if not content:
        ui.notify("请输入回复内容", type="warning")
        return
    with get_db() as db:
        db.add(Reply(comment_id=comment_id, user_id=user["user_id"], content=content))
        db.commit()
    input_elem.set_value("")
    ui.notify("回复成功", type="positive")
    if refresh_fn:
        refresh_fn()


def _delete_reply_by_author(reply_id, refresh_fn):
    with get_db() as db:
        reply = db.query(Reply).filter(Reply.id == reply_id).first()
        if reply:
            reply.is_deleted_by_author = True
            db.commit()
    ui.notify("回复已删除", type="info")
    if refresh_fn:
        refresh_fn()
