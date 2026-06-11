import logging

from sqlalchemy import text

from database import engine

logger = logging.getLogger(__name__)


def migrate():
    """Add new columns and tables for admin blocking and comment replies"""

    migrations = [
        "ALTER TABLE post ADD COLUMN is_hidden_by_admin BOOLEAN DEFAULT FALSE",
        "ALTER TABLE comment ADD COLUMN is_hidden_by_admin BOOLEAN DEFAULT FALSE",
        "ALTER TABLE comment ADD COLUMN is_deleted_by_author BOOLEAN DEFAULT FALSE",
        """
        CREATE TABLE IF NOT EXISTS reply (
            id VARCHAR(36) PRIMARY KEY,
            comment_id VARCHAR(36) NOT NULL,
            user_id VARCHAR(36) NOT NULL,
            content TEXT NOT NULL,
            is_hidden_by_admin BOOLEAN DEFAULT FALSE,
            is_deleted_by_author BOOLEAN DEFAULT FALSE,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (comment_id) REFERENCES comment(id),
            FOREIGN KEY (user_id) REFERENCES "user"(id)
        )
        """,
    ]

    with engine.connect() as conn:
        for migration in migrations:
            try:
                conn.execute(text(migration))
                conn.commit()
                print(f"执行成功: {migration[:80]}...")
            except Exception as e:
                conn.rollback()
                if "already exists" in str(e) or "duplicate column" in str(e):
                    print(f"已存在，跳过: {migration[:80]}...")
                else:
                    print(f"执行失败: {e}")
                    logger.error("迁移失败: %s", migration[:80], exc_info=True)

    print("数据库迁移完成")


if __name__ == "__main__":
    migrate()
