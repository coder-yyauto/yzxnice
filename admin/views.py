from nicegui import APIRouter, app, ui

from core.auth import AuthManager
from core.models import Org, User, UserRole
from core.org_utils import get_classes, get_grades, get_schools
from core.permissions import can_assign_role, get_admin_school_ids, has_admin_page_access
from database import get_db

router = APIRouter()


def _get_admin_context(user):
    if user.get("user_type") == "admin":
        return True, None
    with get_db() as db:
        u = db.query(User).filter(User.id == user["user_id"]).first()
        if not u:
            return False, None
        admin_schools = get_admin_school_ids(db, u)
        if admin_schools:
            return False, list(admin_schools)
    return False, None


def _check_admin_access(user):
    if user.get("user_type") == "admin":
        return True
    with get_db() as db:
        u = db.query(User).filter(User.id == user["user_id"]).first()
        if u and has_admin_page_access(db, u):
            return True
    return False


@router.page("/admin")
async def admin_index():
    if not AuthManager.is_authenticated():
        ui.navigate.to("/login")
        return
    user = AuthManager.get_current_user()
    if not _check_admin_access(user):
        ui.notify("权限不足", type="negative")
        ui.navigate.to("/home")
        return

    from pyq.components import render_admin_navbar

    render_admin_navbar()
    with ui.column().classes("w-full p-6 min-h-screen bg-gray-50 items-center"):
        with ui.column().classes("w-full max-w-4xl"):
            ui.label("管理后台").classes("text-xl font-bold mb-4")
            with ui.row().classes("gap-4"):
                ui.button("组织管理", on_click=lambda: ui.navigate.to("/admin/org")).props("color=primary")
                ui.button("用户管理", on_click=lambda: ui.navigate.to("/admin/users")).props("color=primary")
                ui.button("权限管理", on_click=lambda: ui.navigate.to("/admin/roles")).props("color=primary")


@router.page("/admin/org")
async def admin_org():
    if not AuthManager.is_authenticated():
        ui.navigate.to("/login")
        return
    user = AuthManager.get_current_user()
    if not _check_admin_access(user):
        ui.navigate.to("/home")
        return

    is_super, admin_schools = _get_admin_context(user)

    from pyq.components import render_admin_navbar

    render_admin_navbar("/admin/org")

    with ui.column().classes("w-full min-h-screen bg-gray-50 items-center"):
        with ui.column().classes("w-full max-w-4xl p-6"):
            ui.label("组织管理").classes("text-xl font-bold mb-4")

            if is_super:
                with ui.row().classes("gap-2 mb-4"):
                    school_name_input = (
                        ui.input(label="学校名称", placeholder="如：实验一小").classes("w-48").props("outlined dense")
                    )
                    school_code_input = (
                        ui.input(label="学校代码", placeholder="如：xx001").classes("w-48").props("outlined dense")
                    )

                async def create_school():
                    name = school_name_input.value.strip()
                    code = school_code_input.value.strip()
                    if not name or not code:
                        ui.notify("请填写学校名称和代码", type="warning")
                        return
                    with get_db() as db:
                        existing = db.query(Org).filter(Org.school_code == code).first()
                        if existing:
                            ui.notify("学校代码已存在", type="negative")
                            return
                        root = db.query(Org).filter(Org.org_type == "root").first()
                        if not root:
                            root = Org(name="系统根组织", org_type="root")
                            db.add(root)
                            db.flush()
                        school = Org(name=name, org_type="school", school_code=code, parent_id=root.id)
                        db.add(school)
                        db.flush()
                        for g in range(1, 6):
                            grade = Org(
                                name=f"{g}年级",
                                org_type="grade",
                                parent_id=school.id,
                                grade_number=g,
                            )
                            db.add(grade)
                            db.flush()
                            for c in range(1, 7):
                                cls = Org(
                                    name=f"{g}年级{c}班",
                                    org_type="class",
                                    parent_id=grade.id,
                                    grade_number=g,
                                    class_number=c,
                                )
                                db.add(cls)
                        db.commit()
                    ui.notify(f"学校 {name} 创建成功，含5个年级30个班级", type="positive")
                    refresh_org_list()

                ui.button("创建学校", icon="add", on_click=create_school).props("color=primary")
            else:
                ui.label("仅超级管理员可创建学校").classes("text-gray-400 text-sm mb-4")

            org_container = ui.column().classes("w-full mt-4")
            refresh_org_list = lambda: _refresh_orgs(org_container, admin_schools)
            _refresh_orgs(org_container, admin_schools)


def _refresh_orgs(container, admin_schools=None):
    container.clear()
    with container, get_db() as db:
        schools = get_schools(db)
        if admin_schools:
            schools = [s for s in schools if s.id in admin_schools]
        for school in schools:
            with ui.expansion(f"{school.name} ({school.school_code})", icon="school").classes("w-full"):
                grades = get_grades(db, school.id)
                for grade in grades:
                    with ui.expansion(grade.name, icon="grade").classes("pl-6"):
                        classes = get_classes(db, grade.id)
                        with ui.row().classes("gap-2"):
                            for cls in classes:
                                count = (
                                    db.query(User)
                                    .filter(User.default_org_id == cls.id, User.user_type == "student")
                                    .count()
                                )
                                ui.badge(f"{cls.name} ({count}人)", color="blue").classes("cursor-pointer")


@router.page("/admin/users")
async def admin_users():
    if not AuthManager.is_authenticated():
        ui.navigate.to("/login")
        return
    user = AuthManager.get_current_user()
    if not _check_admin_access(user):
        ui.navigate.to("/home")
        return

    is_super, admin_schools = _get_admin_context(user)

    from pyq.components import render_admin_navbar

    render_admin_navbar("/admin/users")

    with ui.column().classes("w-full min-h-screen bg-gray-50 items-center"):
        with ui.column().classes("w-full max-w-4xl p-6"):
            ui.label("用户管理").classes("text-xl font-bold mb-4")

            with ui.row().classes("gap-2 mb-4 items-end"):
                with get_db() as db:
                    all_schools = get_schools(db)
                    if admin_schools:
                        all_schools = [s for s in all_schools if s.id in admin_schools]
                    school_opts = {str(s.id): f"{s.name} ({s.school_code})" for s in all_schools}

                school_select = ui.select(
                    label="选择学校",
                    options=school_opts,
                    with_input=True,
                ).classes("w-64")
                if school_opts:
                    school_select.value = list(school_opts.keys())[0]

                action_select = ui.select(
                    label="操作",
                    options={
                        "gen_students": "批量生成学生账号",
                        "gen_teacher": "创建教师账号",
                        "reset_pwd": "重置密码",
                    },
                    value="gen_students",
                ).classes("w-48")
                action_btn = ui.button("执行", on_click=lambda: None).props("color=primary")

            user_table_container = ui.column().classes("w-full mt-4")

            async def do_action():
                sid = school_select.value
                action = action_select.value
                if not sid:
                    ui.notify("请选择学校", type="warning")
                    return

                if action == "gen_students":
                    _gen_students(sid, user_table_container, admin_schools)
                elif action == "gen_teacher":
                    _show_teacher_dialog(sid, user_table_container, admin_schools)
                elif action == "reset_pwd":
                    _reset_passwords(sid)

            action_btn.on("click", do_action)

            _refresh_user_table(user_table_container, admin_schools)


def _gen_students(school_id, container, admin_schools=None):
    from config import config as cfg

    if admin_schools and school_id not in admin_schools:
        ui.notify("无权操作此学校", type="negative")
        return

    with get_db() as db:
        school = db.query(Org).filter(Org.id == school_id).first()
        if not school:
            ui.notify("学校不存在", type="negative")
            return

        grades = get_grades(db, school_id)
        count = 0
        for grade in grades:
            classes = get_classes(db, grade.id)
            for cls in classes:
                existing = db.query(User).filter(User.default_org_id == cls.id, User.user_type == "student").count()
                start = 2001 + existing
                for i in range(40 - existing):
                    if existing + i >= 40:
                        break
                    seq = existing + i + 1
                    username = f"{school.school_code}{grade.grade_number}{cls.class_number}{seq:02d}"
                    existing_user = db.query(User).filter(User.username == username).first()
                    if existing_user:
                        continue
                    student = User(
                        username=username,
                        display_name=f"学生{seq:02d}",
                        user_type="student",
                        default_org_id=cls.id,
                    )
                    student.set_password(cfg.DEFAULT_PASSWORD)
                    db.add(student)
                    count += 1
        db.commit()
    ui.notify(f"生成 {count} 个学生账号，密码: {cfg.DEFAULT_PASSWORD}", type="positive")
    _refresh_user_table(container, admin_schools)


def _show_teacher_dialog(school_id, container, admin_schools=None):
    from config import config as cfg

    if admin_schools and school_id not in admin_schools:
        ui.notify("无权操作此学校", type="negative")
        return

    with ui.dialog() as dialog, ui.card().classes("w-96"):
        ui.label("创建教师账号").classes("text-lg font-bold mb-4")
        name_input = ui.input(label="姓名", placeholder="教师姓名").classes("w-full").props("outlined dense")
        username_input = ui.input(label="用户名", placeholder="如：Txx001001").classes("w-full").props("outlined dense")

        async def create():
            name = name_input.value.strip()
            uname = username_input.value.strip()
            if not name or not uname:
                ui.notify("请填写完整", type="warning")
                return
            with get_db() as db:
                existing = db.query(User).filter(User.username == uname).first()
                if existing:
                    ui.notify("用户名已存在", type="negative")
                    return
                teacher = User(
                    username=uname,
                    display_name=name,
                    user_type="teacher",
                    default_org_id=school_id,
                )
                teacher.set_password(cfg.DEFAULT_PASSWORD)
                db.add(teacher)
                db.commit()
            ui.notify(f"教师 {name} 创建成功，密码: {cfg.DEFAULT_PASSWORD}", type="positive")
            dialog.close()
            _refresh_user_table(container, admin_schools)

        with ui.row().classes("w-full justify-end gap-2 mt-4"):
            ui.button("取消", on_click=dialog.close).props("flat")
            ui.button("创建", on_click=create).props("color=primary")

    dialog.open()


def _reset_passwords(school_id, admin_schools=None):
    from config import config as cfg

    if admin_schools and school_id not in admin_schools:
        ui.notify("无权操作此学校", type="negative")
        return

    with get_db() as db:
        school = db.query(Org).filter(Org.id == school_id).first()
        if not school:
            return
        grades = get_grades(db, school_id)
        count = 0
        for grade in grades:
            classes = get_classes(db, grade.id)
            for cls in classes:
                students = db.query(User).filter(User.default_org_id == cls.id, User.user_type == "student").all()
                for s in students:
                    s.set_password(cfg.DEFAULT_PASSWORD)
                    count += 1
        teachers = db.query(User).filter(User.default_org_id == school_id, User.user_type == "teacher").all()
        for t in teachers:
            t.set_password(cfg.DEFAULT_PASSWORD)
            count += 1
        db.commit()
    ui.notify(f"已重置 {count} 个账号密码为: {cfg.DEFAULT_PASSWORD}", type="positive")


def _refresh_user_table(container, admin_schools=None):
    container.clear()
    with container, get_db() as db:
        schools = get_schools(db)
        if admin_schools:
            schools = [s for s in schools if s.id in admin_schools]
        for school in schools:
            with ui.expansion(f"{school.name}", icon="school").classes("w-full mb-2"):
                teachers = (
                    db.query(User)
                    .filter(
                        User.default_org_id == school.id,
                        User.user_type == "teacher",
                        User.is_active == True,
                    )
                    .all()
                )
                if teachers:
                    with ui.expansion(f"教师 ({len(teachers)}人)").classes("pl-4"):
                        rows = [
                            {
                                "用户名": t.username,
                                "姓名": t.display_name or "",
                                "状态": "正常" if t.is_active else "停用",
                                "类型": "教师",
                            }
                            for t in teachers
                        ]
                        ui.table(
                            columns=[
                                {"name": "用户名", "label": "用户名", "field": "用户名"},
                                {"name": "姓名", "label": "姓名", "field": "姓名"},
                                {"name": "状态", "label": "状态", "field": "状态"},
                                {"name": "类型", "label": "类型", "field": "类型"},
                            ],
                            rows=rows,
                        ).classes("w-full")

                grades = get_grades(db, school.id)
                for grade in grades:
                    classes = get_classes(db, grade.id)
                    grade_student_count = sum(
                        db.query(User)
                        .filter(
                            User.default_org_id == cls.id,
                            User.user_type == "student",
                            User.is_active == True,
                        )
                        .count()
                        for cls in classes
                    )

                    if grade_student_count > 0:
                        with ui.expansion(f"{grade.name} ({grade_student_count}人)", icon="grade").classes("pl-4"):
                            for cls in classes:
                                students = (
                                    db.query(User)
                                    .filter(
                                        User.default_org_id == cls.id,
                                        User.user_type == "student",
                                        User.is_active == True,
                                    )
                                    .all()
                                )
                                if students:
                                    with ui.expansion(f"{cls.name} ({len(students)}人)").classes("pl-6"):
                                        rows = [
                                            {
                                                "用户名": s.username,
                                                "姓名": s.display_name or "",
                                                "状态": "正常" if s.is_active else "停用",
                                                "类型": "学生",
                                            }
                                            for s in students[:10]
                                        ]
                                        if rows:
                                            ui.table(
                                                columns=[
                                                    {"name": "用户名", "label": "用户名", "field": "用户名"},
                                                    {"name": "姓名", "label": "姓名", "field": "姓名"},
                                                    {"name": "状态", "label": "状态", "field": "状态"},
                                                    {"name": "类型", "label": "类型", "field": "类型"},
                                                ],
                                                rows=rows,
                                            ).classes("w-full")
                                        if len(students) > 10:
                                            ui.label(f"...等共 {len(students)} 人").classes("text-xs text-gray-400")

        if not admin_schools:
            admins = db.query(User).filter(User.user_type == "admin").all()
            if admins:
                with ui.expansion("系统管理员", icon="admin_panel_settings").classes("w-full mb-2"):
                    rows = [
                        {
                            "用户名": a.username,
                            "姓名": a.display_name or "",
                            "状态": "正常" if a.is_active else "停用",
                            "类型": "管理员",
                        }
                        for a in admins
                    ]
                    ui.table(
                        columns=[
                            {"name": "用户名", "label": "用户名", "field": "用户名"},
                            {"name": "姓名", "label": "姓名", "field": "姓名"},
                            {"name": "状态", "label": "状态", "field": "状态"},
                            {"name": "类型", "label": "类型", "field": "类型"},
                        ],
                        rows=rows,
                    ).classes("w-full")


@router.page("/admin/roles")
async def admin_roles():
    if not AuthManager.is_authenticated():
        ui.navigate.to("/login")
        return
    user = AuthManager.get_current_user()
    if not _check_admin_access(user):
        ui.navigate.to("/home")
        return

    is_super, admin_schools = _get_admin_context(user)

    from pyq.components import render_admin_navbar

    render_admin_navbar("/admin/roles")

    with ui.column().classes("w-full min-h-screen bg-gray-50 items-center"):
        with ui.column().classes("w-full max-w-4xl p-6"):
            ui.label("权限管理").classes("text-xl font-bold mb-4")

            with ui.row().classes("gap-2 mb-4 items-end"):
                with get_db() as db:
                    all_schools = get_schools(db)
                    if admin_schools:
                        all_schools = [s for s in all_schools if s.id in admin_schools]
                    school_opts = {str(s.id): f"{s.name} ({s.school_code})" for s in all_schools}

                school_select = ui.select(label="选择学校", options=school_opts, with_input=True).classes("w-64")
                if school_opts:
                    school_select.value = list(school_opts.keys())[0]

            role_container = ui.column().classes("w-full")

            async def load_roles():
                sid = school_select.value
                if not sid:
                    return
                _refresh_roles(role_container, sid, is_super)

            school_select.on("update:model-value", load_roles)

            if school_opts:
                _refresh_roles(role_container, list(school_opts.keys())[0], is_super)


def _refresh_roles(container, school_id, is_super):
    container.clear()
    with container, get_db() as db:
        school = db.query(Org).filter(Org.id == school_id).first()
        if not school:
            return

        teachers = db.query(User).filter(User.default_org_id == school_id, User.user_type == "teacher").all()
        if not teachers:
            ui.label("该学校暂无教师，请先创建教师账号").classes("text-gray-400")
            return

        teacher_opts = {str(t.id): f"{t.display_name or t.username}" for t in teachers}

        grades = get_grades(db, school_id)

        org_opts = {str(school.id): f"{school.name}(全校)"}
        for grade in grades:
            org_opts[str(grade.id)] = f"{grade.name}"
            classes = get_classes(db, grade.id)
            for cls in classes:
                org_opts[str(cls.id)] = f"  {cls.name}"

        if is_super:
            role_options = {
                "school_admin": "学校管理员",
                "grade_admin": "年级管理员",
                "class_admin": "班级管理员",
            }
        else:
            role_options = {
                "grade_admin": "年级管理员",
                "class_admin": "班级管理员",
            }

        with ui.row().classes("gap-2 items-end"):
            user_select = ui.select(label="选择教师", options=teacher_opts).classes("w-48")
            role_select = ui.select(
                label="角色",
                options=role_options,
                value=list(role_options.keys())[0],
            ).classes("w-40")
            scope_select = ui.select(label="管辖范围", options=org_opts).classes("w-48")

        async def assign_role():
            uid = user_select.value
            role = role_select.value
            scope = scope_select.value
            if not uid or not role or not scope:
                ui.notify("请完整选择", type="warning")
                return
            with get_db() as db2:
                assigner = db2.query(User).filter(User.id == app.storage.user.get("user_id")).first()
                if not assigner:
                    ui.notify("用户不存在", type="negative")
                    return
                if not can_assign_role(db2, assigner, role, scope):
                    ui.notify("权限不足：校级管理员只能由超级管理员赋权", type="negative")
                    return
                existing = (
                    db2.query(UserRole)
                    .filter(
                        UserRole.user_id == uid,
                        UserRole.role == role,
                        UserRole.scope_org_id == scope,
                    )
                    .first()
                )
                if existing:
                    ui.notify("该授权已存在", type="warning")
                    return
                db2.add(UserRole(user_id=uid, role=role, scope_org_id=scope))
                db2.commit()
            ui.notify("授权成功", type="positive")
            _refresh_roles(container, school_id, is_super)

        ui.button("授权", icon="add", on_click=assign_role).props("color=primary").classes("mt-2")

        if not is_super:
            ui.label("提示：校级管理员只能由超级管理员赋权").classes("text-xs text-amber-600 mt-2")

        ui.label("当前授权").classes("text-md font-bold mt-4 mb-2")
        roles = (
            db.query(UserRole).join(User, UserRole.user_id == User.id).filter(User.default_org_id == school_id).all()
        )
        if roles:
            rows = []
            for r in roles:
                u = db.query(User).filter(User.id == r.user_id).first()
                o = db.query(Org).filter(Org.id == r.scope_org_id).first()
                role_name = {
                    "school_admin": "学校管理员",
                    "grade_admin": "年级管理员",
                    "class_admin": "班级管理员",
                }.get(r.role, r.role)
                rows.append(
                    {
                        "教师": u.display_name or u.username if u else "?",
                        "角色": role_name,
                        "管辖范围": o.name if o else "?",
                        "role_id": r.id,
                    }
                )

            def _make_delete_handler(rid):
                async def handler():
                    with get_db() as db2:
                        assigner = db2.query(User).filter(User.id == app.storage.user.get("user_id")).first()
                        if not assigner:
                            return
                        role_obj = db2.query(UserRole).filter(UserRole.id == rid).first()
                        if not role_obj:
                            return
                        if assigner.user_type != "admin":
                            if role_obj.role == "school_admin":
                                ui.notify("仅超级管理员可撤销校级管理员", type="negative")
                                return
                            admin_schools = get_admin_school_ids(db2, assigner)
                            scope_ancestors = []
                            cur = db2.query(Org).filter(Org.id == role_obj.scope_org_id).first()
                            while cur:
                                scope_ancestors.append(cur.id)
                                cur = db2.query(Org).filter(Org.id == cur.parent_id).first() if cur.parent_id else None
                            if not (admin_schools & set(scope_ancestors)):
                                ui.notify("权限不足", type="negative")
                                return
                        db2.delete(role_obj)
                        db2.commit()
                    ui.notify("已撤销授权", type="positive")
                    _refresh_roles(container, school_id, is_super)

                return handler

            with ui.column().classes("w-full gap-2"):
                for row in rows:
                    with ui.row().classes("w-full items-center bg-white rounded p-3 shadow-sm"):
                        ui.label(row["教师"]).classes("w-32 text-sm")
                        ui.badge(row["角色"], color="blue").classes("mr-2")
                        ui.label(row["管辖范围"]).classes("flex-1 text-sm text-gray-600")
                        ui.button(
                            icon="delete",
                            on_click=_make_delete_handler(row["role_id"]),
                        ).props("flat dense size=sm color=red").tooltip("撤销授权")
        else:
            ui.label("暂无授权记录").classes("text-gray-400")
