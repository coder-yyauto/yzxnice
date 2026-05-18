from __future__ import annotations

import time
from typing import Any

from nicegui import app

from core.models import Org, User


class AuthManager:

    @staticmethod
    def login(username: str, password: str) -> dict[str, Any]:
        from database import get_db
        from core.org_utils import get_user_school
        from core.permissions import has_any_admin_role

        with get_db() as db:
            user: User | None = db.query(User).filter(User.username == username).first()
            if not user or not user.check_password(password):
                raise ValueError("用户名或密码错误")
            if not user.is_active:
                raise ValueError("账号已被停用")

            user_info: dict[str, Any] = user.to_dict()

            school: Org | None = get_user_school(db, user)
            if school:
                user_info["school_id"] = school.id
                user_info["school_name"] = school.name
                user_info["school_code"] = school.school_code
            else:
                user_info["school_id"] = None
                user_info["school_name"] = ""
                user_info["school_code"] = ""

            org_obj: Org | None = db.query(Org).filter(Org.id == user.default_org_id).first()
            user_info["org_name"] = org_obj.name if org_obj else ""

            from core.permissions import has_admin_page_access

            user_info["is_admin"] = user.user_type == "admin" or has_any_admin_role(db, user)
            user_info["has_admin_page"] = user.user_type == "admin" or has_admin_page_access(db, user)

            return user_info

    @staticmethod
    def set_session(user_info: dict[str, Any]) -> None:
        app.storage.user.update(
            {
                "user_id": user_info["id"],
                "username": user_info["username"],
                "display_name": user_info.get("display_name", ""),
                "user_type": user_info.get("user_type", "student"),
                "is_admin": user_info.get("is_admin", False),
                "has_admin_page": user_info.get("has_admin_page", False),
                "school_id": user_info.get("school_id"),
                "school_name": user_info.get("school_name", ""),
                "school_code": user_info.get("school_code", ""),
                "default_org_id": user_info.get("default_org_id"),
                "org_name": user_info.get("org_name", ""),
                "login_time": time.time(),
            }
        )

    @staticmethod
    def clear_session() -> None:
        app.storage.user.clear()

    @staticmethod
    def get_current_user() -> dict[str, Any] | None:
        user_id: str | None = app.storage.user.get("user_id")
        if not user_id:
            return None
        return {
            "user_id": user_id,
            "username": app.storage.user.get("username", ""),
            "display_name": app.storage.user.get("display_name", ""),
            "user_type": app.storage.user.get("user_type", "student"),
            "is_admin": app.storage.user.get("is_admin", False),
            "has_admin_page": app.storage.user.get("has_admin_page", False),
            "school_id": app.storage.user.get("school_id"),
            "school_name": app.storage.user.get("school_name", ""),
            "school_code": app.storage.user.get("school_code", ""),
            "default_org_id": app.storage.user.get("default_org_id"),
            "org_name": app.storage.user.get("org_name", ""),
        }

    @staticmethod
    def is_authenticated() -> bool:
        return bool(app.storage.user.get("user_id"))

    @staticmethod
    def is_admin() -> bool:
        return bool(app.storage.user.get("is_admin"))
