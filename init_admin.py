"""重置数据库并初始化超级管理员"""
import sys
import os

sys.path.insert(0, os.path.dirname(__file__))

from database import Base, engine, init_db, get_db
from core.models import Org, User, UserRole

db_path = "data/yzxnice.duckdb"
if os.path.exists(db_path):
    os.remove(db_path)
    print(f"已删除旧数据库: {db_path}")

init_db()

with get_db() as db:
    root = Org(name="系统根组织", org_type="root")
    db.add(root)
    db.flush()

    admin = User(
        username="emster",
        display_name="超级管理员",
        user_type="admin",
        default_org_id=root.id,
        is_active=True,
    )
    admin.set_password('ww0oKk,3w5t3r.')
    db.add(admin)
    db.flush()

    admin_role = UserRole(
        user_id=admin.id,
        role="super_admin",
        scope_org_id=root.id,
    )
    db.add(admin_role)

    db.commit()

    print(f"根组织: {root.name} (id={root.id})")
    print(f"超级管理员: {admin.username} (id={admin.id})")
    print("数据库重置完成")
