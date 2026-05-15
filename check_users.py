#!/usr/bin/env python3
"""
检查数据库中的用户和组织
"""

import sys
sys.path.insert(0, '.')

from database import get_db, init_db
from core.models import User, Org

def check_data():
    init_db()
    
    with get_db() as db:
        print("=" * 60)
        print("组织统计:")
        print("=" * 60)
        org_types = db.query(Org.org_type).distinct().all()
        print(f"组织类型: {[ot[0] for ot in org_types]}")
        
        root_count = db.query(Org).filter(Org.org_type == "root").count()
        school_count = db.query(Org).filter(Org.org_type == "school").count()
        grade_count = db.query(Org).filter(Org.org_type == "grade").count()
        class_count = db.query(Org).filter(Org.org_type == "class").count()
        
        print(f"根组织: {root_count}")
        print(f"学校: {school_count}")
        print(f"年级: {grade_count}")
        print(f"班级: {class_count}")
        
        schools = db.query(Org).filter(Org.org_type == "school").all()
        for school in schools:
            print(f"\n学校: {school.name} ({school.school_code}) ID: {school.id}")
            grades = db.query(Org).filter(Org.org_type == "grade", Org.parent_id == school.id).all()
            for grade in grades:
                classes = db.query(Org).filter(Org.org_type == "class", Org.parent_id == grade.id).all()
                print(f"  {grade.name}: {len(classes)}个班级")
        
        print("\n" + "=" * 60)
        print("用户统计:")
        print("=" * 60)
        
        user_count = db.query(User).count()
        admin_count = db.query(User).filter(User.user_type == "admin").count()
        teacher_count = db.query(User).filter(User.user_type == "teacher").count()
        student_count = db.query(User).filter(User.user_type == "student").count()
        
        print(f"总用户数: {user_count}")
        print(f"管理员: {admin_count}")
        print(f"教师: {teacher_count}")
        print(f"学生: {student_count}")
        
        print("\n管理员用户:")
        admins = db.query(User).filter(User.user_type == "admin").all()
        for admin in admins:
            print(f"  {admin.username} ({admin.display_name}) - 默认组织: {admin.default_org_id}")
        
        print("\n教师用户:")
        teachers = db.query(User).filter(User.user_type == "teacher").all()
        for teacher in teachers:
            print(f"  {teacher.username} ({teacher.display_name}) - 默认组织: {teacher.default_org_id}")
            org = db.query(Org).filter(Org.id == teacher.default_org_id).first() if teacher.default_org_id else None
            if org:
                print(f"    所属组织: {org.name} ({org.org_type})")
        
        print("\n学生用户 (前20个):")
        students = db.query(User).filter(User.user_type == "student").limit(20).all()
        for student in students:
            print(f"  {student.username} ({student.display_name}) - 默认组织: {student.default_org_id}")
            org = db.query(Org).filter(Org.id == student.default_org_id).first() if student.default_org_id else None
            if org:
                print(f"    所属班级: {org.name} ({org.org_type})")
        
        if student_count > 20:
            print(f"  ... 还有 {student_count - 20} 个学生")
        
        print("\n" + "=" * 60)
        print("用户-组织关联检查:")
        print("=" * 60)
        
        # 检查没有默认组织的用户
        users_without_org = db.query(User).filter(User.default_org_id == None).all()
        if users_without_org:
            print(f"没有默认组织的用户 ({len(users_without_org)}个):")
            for user in users_without_org:
                print(f"  {user.username} ({user.user_type})")
        else:
            print("所有用户都有默认组织")
        
        # 检查默认组织不存在的用户
        users_with_invalid_org = []
        for user in db.query(User).filter(User.default_org_id != None).all():
            org = db.query(Org).filter(Org.id == user.default_org_id).first()
            if not org:
                users_with_invalid_org.append(user)
        
        if users_with_invalid_org:
            print(f"默认组织不存在的用户 ({len(users_with_invalid_org)}个):")
            for user in users_with_invalid_org:
                print(f"  {user.username} ({user.user_type}) - 组织ID: {user.default_org_id}")
        else:
            print("所有用户的默认组织都存在")

if __name__ == "__main__":
    check_data()