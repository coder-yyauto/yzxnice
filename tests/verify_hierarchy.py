#!/usr/bin/env python3
"""
验证年级-班级层级结构代码
"""

import sys

sys.path.insert(0, ".")

from core.models import User
from core.org_utils import get_classes, get_grades, get_schools
from database import get_db, init_db


def verify_structure():
    init_db()

    with get_db() as db:
        schools = get_schools(db)
        print(f"找到 {len(schools)} 所学校")

        for school in schools:
            print(f"\n学校: {school.name} ({school.school_code})")

            grades = get_grades(db, school.id)
            print(f"  有 {len(grades)} 个年级")

            for grade in grades:
                classes = get_classes(db, grade.id)

                # 计算该年级的学生总数
                grade_student_count = 0
                for cls in classes:
                    student_count = (
                        db.query(User)
                        .filter(
                            User.default_org_id == cls.id,
                            User.user_type == "student",
                            User.is_active,
                        )
                        .count()
                    )
                    grade_student_count += student_count

                print(f"  {grade.name}: {len(classes)} 个班级, {grade_student_count} 名学生")

                for cls in classes:
                    student_count = (
                        db.query(User)
                        .filter(
                            User.default_org_id == cls.id,
                            User.user_type == "student",
                            User.is_active,
                        )
                        .count()
                    )
                    if student_count > 0:
                        print(f"    {cls.name}: {student_count} 名学生")
                        # 显示前几个学生用户名
                        students = (
                            db.query(User)
                            .filter(
                                User.default_org_id == cls.id,
                                User.user_type == "student",
                                User.is_active,
                            )
                            .limit(3)
                            .all()
                        )
                        usernames = [s.username for s in students]
                        print(f"      示例: {', '.join(usernames)}")

    print("\n" + "=" * 60)
    print("验证完成!")
    print("=" * 60)


if __name__ == "__main__":
    verify_structure()
