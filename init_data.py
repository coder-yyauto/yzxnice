import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from config import config
from core.models import Org, User, UserRole
from database import get_db, init_db


def init_data():
    init_db()

    with get_db() as db:
        root = db.query(Org).filter(Org.org_type == "root").first()
        if not root:
            root = Org(name="系统根组织", org_type="root")
            db.add(root)
            db.commit()

        _create_school(db, "向阳小学", "xy001")
        _create_school(db, "育才小学", "yc002")

        root = db.query(Org).filter(Org.org_type == "root").first()
        admin = db.query(User).filter(User.username == "admin").first()
        if not admin:
            admin = User(
                username="admin",
                display_name="系统管理员",
                user_type="admin",
                default_org_id=root.id if root else None,
            )
            admin.set_password(config.DEFAULT_PASSWORD)
            db.add(admin)
            db.commit()

        _gen_all_students(db)
        _ensure_teachers(db)

    print("=" * 60)
    print("数据初始化完成!")
    print("=" * 60)
    print("系统管理员: admin")
    print()
    _print_account_info()


def _create_school(db, name, code):
    existing = db.query(Org).filter(Org.school_code == code).first()
    if existing:
        print(f"学校 {name} ({code}) 已存在，跳过")
        return existing

    root = db.query(Org).filter(Org.org_type == "root").first()
    if not root:
        root = Org(name="系统根组织", org_type="root")
        db.add(root)
        db.flush()

    school = Org(name=name, org_type="school", school_code=code, parent_id=root.id)
    db.add(school)
    db.flush()

    for g in range(1, 6):
        grade = Org(name=f"{g}年级", org_type="grade", parent_id=school.id, grade_number=g)
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
    print(f"创建学校: {name} ({code}) - 5个年级30个班级")
    return school


def _gen_all_students(db):
    schools = db.query(Org).filter(Org.org_type == "school").all()
    for school in schools:
        grades = db.query(Org).filter(Org.org_type == "grade", Org.parent_id == school.id).all()
        for grade in grades:
            classes = db.query(Org).filter(Org.org_type == "class", Org.parent_id == grade.id).all()
            for cls in classes:
                existing_count = (
                    db.query(User).filter(User.default_org_id == cls.id, User.user_type == "student").count()
                )
                if existing_count >= 40:
                    continue

                for i in range(40):
                    seq = i + 1  # 1-40
                    username = f"{school.school_code}{grade.grade_number}{cls.class_number}{seq:02d}"
                    existing = db.query(User).filter(User.username == username).first()
                    if existing:
                        continue
                    student = User(
                        username=username,
                        display_name=f"学生{seq:02d}",
                        user_type="student",
                        default_org_id=cls.id,
                    )
                    student.set_password(config.DEFAULT_PASSWORD)
                    db.add(student)
    db.commit()
    total = db.query(User).filter(User.user_type == "student").count()
    print(f"学生账号总数: {total}")


def _ensure_teachers(db):
    schools = db.query(Org).filter(Org.org_type == "school").all()
    for school in schools:
        code = school.school_code
        teacher_name = f"T{code}001"
        existing = db.query(User).filter(User.username == teacher_name).first()
        if not existing:
            teacher = User(
                username=teacher_name,
                display_name=f"{school.name}教师",
                user_type="teacher",
                default_org_id=school.id,
            )
            teacher.set_password(config.DEFAULT_PASSWORD)
            db.add(teacher)
    db.commit()

    for school in schools:
        code = school.school_code
        admin_name = f"T{code}admin"
        existing = db.query(User).filter(User.username == admin_name).first()
        if not existing:
            admin_teacher = User(
                username=admin_name,
                display_name=f"{school.name}管理员",
                user_type="teacher",
                default_org_id=school.id,
            )
            admin_teacher.set_password(config.DEFAULT_PASSWORD)
            db.add(admin_teacher)
            db.flush()

            db.add(UserRole(user_id=admin_teacher.id, role="school_admin", scope_org_id=school.id))

    db.commit()
    total = db.query(User).filter(User.user_type == "teacher").count()
    print(f"教师账号总数: {total}")


def _print_account_info():
    with get_db() as db:
        schools = db.query(Org).filter(Org.org_type == "school").all()
        for school in schools:
            code = school.school_code
            print(f"\n--- {school.name} ({code}) ---")
            print(f"  教师: T{code}001")
            print(f"  管理员: T{code}admin")
            print(f"  学生示例: {code}1101 ~ {code}1140 (格式: 学校代码+年级+班级+两位序号)")
            print("  学生密码: 系统默认密码")

            grade = (
                db.query(Org).filter(Org.org_type == "grade", Org.parent_id == school.id, Org.grade_number == 1).first()
            )
            if grade:
                cls = (
                    db.query(Org)
                    .filter(Org.org_type == "class", Org.parent_id == grade.id, Org.class_number == 1)
                    .first()
                )
                if cls:
                    print(
                        f"  例: {cls.name} 学生 "
                        f"{code}{cls.grade_number}{cls.class_number}01~{code}{cls.grade_number}{cls.class_number}40"
                    )


if __name__ == "__main__":
    init_data()
