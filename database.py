import os
import logging
from contextlib import contextmanager

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
def get_db():
    session = ScopedSession()
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise


def init_db():
    from core.models import Comment, Like, Org, Post, Reply, User, UserRole

    Base.metadata.create_all(bind=engine, checkfirst=True)
    _migrate_post_visibility()
    print("数据库初始化完成")


def _migrate_post_visibility():
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
            except Exception:
                pass
        conn.commit()
    logger.info("post表字段迁移完成")
