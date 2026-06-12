import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from config import config
from core.models import Org, User
from database import get_db, init_db


def cleanup_data() -> None:
    """清洗数据：只保留根组织和超级管理员"""

    # 删除数据库文件
    db_path = config.DATABASE_URL.replace("duckdb:///", "").replace("duckdb://", "")
    if db_path and db_path != ":memory:" and os.path.exists(db_path):
        print(f"正在删除数据库文件: {db_path}")
        os.remove(db_path)
        print("数据库文件已删除")

    # 重新初始化数据库
    print("\n正在重新初始化数据库...")
    init_db()

    # 创建根组织和超级管理员
    with get_db() as db:
        print("正在创建根组织和超级管理员...")

        root = Org(name="系统根组织", org_type="root")
        db.add(root)
        db.flush()

        admin = User(
            username="admin",
            display_name="系统管理员",
            user_type="admin",
            default_org_id=root.id,
        )
        admin.set_password(config.DEFAULT_PASSWORD)
        db.add(admin)
        db.commit()

        print(f"\n根组织ID: {root.id}")
        print(f"超级管理员ID: {admin.id}")

        # 验证结果
        print("\n" + "=" * 60)
        print("数据清洗完成!")
        print("=" * 60)

        org_count = db.query(Org).count()
        user_count = db.query(User).count()

        print("\n当前数据统计:")
        print(f"  组织总数: {org_count}")
        print(f"  用户总数: {user_count}")

        print(f"\n保留的根组织: {root.name} ({root.org_type})")
        print(f"保留的超级管理员: {admin.username} ({admin.display_name})")


if __name__ == "__main__":
    print("=" * 60)
    print("开始清洗数据")
    print("=" * 60)
    print("警告：此操作将删除所有数据！")
    print("只保留根组织和超级管理员（admin）")
    print("=" * 60)

    response = input("\n确认继续吗？(yes/no): ")
    if response.lower() == "yes":
        cleanup_data()
    else:
        print("操作已取消")
