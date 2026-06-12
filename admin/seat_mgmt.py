import csv
import io
import logging
from typing import Any, cast

from nicegui import APIRouter, ui

from core.auth import AuthManager
from core.models import Org, User, UserRole
from core.org_utils import get_classes, get_grades, get_org_ancestors
from core.security import PasswordManager
from database import get_db

logger = logging.getLogger(__name__)

router = APIRouter()


def _resolve_role_class_ids(db: Any, role: UserRole) -> set[str]:
    """Resolve a single UserRole to the set of class Org IDs it covers."""
    scope = db.query(Org).filter(Org.id == role.scope_org_id).first()
    if not scope:
        return set()
    if scope.org_type == "class":
        return {scope.id}
    if scope.org_type == "grade":
        return {c.id for c in get_classes(db, scope.id)}
    if scope.org_type == "school":
        result: set[str] = set()
        for grade in get_grades(db, scope.id):
            result.update(c.id for c in get_classes(db, grade.id))
        return result
    return set()


def _get_managed_class_ids(user: dict[str, Any], db: Any) -> set[str]:
    """Return all class org IDs the user can manage seats for."""
    u = db.query(User).filter(User.id == user["user_id"]).first()
    if not u:
        return set()
    if u.user_type == "admin":
        classes = db.query(Org).filter(Org.org_type == "class", Org.is_active).all()
        return {c.id for c in classes}
    roles = db.query(UserRole).filter(UserRole.user_id == u.id).all()
    managed: set[str] = set()
    for role in roles:
        managed.update(_resolve_role_class_ids(db, role))
    return managed


def _has_seat_access(user: dict[str, Any]) -> bool:
    with get_db() as db:
        u = db.query(User).filter(User.id == user["user_id"]).first()
        if not u:
            return False
        if u.user_type == "admin":
            return True
        count = db.query(UserRole).filter(UserRole.user_id == u.id).count()
        return bool(count > 0)


def _build_school_class_index(db: Any, managed_ids: set[str]) -> dict[str, Any]:
    """Group managed class orgs under their parent school."""
    schools: dict[str, Any] = {}
    for cid in managed_ids:
        cls = db.query(Org).filter(Org.id == cid).first()
        if not cls:
            continue
        school = None
        for aid in get_org_ancestors(db, cid):
            org = db.query(Org).filter(Org.id == aid).first()
            if org and org.org_type == "school":
                school = org
                break
        if school:
            schools.setdefault(school.id, {"obj": school, "classes": []})
            schools[school.id]["classes"].append(cls)
    return schools


@router.page("/admin/seats")  # type: ignore[misc]
async def seat_management() -> None:
    if not AuthManager.is_authenticated():
        ui.navigate.to("/login")
        return
    user_data = cast(dict[str, Any], AuthManager.get_current_user())
    if not _has_seat_access(user_data):
        ui.notify("权限不足", type="negative")
        ui.navigate.to("/home")
        return

    from pyq.components import render_admin_navbar

    render_admin_navbar("/admin/seats")

    with (
        ui.column().classes("w-full min-h-screen bg-gray-50 items-center"),
        ui.column().classes("w-full max-w-4xl p-6"),
    ):
        ui.label("席位管理").classes("text-xl font-bold mb-4")

        with get_db() as db:
            managed_ids = _get_managed_class_ids(user_data, db)
            if not managed_ids:
                ui.label("没有可管理的班级").classes("text-gray-400")
                return

            schools = _build_school_class_index(db, managed_ids)

        for _sid, sdata in sorted(schools.items(), key=lambda x: x[1]["obj"].name):
            school = sdata["obj"]
            with ui.expansion(f"{school.name} ({school.school_code})", icon="school").classes("w-full"):
                for cls_obj in sorted(sdata["classes"], key=lambda c: (c.grade_number or 0, c.class_number or 0)):
                    _render_class_seat_row(cls_obj)


def _render_class_seat_row(cls_obj: Org) -> None:

    with ui.row().classes("w-full items-center gap-2 py-2 px-4 border-b border-gray-100"):
        with get_db() as db:
            student_count = (
                db.query(User)
                .filter(User.default_org_id == cls_obj.id, User.user_type == "student", User.is_active)
                .count()
            )
        ui.label(f"{cls_obj.name}").classes("text-sm font-medium w-32")
        ui.label(f"{student_count} 席位").classes("text-xs text-gray-500 w-16")

        ui.button("导出CSV", icon="download", on_click=lambda cid=cls_obj.id: _export_csv(cid)).props(
            "flat dense size=sm color=blue"
        )
        ui.button(
            "清空", icon="clear_all", on_click=lambda cid=cls_obj.id, cn=cls_obj.name: _clear_seats(cid, cn)
        ).props("flat dense size=sm color=orange")

        ui.upload(
            on_upload=_make_csv_upload_handler(class_id=cls_obj.id, class_name=cls_obj.name),
            auto_upload=True,
        ).props("accept=.csv label=导入CSV重置 color=green flat dense").classes("inline-block")


def _export_csv(class_id: str) -> None:
    with get_db() as db:
        cls = db.query(Org).filter(Org.id == class_id).first()
        if not cls:
            ui.notify("班级不存在", type="negative")
            return
        students = (
            db.query(User)
            .filter(User.default_org_id == class_id, User.user_type == "student", User.is_active)
            .order_by(User.username)
            .all()
        )

    output = io.StringIO()
    output.write("\ufeff")
    writer = csv.writer(output)
    writer.writerow(["用户名", "姓名", "昵称"])
    for s in students:
        writer.writerow([s.username, s.display_name or "", s.nickname or ""])

    csv_content = output.getvalue()
    filename = f"{cls.name}_席位表.csv"

    ui.download(
        csv_content.encode("utf-8"),
        filename,
        "text/csv; charset=utf-8",
    )
    ui.notify(f"已导出 {len(students)} 条席位", type="positive")


def _clear_seats(class_id: str, class_name: str) -> None:
    with get_db() as db:
        students = (
            db.query(User).filter(User.default_org_id == class_id, User.user_type == "student", User.is_active).all()
        )
        count = 0
        for s in students:
            if s.display_name or s.nickname:
                s.display_name = None
                s.nickname = None
                count += 1
        db.commit()
    ui.notify(f"[{class_name}] 已清空 {count} 条席位姓名/昵称", type="positive")


def _make_csv_upload_handler(class_id: str, class_name: str) -> Any:
    async def handler(e: Any) -> None:
        await _handle_csv_upload(e, class_id, class_name)

    return handler


async def _handle_csv_upload(e: Any, class_id: str, class_name: str) -> None:
    content = e.content
    try:
        text = content.decode("utf-8-sig") if isinstance(content, bytes) else str(content)
    except UnicodeDecodeError:
        ui.notify("CSV编码错误，请使用UTF-8编码", type="negative")
        return

    reader = csv.DictReader(io.StringIO(text))
    rows = list(reader)
    if not rows:
        ui.notify("CSV文件为空", type="warning")
        return

    new_password = PasswordManager.generate_random_password()

    with get_db() as db:
        updated = 0
        for row in rows:
            username = row.get("用户名", "").strip()
            if not username:
                continue
            student = (
                db.query(User).filter(User.username == username, User.user_type == "student", User.is_active).first()
            )
            if not student or student.default_org_id != class_id:
                continue
            display_name = row.get("姓名", "").strip() or None
            nickname = row.get("昵称", "").strip() or None
            student.display_name = display_name
            student.nickname = nickname
            student.set_password(new_password)
            updated += 1
        db.commit()

    ui.notify(
        f"[{class_name}] 已重置 {updated} 个席位，班级新密码: {new_password}",
        type="positive",
        timeout=0,
    )
