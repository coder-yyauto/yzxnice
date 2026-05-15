from database import get_db
from core.models import Comment, Org, Post, User, UserRole
from core.org_utils import get_manageable_org_ids, get_org_ancestors


def can_manage_post(user: User, post: Post) -> bool:
    if user.user_type == "admin":
        return True
    if user.user_type == "student":
        return False
    if post.user_id == user.id:
        return True
    with get_db() as db:
        manageable = get_manageable_org_ids(db, user)
        return post.org_id in manageable


def can_manage_comment(user: User, comment: Comment, post: Post) -> bool:
    if user.user_type == "admin":
        return True
    if user.user_type == "student":
        return comment.user_id == user.id
    if comment.user_id == user.id:
        return True
    with get_db() as db:
        manageable = get_manageable_org_ids(db, user)
        return post.org_id in manageable


def can_delete_post(user: User, post: Post) -> bool:
    if user.user_type == "admin":
        return True
    if user.user_type == "student":
        return post.user_id == user.id
    if post.user_id == user.id:
        return True
    with get_db() as db:
        manageable = get_manageable_org_ids(db, user)
        return post.org_id in manageable


def is_system_admin(user: User) -> bool:
    return user.user_type == "admin"


def get_user_roles(db, user: User) -> list[dict]:
    roles = db.query(UserRole).filter(UserRole.user_id == user.id).all()
    return [r.to_dict() for r in roles]


def has_any_admin_role(db, user: User) -> bool:
    if user.user_type == "admin":
        return True
    if user.user_type == "student":
        return False
    count = db.query(UserRole).filter(UserRole.user_id == user.id).count()
    return count > 0


def has_admin_page_access(db, user: User) -> bool:
    if user.user_type == "admin":
        return True
    school_admin = db.query(UserRole).filter(
        UserRole.user_id == user.id,
        UserRole.role == "school_admin"
    ).first()
    return school_admin is not None


def get_admin_school_ids(db, user: User) -> set[str]:
    if user.user_type == "admin":
        return {s.id for s in db.query(Org).filter(Org.org_type == "school", Org.is_active == True).all()}
    roles = db.query(UserRole).filter(
        UserRole.user_id == user.id,
        UserRole.role == "school_admin"
    ).all()
    return {r.scope_org_id for r in roles}


def can_assign_role(db, assigner: User, role_name: str, scope_org_id: str) -> bool:
    if assigner.user_type == "admin":
        return True
    if role_name == "school_admin":
        return False
    admin_schools = get_admin_school_ids(db, assigner)
    if not admin_schools:
        return False
    scope = db.query(Org).filter(Org.id == scope_org_id).first()
    if not scope:
        return False
    if scope.org_type == "school":
        return scope.id in admin_schools
    ancestors = get_org_ancestors(db, scope_org_id)
    return bool(admin_schools & set(ancestors))
