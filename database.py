import logging
import os
from collections.abc import Iterator
from contextlib import contextmanager
from typing import Any

from sqlalchemy import create_engine
from sqlalchemy.orm import declarative_base, scoped_session, sessionmaker
from sqlalchemy.pool import StaticPool

from config import config

logger = logging.getLogger(__name__)

_db_url = config.DATABASE_URL

if _db_url.startswith("duckdb"):
    db_path = _db_url.replace("duckdb:///", "").replace("duckdb://", "")
    if db_path and db_path != ":memory:":
        os.makedirs(os.path.dirname(db_path) or ".", exist_ok=True)
    engine = create_engine(
        _db_url,
        echo=False,
        poolclass=StaticPool,
    )
else:
    engine = create_engine(_db_url, echo=False, pool_pre_ping=True, pool_size=10, max_overflow=20)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine, expire_on_commit=False)
Base = declarative_base()

ScopedSession = scoped_session(SessionLocal)


@contextmanager
def get_db() -> Iterator[Any]:
    session = ScopedSession()
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise


def init_db() -> None:
    Base.metadata.create_all(bind=engine, checkfirst=True)
    _migrate_post_visibility()
    _migrate_user_nickname()
    print("数据库初始化完成")


def _migrate_post_visibility() -> None:
    from sqlalchemy import text

    new_cols = [
        ("visibility", "VARCHAR(20)", "'public'"),
        ("show_location", "BOOLEAN", "TRUE"),
        ("visible_to_orgs", "TEXT", "NULL"),
        ("excluded_orgs", "TEXT", "NULL"),
    ]
    with engine.connect() as conn:
        for col_name, col_type, default in new_cols:
            try:
                conn.execute(text(f"ALTER TABLE post ADD COLUMN {col_name} {col_type} DEFAULT {default}"))
                conn.commit()
                logger.info("Migration: added column post.%s", col_name)
            except Exception as e:
                conn.rollback()
                msg = str(e)
                if "already exists" not in msg.lower():
                    logger.warning("Migration column %s failed: %s", col_name, e)
    logger.info("post表字段迁移完成")


def _migrate_user_nickname() -> None:
    from sqlalchemy import text

    new_cols = [
        ("nickname", "VARCHAR(100)", "NULL"),
    ]
    with engine.connect() as conn:
        for col_name, col_type, default in new_cols:
            try:
                conn.execute(text(f'ALTER TABLE "user" ADD COLUMN {col_name} {col_type} DEFAULT {default}'))
                conn.commit()
                logger.info("Migration: added column user.%s", col_name)
            except Exception as e:
                conn.rollback()
                msg = str(e)
                if "already exists" not in msg.lower():
                    logger.warning("Migration column user.%s failed: %s", col_name, e)
    logger.info("user表字段迁移完成")
