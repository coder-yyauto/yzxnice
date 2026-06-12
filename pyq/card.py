import os
from datetime import datetime
from typing import Any, cast

from nicegui import ui

from config import config
from core.models import Comment, Like, Org, Post, Reply, User
from core.org_utils import get_org_descendants, get_user_school, get_visible_org_ids
from core.permissions import can_delete_post, can_manage_post
from database import get_db


def _resolve_post_permissions(post_data: dict[str, Any], current_user: dict[str, Any]) -> tuple[bool, bool, bool]:
    """Return (is_author, can_delete, can_hide) for a post."""
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
    return is_author, can_del, can_hide


def render_post_card(post_data: dict[str, Any], current_user: dict[str, Any], refresh_fn: Any = None) -> None:
    is_author, can_del, can_hide = _resolve_post_permissions(post_data, current_user)

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
            ui.label(post_data.get("content", "")).classes("text-sm text-gray-800 leading-relaxed whitespace-pre-wrap")

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


def _render_image_grid(images: list[str]) -> None:
    count = len(images)
    if count == 0:
        return

    if count == 1:
        grid_cols = "grid-cols-1"
        max_w = "max-w-[66%]"
    elif count == 2 or count == 4:
        grid_cols = "grid-cols-2"
        max_w = ""
    else:
        grid_cols = "grid-cols-3"
        max_w = ""

    with ui.element("div").classes(f"grid {grid_cols} gap-1 px-4 mt-2 {max_w}"):
        for img in images:
            if img:
                with (
                    ui.element("div")
                    .classes("aspect-square overflow-hidden rounded bg-gray-100 cursor-pointer")
                    .on("click", lambda img_name=img: _show_image_viewer(img_name))
                ):
                    ui.image(f"/static/uploads/{img}").classes("w-full h-full object-cover")


def _show_image_viewer(img_name: str) -> None:
    with (
        ui.dialog() as dialog,
        ui.element("div")
        .classes("fixed inset-0 bg-black/95 flex items-center justify-center")
        .style("width: 100vw; height: 100vh; position: fixed; top: 0; left: 0; right: 0; bottom: 0; z-index: 9999;"),
    ):
        ui.button(
            icon="close",
            on_click=dialog.close,
        ).props("flat round dense color=white size=lg").classes("absolute top-4 right-4").style("z-index: 10001;")
        ui.image(f"/static/uploads/{img_name}").classes("object-contain").style(
            "max-width: 90vw; max-height: 90vh; user-select: none; -webkit-user-drag: none;"
        )

    dialog.props("full-width seamless")
    dialog.open()


_comment_boxes: dict[str, Any] = {}


def _toggle_comment_box(post_id: str) -> None:
    if post_id in _comment_boxes:
        box = _comment_boxes[post_id]
        box.set_value(not box.value)


def _should_show_comment(c: dict[str, Any], current_user: dict[str, Any], post_can_manage: bool) -> bool:
    """Check if a comment should be visible to the current user."""
    if c.get("is_deleted_by_author"):
        return False
    c_is_author = c.get("user_id") == current_user["user_id"]
    return not (c.get("is_hidden_by_admin") and not c_is_author and not post_can_manage)


def _render_comment_header(c: dict[str, Any]) -> tuple[str, bool]:
    """Render comment author name + badge. Returns (name_cls, is_teacher)."""
    is_teacher = c.get("user_type") == "teacher"
    name_cls = "text-blue-500 font-bold" if is_teacher else "text-blue-500"
    if c.get("is_hidden_by_admin"):
        with ui.element("span").classes(
            "inline-flex items-center bg-red-100 text-red-600 text-xs px-2 py-0.5 rounded-full font-bold mr-1"
        ):
            ui.icon("block", size="xs").classes("mr-1")
            ui.label("被屏蔽")
    return name_cls, is_teacher


def _render_comment_actions(
    c: dict[str, Any], current_user: dict[str, Any], post_can_manage: bool, refresh_fn: Any
) -> None:
    """Render action buttons for a single comment."""
    c_is_author = c.get("user_id") == current_user["user_id"]
    c_can_hide = post_can_manage and not c_is_author
    if c_can_hide:
        if c.get("is_hidden_by_admin"):
            ui.button(icon="visibility", on_click=lambda cid=c["id"]: _unhide_comment(cid, refresh_fn)).props(
                "flat dense size=sm color=green icon-only"
            )
        else:
            ui.button(icon="visibility_off", on_click=lambda cid=c["id"]: _hide_comment(cid, refresh_fn)).props(
                "flat dense size=sm color=orange icon-only"
            )
    if c_is_author or post_can_manage:
        post_id = c.get("post_id", "")
        ui.button(
            icon="close",
            on_click=lambda cid=c["id"], pid=post_id: _delete_comment_by_author(cid, pid, refresh_fn),
        ).props("flat dense size=sm color=red icon-only")
    ui.button(icon="reply", on_click=lambda cid=c["id"]: _toggle_reply_box(cid)).props(
        "flat dense size=sm color=blue icon-only"
    )


def _render_comment_action_row(
    c: dict[str, Any], c_is_author: bool, post_id: str, refresh_fn: Any, post_can_manage: bool
) -> None:
    """Render the right-aligned action buttons (hide/unhide/delete/reply) for a comment."""
    c_can_del = c_is_author or post_can_manage
    c_can_hide = post_can_manage and not c_is_author

    with ui.row().classes("ml-auto gap-1 items-center"):
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
                on_click=lambda cid=c["id"], pid=post_id: _delete_comment_by_author(cid, pid, refresh_fn),
            ).props("flat dense size=sm color=red icon-only")

        ui.button(
            icon="reply",
            on_click=lambda cid=c["id"]: _toggle_reply_box(cid),
        ).props("flat dense size=sm color=blue icon-only")


def _render_replies(
    replies: list[dict[str, Any]], current_user: dict[str, Any], refresh_fn: Any, post_can_manage: bool
) -> None:
    """Render the list of replies under a comment, skipping hidden/deleted ones."""
    if not replies:
        return
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
                        "inline-flex items-center bg-red-100 text-red-600 text-xs "
                        "px-2 py-0.5 rounded-full font-bold mr-1"
                    ):
                        ui.icon("block", size="xs").classes("mr-1")
                        ui.label("被屏蔽")

                with ui.row().classes("gap-0"):
                    ui.label(r.get("author_name", "?")).classes(f"text-xs {r_name_cls}")
                    ui.label(f"：{r['content']}").classes("text-xs text-gray-600")

                with ui.row().classes("ml-auto gap-1"):
                    if r_is_author:
                        ui.button(
                            icon="close",
                            on_click=lambda rid=r["id"]: _delete_reply_by_author(rid, refresh_fn),
                        ).props("flat dense size=sm color=red icon-only")


def _render_single_comment(
    c: dict[str, Any], current_user: dict[str, Any], refresh_fn: Any, post_can_manage: bool, post_id: str
) -> bool:
    """Render one comment row, its replies, and its reply box. Skips hidden/deleted."""
    if c.get("is_deleted_by_author"):
        return False
    c_is_author = c.get("user_id") == current_user["user_id"]
    if c.get("is_hidden_by_admin") and not c_is_author and not post_can_manage:
        return False

    with ui.row().classes("w-full text-sm leading-relaxed"):
        is_t = c.get("user_type") == "teacher"
        name_cls = "text-blue-500 font-bold" if is_t else "text-blue-500"

        if c.get("is_hidden_by_admin"):
            with ui.element("span").classes(
                "inline-flex items-center bg-red-100 text-red-600 text-xs px-2 py-0.5 rounded-full font-bold mr-1"
            ):
                ui.icon("block", size="xs").classes("mr-1")
                ui.label("被屏蔽")

        with ui.row().classes("gap-0"):
            ui.label(c.get("author_name", "?")).classes(f"text-sm {name_cls}")
            ui.label(f"：{c['content']}").classes("text-sm text-gray-600")

        _render_comment_action_row(c, c_is_author, post_id, refresh_fn, post_can_manage)

    _render_replies(c.get("replies", []), current_user, refresh_fn, post_can_manage)

    reply_box = ui.expansion("回复...", value=False).classes("w-full mt-1").props("dense")
    with reply_box, ui.row().classes("w-full items-center gap-2"):
        reply_inp = ui.input(placeholder="回复...").classes("flex-1").props("outlined dense")
        ui.button(
            "发送",
            on_click=lambda cid=c["id"], ri=reply_inp: _add_reply(cid, ri, refresh_fn),
        ).props("dense size=sm color=primary")
    _reply_boxes[c["id"]] = reply_box
    return True


def _render_comments(
    post_data: dict[str, Any], current_user: dict[str, Any], refresh_fn: Any, post_can_manage: bool = False
) -> None:
    comments = post_data.get("comments", [])

    with ui.column().classes("w-full"):
        if comments:
            with ui.element("div").classes("bg-[#f7f7f7] rounded mt-3 px-3 py-2"):
                for c in comments:
                    _render_single_comment(c, current_user, refresh_fn, post_can_manage, post_data["id"])

        comment_box = ui.expansion("写评论...", value=False).classes("w-full mt-2").props("dense")
        with comment_box, ui.row().classes("w-full items-center gap-2"):
            inp = ui.input(placeholder="评论...").classes("flex-1").props("outlined dense")
            ui.button(
                "发送",
                on_click=lambda pid=post_data["id"]: _add_comment(pid, inp, refresh_fn),
            ).props("dense size=sm color=primary")

        _comment_boxes[post_data["id"]] = comment_box


def _toggle_like(post_id: str, refresh_fn: Any) -> None:
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


def _add_comment(post_id: str, input_elem: Any, refresh_fn: Any) -> None:
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


def _delete_comment(comment_id: str, post_id: str, refresh_fn: Any) -> None:
    with get_db() as db:
        c = db.query(Comment).filter(Comment.id == comment_id).first()
        if c:
            db.delete(c)
            db.commit()
    ui.notify("已删除", type="info")
    if refresh_fn:
        refresh_fn()


def _delete_post(post_id: str, refresh_fn: Any) -> None:
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


def _compute_user_org_ids(user_obj: Any, db: Any, visible_ids: list[str]) -> set[str]:
    """Compute the set of org IDs that are visible to this user for visibility filtering."""
    user_org_ids: set[str] = set()
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
    return user_org_ids


def _apply_visibility_filters(posts: list[Any], user_id: str, user_org_ids: set[str]) -> list[Any]:
    """Filter posts by visibility settings (private/partial/excluded)."""
    filtered: list[Any] = []
    for post in posts:
        if post.visibility == "private" and post.user_id != user_id:
            continue
        if post.visibility == "partial" and post.user_id != user_id:
            post_vis = set(post.visible_to_orgs.split(",")) if post.visible_to_orgs else set()
            if not (user_org_ids & post_vis):
                continue
        if post.excluded_orgs and post.user_id != user_id:
            excl = set(post.excluded_orgs.split(","))
            if user_org_ids & excl:
                continue
        filtered.append(post)
    return filtered


def _build_post_dict(
    post: Any,
    author: Any,
    org: Any,
    comments: list[dict[str, Any]],
    like_count: int,
    is_liked: bool,
    comment_count: int,
) -> dict[str, Any]:
    """Build the dict representation of a single post."""
    return {
        "id": post.id,
        "user_id": post.user_id,
        "user_type": author.user_type if author else "",
        "content": post.content,
        "images": post.images.split(",") if post.images else [],
        "author_name": (author.nickname or author.display_name or author.username) if author else "未知",
        "org_id": post.org_id,
        "org_name": org.name if org else "",
        "time_ago": _time_ago(post.created_at),
        "created_at": post.created_at.isoformat() if post.created_at else None,
        "like_count": like_count,
        "is_liked": is_liked,
        "comment_count": comment_count,
        "comments": comments,
        "is_hidden_by_admin": post.is_hidden_by_admin,
        "visibility": post.visibility or "public",
        "show_location": post.show_location if post.show_location is not None else True,
        "visible_to_orgs": post.visible_to_orgs.split(",") if post.visible_to_orgs else [],
        "excluded_orgs": post.excluded_orgs.split(",") if post.excluded_orgs else [],
    }


def _build_posts_query(db: Any, user_obj: Any, filter_org_id: str | list[str] | None) -> tuple[Any, bool]:
    """Build the base post query for `load_posts`.

    Returns (query, ok). When ok is False, the caller must return [] (either
    the user lacks visibility for the requested filter, or no org ids are visible).
    """
    visible_ids = get_visible_org_ids(db, user_obj)
    query = db.query(Post).filter(~Post.is_hidden, Post.org_id.in_(visible_ids))
    if not filter_org_id:
        return query, True

    if isinstance(filter_org_id, list):
        valid = [oid for oid in filter_org_id if oid in visible_ids]
        if not valid:
            return query, False
        return query.filter(Post.org_id.in_(valid)), True

    if filter_org_id in visible_ids:
        return query.filter(Post.org_id == filter_org_id), True

    return query, False


def _collect_post_relations(db: Any, filtered: list[Any], viewer_id: str) -> dict[str, Any]:
    """Batch-load likes, comments, replies, users and orgs for the given posts.

    Returns a dict containing the lookup tables needed for dict assembly.
    """
    post_ids = [p.id for p in filtered]
    all_user_ids: set[str] = {p.user_id for p in filtered}

    like_rows = db.query(Like.post_id, Like.user_id).filter(Like.post_id.in_(post_ids)).all()
    like_count_map: dict[str, int] = {}
    is_liked_set: set[str] = set()
    for post_id, uid in like_rows:
        like_count_map[post_id] = like_count_map.get(post_id, 0) + 1
        if uid == viewer_id:
            is_liked_set.add(post_id)

    all_comments = db.query(Comment).filter(Comment.post_id.in_(post_ids)).order_by(Comment.created_at.asc()).all()
    comment_ids = [c.id for c in all_comments]
    for c in all_comments:
        all_user_ids.add(c.user_id)

    all_replies: list[Reply] = []
    if comment_ids:
        all_replies = db.query(Reply).filter(Reply.comment_id.in_(comment_ids)).order_by(Reply.created_at.asc()).all()
        for r in all_replies:
            all_user_ids.add(r.user_id)

    users_map: dict[str, User] = {}
    if all_user_ids:
        user_rows = db.query(User).filter(User.id.in_(list(all_user_ids))).all()
        users_map = {u.id: u for u in user_rows}

    all_org_ids: set[str] = {p.org_id for p in filtered} | {p.visible_org_id for p in filtered if p.visible_org_id}
    orgs_map: dict[str, Org] = {}
    if all_org_ids:
        org_rows = db.query(Org).filter(Org.id.in_(list(all_org_ids))).all()
        orgs_map = {o.id: o for o in org_rows}

    return {
        "like_count_map": like_count_map,
        "is_liked_set": is_liked_set,
        "users_map": users_map,
        "orgs_map": orgs_map,
        "all_comments": all_comments,
        "all_replies": all_replies,
    }


def _build_reply_dict(r: Any, users_map: dict[str, Any]) -> dict[str, Any]:
    """Convert a Reply ORM row to its API dict representation."""
    ra = users_map.get(r.user_id)
    return {
        "id": r.id,
        "user_id": r.user_id,
        "user_type": ra.user_type if ra else "",
        "content": r.content,
        "author_name": (ra.nickname or ra.display_name or ra.username) if ra else "未知",
        "is_hidden_by_admin": r.is_hidden_by_admin,
        "is_deleted_by_author": r.is_deleted_by_author,
    }


def _build_comment_dict(c: Any, users_map: dict[str, Any], replies_by_comment: dict[str, list[Any]]) -> dict[str, Any]:
    """Convert a Comment ORM row + its replies to its API dict representation."""
    ca = users_map.get(c.user_id)
    replies_data = [_build_reply_dict(r, users_map) for r in replies_by_comment.get(c.id, [])]
    return {
        "id": c.id,
        "user_id": c.user_id,
        "user_type": ca.user_type if ca else "",
        "content": c.content,
        "author_name": (ca.nickname or ca.display_name or ca.username) if ca else "未知",
        "is_hidden_by_admin": c.is_hidden_by_admin,
        "is_deleted_by_author": c.is_deleted_by_author,
        "replies": replies_data,
    }


def load_posts(user: dict[str, Any], filter_org_id: str | list[str] | None = None) -> list[dict[str, Any]]:
    with get_db() as db:
        user_obj = db.query(User).filter(User.id == user["user_id"]).first()
        if not user_obj:
            return []

        query, ok = _build_posts_query(db, user_obj, filter_org_id)
        if not ok:
            return []

        posts = query.order_by(Post.created_at.desc()).limit(100).all()

        user_org_ids = _compute_user_org_ids(user_obj, db, get_visible_org_ids(db, user_obj))
        filtered = _apply_visibility_filters(posts, user["user_id"], user_org_ids)
        if not filtered:
            return []

        rels = _collect_post_relations(db, filtered, user["user_id"])
        users_map = rels["users_map"]
        orgs_map = rels["orgs_map"]
        like_count_map = rels["like_count_map"]
        is_liked_set = rels["is_liked_set"]

        comments_by_post: dict[str, list[Comment]] = {}
        for c in rels["all_comments"]:
            comments_by_post.setdefault(c.post_id, []).append(c)
        replies_by_comment: dict[str, list[Reply]] = {}
        for r in rels["all_replies"]:
            replies_by_comment.setdefault(r.comment_id, []).append(r)

        result: list[dict[str, Any]] = []
        for post in filtered:
            author = users_map.get(post.user_id)
            org = orgs_map.get(post.org_id)
            comments_data = [
                _build_comment_dict(c, users_map, replies_by_comment) for c in comments_by_post.get(post.id, [])
            ]
            result.append(
                {
                    "id": post.id,
                    "user_id": post.user_id,
                    "user_type": author.user_type if author else "",
                    "author_name": (author.nickname or author.display_name or author.username) if author else "未知",
                    "content": post.content,
                    "images": post.images.split(",") if post.images else [],
                    "org_id": post.org_id,
                    "org_name": org.name if org else "",
                    "like_count": like_count_map.get(post.id, 0),
                    "is_liked": post.id in is_liked_set,
                    "comment_count": len(comments_by_post.get(post.id, [])),
                    "comments": comments_data,
                    "is_hidden_by_admin": post.is_hidden_by_admin,
                    "visibility": post.visibility or "public",
                    "show_location": post.show_location if post.show_location is not None else True,
                    "time_ago": _time_ago(post.created_at),
                }
            )
        return result


def _time_ago(dt: Any) -> str:
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
        return cast(str, dt.strftime("%Y-%m-%d"))


def _hide_post(post_id: str, refresh_fn: Any) -> None:
    with get_db() as db:
        post = db.query(Post).filter(Post.id == post_id).first()
        if post:
            post.is_hidden_by_admin = True
            db.commit()
    ui.notify("已屏蔽此内容", type="info")
    if refresh_fn:
        refresh_fn()


def _unhide_post(post_id: str, refresh_fn: Any) -> None:
    with get_db() as db:
        post = db.query(Post).filter(Post.id == post_id).first()
        if post:
            post.is_hidden_by_admin = False
            db.commit()
    ui.notify("已解除屏蔽", type="positive")
    if refresh_fn:
        refresh_fn()


def _hide_comment(comment_id: str, refresh_fn: Any) -> None:
    with get_db() as db:
        comment = db.query(Comment).filter(Comment.id == comment_id).first()
        if comment:
            comment.is_hidden_by_admin = True
            db.commit()
    ui.notify("已屏蔽此评论", type="info")
    if refresh_fn:
        refresh_fn()


def _unhide_comment(comment_id: str, refresh_fn: Any) -> None:
    with get_db() as db:
        comment = db.query(Comment).filter(Comment.id == comment_id).first()
        if comment:
            comment.is_hidden_by_admin = False
            db.commit()
    ui.notify("已解除屏蔽", type="positive")
    if refresh_fn:
        refresh_fn()


def _delete_comment_by_author(comment_id: str, post_id: str, refresh_fn: Any) -> None:
    with get_db() as db:
        comment = db.query(Comment).filter(Comment.id == comment_id).first()
        if comment:
            comment.is_deleted_by_author = True
            db.commit()
    ui.notify("评论已删除", type="info")
    if refresh_fn:
        refresh_fn()


_reply_boxes: dict[str, Any] = {}


def _toggle_reply_box(comment_id: str) -> None:
    if comment_id in _reply_boxes:
        box = _reply_boxes[comment_id]
        box.set_value(not box.value)


def _add_reply(comment_id: str, input_elem: Any, refresh_fn: Any) -> None:
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


def _delete_reply_by_author(reply_id: str, refresh_fn: Any) -> None:
    with get_db() as db:
        reply = db.query(Reply).filter(Reply.id == reply_id).first()
        if reply:
            reply.is_deleted_by_author = True
            db.commit()
    ui.notify("回复已删除", type="info")
    if refresh_fn:
        refresh_fn()
