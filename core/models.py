import uuid
from datetime import datetime

from sqlalchemy import Boolean, Column, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import relationship

from database import Base


class Org(Base):
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

    def to_dict(self):
        return {
            "id": self.id,
            "name": self.name,
            "org_type": self.org_type,
            "parent_id": self.parent_id,
            "school_code": self.school_code,
            "grade_number": self.grade_number,
            "class_number": self.class_number,
        }


class User(Base):
    __tablename__ = "user"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    username = Column(String(80), unique=True, nullable=False)
    password_hash = Column(String(255), nullable=False)
    display_name = Column(String(100), nullable=True)
    user_type = Column(String(20), nullable=False, default="student")
    default_org_id = Column(String(36), ForeignKey("org.id"), nullable=True)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    default_org = relationship("Org", foreign_keys=[default_org_id])
    roles = relationship("UserRole", back_populates="user", cascade="all, delete-orphan")
    posts = relationship("Post", back_populates="author")

    def set_password(self, password: str):
        import argon2

        hasher = argon2.PasswordHasher(time_cost=2, memory_cost=65536, parallelism=2, hash_len=32)
        self.password_hash = hasher.hash(password)

    def check_password(self, password: str) -> bool:
        import argon2

        hasher = argon2.PasswordHasher()
        try:
            hasher.verify(self.password_hash, password)
            return True
        except (argon2.exceptions.VerifyMismatchError, argon2.exceptions.VerificationError):
            return False
        except Exception:
            return False

    def to_dict(self):
        return {
            "id": self.id,
            "username": self.username,
            "display_name": self.display_name,
            "user_type": self.user_type,
            "default_org_id": self.default_org_id,
            "is_active": self.is_active,
        }


class UserRole(Base):
    __tablename__ = "user_role"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = Column(String(36), ForeignKey("user.id"), nullable=False)
    role = Column(String(30), nullable=False)
    scope_org_id = Column(String(36), ForeignKey("org.id"), nullable=False)

    user = relationship("User", back_populates="roles")
    scope_org = relationship("Org")

    def to_dict(self):
        return {
            "id": self.id,
            "user_id": self.user_id,
            "role": self.role,
            "scope_org_id": self.scope_org_id,
        }


class Post(Base):
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

    def to_dict(self):
        return {
            "id": self.id,
            "user_id": self.user_id,
            "content": self.content,
            "images": self.images.split(",") if self.images else [],
            "org_id": self.org_id,
            "visible_org_id": self.visible_org_id,
            "is_hidden": self.is_hidden,
            "is_hidden_by_admin": self.is_hidden_by_admin,
            "visibility": self.visibility or "public",
            "show_location": self.show_location if self.show_location is not None else True,
            "visible_to_orgs": self.visible_to_orgs.split(",") if self.visible_to_orgs else [],
            "excluded_orgs": self.excluded_orgs.split(",") if self.excluded_orgs else [],
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }


class Like(Base):
    __tablename__ = "like"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    post_id = Column(String(36), ForeignKey("post.id"), nullable=False)
    user_id = Column(String(36), ForeignKey("user.id"), nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)

    post = relationship("Post", back_populates="likes")
    user = relationship("User")

    __table_args__ = ()


class Comment(Base):
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

    def to_dict(self):
        return {
            "id": self.id,
            "post_id": self.post_id,
            "user_id": self.user_id,
            "content": self.content,
            "is_hidden_by_admin": self.is_hidden_by_admin,
            "is_deleted_by_author": self.is_deleted_by_author,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }


class Reply(Base):
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

    def to_dict(self):
        return {
            "id": self.id,
            "comment_id": self.comment_id,
            "user_id": self.user_id,
            "content": self.content,
            "is_hidden_by_admin": self.is_hidden_by_admin,
            "is_deleted_by_author": self.is_deleted_by_author,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }
