from database import get_db
from core.models import Org, User, UserRole


def get_org_ancestors(db, org_id: str) -> list[str]:
    ids = []
    current = db.query(Org).filter(Org.id == org_id).first()
    while current:
        ids.append(current.id)
        if current.parent_id:
            current = db.query(Org).filter(Org.id == current.parent_id).first()
        else:
            break
    return ids


def get_org_descendants(db, org_id: str) -> list[str]:
    result = [org_id]
    children = db.query(Org).filter(Org.parent_id == org_id).all()
    for child in children:
        result.extend(get_org_descendants(db, child.id))
    return result


def get_school_root(db, org_id: str) -> Org | None:
    current = db.query(Org).filter(Org.id == org_id).first()
    while current and current.org_type != "school":
        if current.parent_id:
            current = db.query(Org).filter(Org.id == current.parent_id).first()
        else:
            return None
    return current


def get_user_school(db, user: User) -> Org | None:
    if user.user_type == "teacher":
        org = db.query(Org).filter(Org.id == user.default_org_id).first()
        if org:
            return get_school_root(db, org.id)
        return None
    elif user.user_type == "student":
        class_org = db.query(Org).filter(Org.id == user.default_org_id).first()
        if class_org and class_org.parent_id:
            grade_org = db.query(Org).filter(Org.id == class_org.parent_id).first()
            if grade_org and grade_org.parent_id:
                return db.query(Org).filter(Org.id == grade_org.parent_id).first()
    return None


def get_visible_org_ids(db, user: User) -> list[str]:
    if user.user_type == "admin":
        return [o.id for o in db.query(Org).filter(Org.is_active == True).all()]

    school = get_user_school(db, user)
    if not school:
        return []

    if user.user_type == "teacher":
        return get_org_descendants(db, school.id)
    elif user.user_type == "student":
        class_org = db.query(Org).filter(Org.id == user.default_org_id).first()
        if class_org:
            return [class_org.id]
    return []


def get_manageable_org_ids(db, user: User) -> list[str]:
    if user.user_type == "admin":
        all_orgs = db.query(Org).filter(Org.is_active == True).all()
        return [o.id for o in all_orgs]

    if user.user_type == "student":
        return []

    roles = db.query(UserRole).filter(UserRole.user_id == user.id).all()
    if not roles:
        return []

    manageable = set()
    for role in roles:
        descendants = get_org_descendants(db, role.scope_org_id)
        manageable.update(descendants)
    return list(manageable)


def get_schools(db) -> list[Org]:
    return db.query(Org).filter(Org.org_type == "school", Org.is_active == True).all()


def get_grades(db, school_id: str) -> list[Org]:
    return (
        db.query(Org)
        .filter(Org.org_type == "grade", Org.parent_id == school_id, Org.is_active == True)
        .order_by(Org.grade_number)
        .all()
    )


def get_classes(db, grade_id: str) -> list[Org]:
    return (
        db.query(Org)
        .filter(Org.org_type == "class", Org.parent_id == grade_id, Org.is_active == True)
        .order_by(Org.class_number)
        .all()
    )
