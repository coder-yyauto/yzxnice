#!/usr/bin/env python3
"""
检查帖子数据
"""

import sys

sys.path.insert(0, ".")

from core.models import Post, User
from database import get_db, init_db


def check_posts() -> None:
    init_db()

    with get_db() as db:
        post_count = db.query(Post).count()
        print(f"总帖子数: {post_count}")

        posts = db.query(Post).order_by(Post.created_at.desc()).limit(10).all()
        for post in posts:
            author = db.query(User).filter(User.id == post.user_id).first()
            print(f"\n帖子ID: {post.id}")
            print(f"  作者: {author.username if author else '未知'} ({author.user_type if author else ''})")
            print(f"  内容: {post.content[:50]}...")
            print(f"  图片: {post.images}")
            print(f"  组织ID: {post.org_id}")
            print(f"  可见组织ID: {post.visible_org_id}")
            print(f"  时间: {post.created_at}")

            # 检查图片路径
            if post.images:
                import os

                from config import config

                img_list = post.images.split(",")
                print(f"  图片文件列表: {img_list}")
                for img in img_list:
                    if img:
                        path = os.path.join(config.UPLOAD_DIR, img)
                        exists = os.path.exists(path)
                        print(f"    {img}: {'存在' if exists else '不存在'}")
                        if exists:
                            print(f"      大小: {os.path.getsize(path)} bytes")

        # 检查admin用户的帖子
        admin = db.query(User).filter(User.username == "admin").first()
        if admin:
            admin_posts = db.query(Post).filter(Post.user_id == admin.id).all()
            print(f"\nadmin用户的帖子数: {len(admin_posts)}")
            for p in admin_posts:
                print(f"  帖子ID: {p.id}, 图片: {p.images}")


if __name__ == "__main__":
    check_posts()
