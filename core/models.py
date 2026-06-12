import uuid
from datetime import datetime
from typing import Any

from sqlalchemy import Boolean, Column, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import relationship

from database import Base


class Org(Base):  # type: ignore[misc]
    __tablename__ = "org"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    name = Column(String(100), nullable=False)
    org_type = Column(String(20), nullable=False)
    parent_id = Column(String(36), ForeignKey("org.id"), nullable=True)
    school_code = Column(String(50), unique=True, nullable=True)
    school_level = Column(String(20), nullable=True)
    grade_number = Column(Integer, nullable=True)
    class_number = Column(Integer, nullable=True)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    parent = relationship("Org", remote_side=[id], backref="children")

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": str(self.id),
            "name": str(self.name),
            "org_type": str(self.org_type),
            "parent_id": str(self.parent_id) if self.parent_id is not None else None,
            "school_code": str(self.school_code) if self.school_code is not None else None,
            "grade_number": int(self.grade_number) if self.grade_number is not None else None,
            "class_number": int(self.class_number) if self.class_number is not None else None,
        }


class User(Base):  # type: ignore[misc]
    __tablename__ = "user"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    username = Column(String(80), unique=True, nullable=False)
    password_hash = Column(String(512), nullable=False)
    display_name = Column(String(100), nullable=True)
    nickname = Column(String(100), nullable=True)
    user_type = Column(String(20), nullable=False, default="student")
    default_org_id = Column(String(36), ForeignKey("org.id"), nullable=True)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    default_org = relationship("Org", foreign_keys=[default_org_id])
    roles = relationship("UserRole", back_populates="user", cascade="all, delete-orphan")
    posts = relationship("Post", back_populates="author")

    def set_password(self, password: str) -> None:
        from core.security import PasswordManager

        self.password_hash = PasswordManager.hash_password(password)

    def check_password(self, password: str) -> bool:
        from core.security import PasswordManager

        return PasswordManager.verify_password(self.password_hash, password)

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": str(self.id),
            "username": str(self.username),
            "display_name": str(self.display_name) if self.display_name is not None else None,
            "nickname": str(self.nickname) if self.nickname is not None else None,
            "user_type": str(self.user_type),
            "default_org_id": str(self.default_org_id) if self.default_org_id is not None else None,
            "is_active": bool(self.is_active),
        }


class UserRole(Base):  # type: ignore[misc]
    __tablename__ = "user_role"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = Column(String(36), ForeignKey("user.id"), nullable=False)
    role = Column(String(30), nullable=False)
    scope_org_id = Column(String(36), ForeignKey("org.id"), nullable=False)

    user = relationship("User", back_populates="roles")
    scope_org = relationship("Org")

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": str(self.id),
            "user_id": str(self.user_id),
            "role": str(self.role),
            "scope_org_id": str(self.scope_org_id),
        }


class Post(Base):  # type: ignore[misc]
    __tablename__ = "post"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = Column(String(36), ForeignKey("user.id"), nullable=False)
    content = Column(Text, nullable=False)
    images = Column(Text, nullable=True)
    org_id = Column(String(36), ForeignKey("org.id"), nullable=False)
    visible_org_id = Column(String(36), ForeignKey("org.id"), nullable=True)
    is_hidden = Column(Boolean, default=False)
    is_hidden_by_admin = Column(Boolean, default=False)
    visibility = Column(String(20), default="public")
    show_location = Column(Boolean, default=True)
    visible_to_orgs = Column(Text, nullable=True)
    excluded_orgs = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    author = relationship("User", back_populates="posts")
    org = relationship("Org", foreign_keys=[org_id])
    visible_org = relationship("Org", foreign_keys=[visible_org_id])
    likes = relationship("Like", back_populates="post", cascade="all, delete-orphan")
    comments = relationship("Comment", back_populates="post", cascade="all, delete-orphan")

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": str(self.id),
            "user_id": str(self.user_id),
            "content": str(self.content),
            "images": self.images.split(",") if self.images else [],
            "org_id": str(self.org_id),
            "visible_org_id": str(self.visible_org_id) if self.visible_org_id is not None else None,
            "is_hidden": bool(self.is_hidden),
            "is_hidden_by_admin": bool(self.is_hidden_by_admin),
            "visibility": str(self.visibility) if self.visibility else "public",
            "show_location": bool(self.show_location) if self.show_location is not None else True,
            "visible_to_orgs": self.visible_to_orgs.split(",") if self.visible_to_orgs else [],
            "excluded_orgs": self.excluded_orgs.split(",") if self.excluded_orgs else [],
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }


class Like(Base):  # type: ignore[misc]
    __tablename__ = "like"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    post_id = Column(String(36), ForeignKey("post.id"), nullable=False)
    user_id = Column(String(36), ForeignKey("user.id"), nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)

    post = relationship("Post", back_populates="likes")
    user = relationship("User")


class Comment(Base):  # type: ignore[misc]
    __tablename__ = "comment"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    post_id = Column(String(36), ForeignKey("post.id"), nullable=False)
    user_id = Column(String(36), ForeignKey("user.id"), nullable=False)
    content = Column(Text, nullable=False)
    is_hidden_by_admin = Column(Boolean, default=False)
    is_deleted_by_author = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.utcnow)

    post = relationship("Post", back_populates="comments")
    user = relationship("User")
    replies = relationship("Reply", back_populates="comment", cascade="all, delete-orphan")

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": str(self.id),
            "post_id": str(self.post_id),
            "user_id": str(self.user_id),
            "content": str(self.content),
            "is_hidden_by_admin": bool(self.is_hidden_by_admin),
            "is_deleted_by_author": bool(self.is_deleted_by_author),
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }


class Reply(Base):  # type: ignore[misc]
    __tablename__ = "reply"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    comment_id = Column(String(36), ForeignKey("comment.id"), nullable=False)
    user_id = Column(String(36), ForeignKey("user.id"), nullable=False)
    content = Column(Text, nullable=False)
    is_hidden_by_admin = Column(Boolean, default=False)
    is_deleted_by_author = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.utcnow)

    comment = relationship("Comment", back_populates="replies")
    user = relationship("User")

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": str(self.id),
            "comment_id": str(self.comment_id),
            "user_id": str(self.user_id),
            "content": str(self.content),
            "is_hidden_by_admin": bool(self.is_hidden_by_admin),
            "is_deleted_by_author": bool(self.is_deleted_by_author),
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }


class LoginAttempt(Base):  # type: ignore[misc]
    __tablename__ = "login_attempt"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    username = Column(String(80), nullable=False, index=True)
    ip_address = Column(String(45), nullable=True)
    attempted_at = Column(DateTime, default=datetime.utcnow)
