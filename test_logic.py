"""
测试应用逻辑，不涉及UI
"""
import os
from database import get_db
from core.models import User, Post, Comment, Reply, Org
from core.auth import AuthManager
from core.org_utils import get_visible_org_ids
from pyq.card import load_posts

print("=" * 50)
print("测试应用核心功能")
print("=" * 50)

# 1. 测试用户加载
print("\n1. 测试用户加载...")
with get_db() as db:
    user = db.query(User).filter(User.username == 'helaoshi').first()
    if user:
        print(f"✓ 用户加载成功: {user.display_name} ({user.user_type})")
    else:
        print("✗ 用户加载失败")
        exit(1)

# 2. 测试认证
print("\n2. 测试认证...")
try:
    user_info = AuthManager.login(username='helaoshi', password=os.getenv("DEFAULT_PASSWORD"))
    print(f"✓ 登录成功: {user_info['display_name']}")
    print(f"  用户类型: {user_info['user_type']}")
    print(f"  学校ID: {user_info['school_id']}")
    print(f"  是否管理员: {user_info['is_admin']}")
    print(f"  是否显示筛选班级: {user_info['user_type'] in ('teacher', 'admin') or user_info['is_admin']}")
except Exception as e:
    print(f"✗ 登录失败: {e}")
    exit(1)

# 3. 测试可见组织
print("\n3. 测试可见组织...")
with get_db() as db:
    user = db.query(User).filter(User.username == 'helaoshi').first()
    visible = get_visible_org_ids(db, user)
    print(f"✓ 可见组织数量: {len(visible)}")
    print("  前10个组织:")
    for i, org_id in enumerate(visible[:10], 1):
        org = db.query(Org).filter(Org.id == org_id).first()
        if org:
            print(f"    {i}. {org.name} ({org.org_type})")

# 4. 测试帖子加载
print("\n4. 测试帖子加载...")
try:
    with get_db() as db:
        user = db.query(User).filter(User.username == 'helaoshi').first()
        user_info_for_load = {
            'user_id': user.id,
            'username': user.username,
            'display_name': user.display_name,
            'user_type': user.user_type,
            'is_admin': True,
            'school_id': user.default_org_id,
        }
        posts = load_posts(user_info_for_load, filter_org_id=None)
        print(f"✓ 加载帖子成功: {len(posts)} 条")
        for i, post in enumerate(posts, 1):
            print(f"  {i}. {post['content'][:40]}... (作者: {post['author_name']}, 评论数: {post['comment_count']})")
except Exception as e:
    print(f"✗ 加载帖子失败: {e}")
    import traceback
    traceback.print_exc()

# 5. 测试评论数据
print("\n5. 测试评论数据...")
with get_db() as db:
    comments = db.query(Comment).all()
    print(f"✓ 数据库中评论总数: {len(comments)}")
    if comments:
        for comment in comments[:3]:
            print(f"  - {comment.content[:30]}... (作者: {comment.user_id})")

# 6. 测试回复数据
print("\n6. 测试回复数据...")
with get_db() as db:
    replies = db.query(Reply).all()
    print(f"✓ 数据库中回复总数: {len(replies)}")
    if replies:
        for reply in replies[:3]:
            print(f"  - {reply.content[:30]}... (作者: {reply.user_id})")

# 7. 测试帖子过滤功能
print("\n7. 测试帖子过滤功能...")
try:
    # 获取第一个班级ID进行测试
    with get_db() as db:
        user = db.query(User).filter(User.username == 'helaoshi').first()
        user_info_for_filter = {
            'user_id': user.id,
            'username': user.username,
            'display_name': user.display_name,
            'user_type': user.user_type,
            'is_admin': True,
            'school_id': user.default_org_id,
        }
        first_class = db.query(Org).filter(Org.org_type == 'class').first()
        if first_class:
            print(f"  测试班级: {first_class.name} (ID: {first_class.id})")
            posts = load_posts(user_info_for_filter, filter_org_id=first_class.id)
            print(f"  ✓ 班级帖子数量: {len(posts)}")
        else:
            print("  ✗ 未找到班级")
except Exception as e:
    print(f"  ✗ 过滤失败: {e}")

# 8. 测试权限检查
print("\n8. 测试权限检查...")
from core.permissions import can_manage_post, can_manage_comment

with get_db() as db:
    user = db.query(User).filter(User.username == 'helaoshi').first()
    test_post = db.query(Post).first()
    if test_post:
        can_manage = can_manage_post(user, test_post)
        print(f"  ✓ 用户是否可以管理帖子: {can_manage}")

    test_comment = db.query(Comment).first()
    if test_comment and test_post:
        can_manage = can_manage_comment(user, test_comment, test_post)
        print(f"  ✓ 用户是否可以管理评论: {can_manage}")

print("\n" + "=" * 50)
print("测试完成")
print("=" * 50)