import os
import signal
import subprocess
import time

import requests
from playwright.sync_api import sync_playwright


def start_app():
    """启动应用"""
    try:
        requests.get("http://localhost:8080", timeout=2)
        print("应用已在运行")
        return None
    except requests.ConnectionError:
        print("应用未运行，正在启动...")
        process = subprocess.Popen(["python", "main.py"], env={**os.environ, "NICEGUI_RELOAD": "false"})
        time.sleep(5)
        return process


def login_and_navigate(page):
    """登录并导航到朋友圈"""
    print("正在访问应用...")
    page.goto("http://localhost:8080")
    page.wait_for_load_state("networkidle")
    time.sleep(2)

    print("点击登录...")
    page.get_by_text("登录").click()
    page.wait_for_load_state("networkidle")
    time.sleep(2)

    print("填写登录信息...")
    page.get_by_placeholder("用户名").fill("helaoshi")
    time.sleep(1)
    page.get_by_placeholder("密码").fill("123456")
    time.sleep(1)
    page.get_by_placeholder("请输入验证码").fill("1234")
    time.sleep(1)

    print("提交登录...")
    page.get_by_text("登录").click()
    time.sleep(3)

    if "/home" in page.url:
        print("✓ 登录成功")
        page.wait_for_load_state("networkidle")
        time.sleep(2)
        return True
    return False


def _inspect_post_comment_buttons(page) -> None:
    """Click through comment buttons until a comment area with content is found."""
    comment_buttons = page.get_by_text("评论")
    if comment_buttons.count() < 1:
        return
    print(f"找到 {comment_buttons.count()} 个评论按钮")

    for i in range(min(5, comment_buttons.count())):
        print(f"\n尝试第 {i + 1} 个评论按钮...")
        comment_buttons.nth(i).click()
        time.sleep(3)

        print(f"截图：点击第 {i + 1} 个评论按钮后")
        page.screenshot(path=f"/tmp/test_comment_click_{i + 1}.png")

        comment_area_content = page.content()

        if "还不错" not in comment_area_content:
            print("没有找到评论内容，继续尝试下一个按钮...")
            page.go_back()
            time.sleep(2)
            continue

        print("✓ 展开了包含评论的区域")

        print("\n检查功能按钮:")

        reply_buttons = page.get_by_text("回复")
        if reply_buttons.count() > 0:
            print(f"  ✓ 回复按钮: {reply_buttons.count()} 个")
        else:
            print("  ✗ 回复按钮: 0 个")

        delete_buttons = page.get_by_text("删除")
        if delete_buttons.count() > 0:
            print(f"  ✓ 删除按钮: {delete_buttons.count()} 个")
        else:
            print("  ✗ 删除按钮: 0 个")

        hide_texts = ["屏蔽", "visibility_off", "visibility"]
        hide_found = False
        for text in hide_texts:
            elements = page.get_by_text(text)
            if elements.count() > 0:
                print(f"  ✓ 屏蔽功能 ('{text}'): {elements.count()} 个")
                hide_found = True
        if not hide_found:
            print("  ✗ 屏蔽功能: 未找到")

        if "被屏蔽" in comment_area_content:
            print("  ✓ 被屏蔽提示: 存在")
        else:
            print("  ✗ 被屏蔽提示: 不存在")

        print("\n返回上一页...")
        page.go_back()
        time.sleep(2)
        break


def test_specific_post_with_comment(page):
    """专门测试有评论的帖子"""
    print("\n=== 测试有评论的帖子功能 ===")

    print("寻找学生发的帖子...")
    page_content = page.content()

    if "学生发的帖子" not in page_content:
        print("✗ 未找到学生发的帖子")
        return
    print("✓ 找到学生发的帖子")

    print("检查该帖子的评论按钮...")
    _inspect_post_comment_buttons(page)


def test_main_features(page):
    """测试主要功能"""
    print("\n=== 测试主要功能 ===")

    # 1. 筛选班级
    print("\n1. 测试筛选班级功能...")
    filter_select = page.get_by_text("筛选班级")
    if filter_select.count() > 0:
        print("✓ 找到筛选班级")
        # 尝试展开
        try:
            filter_select.click()
            time.sleep(2)
            page.screenshot(path="/tmp/test_filter_expanded.png")

            # 检查是否有选项
            filter_content = page.content()
            if "全部" in filter_content:
                print("✓ 筛选班级可以展开")
            else:
                print("✗ 筛选班级无法展开或没有选项")
        except Exception:
            print("✗ 筛选班级点击失败")
    else:
        print("✗ 未找到筛选班级功能")

    # 2. 发布功能
    print("\n2. 测试发布功能...")
    publish_btn = page.get_by_text("发布")
    if publish_btn.is_visible():
        print("✓ 找到发布按钮")
        publish_btn.click()
        time.sleep(2)
        page.screenshot(path="/tmp/test_publish_page.png")

        # 检查发布页面元素
        publish_content = page.content()
        print(f"发布页面是否包含'发布到': {'发布到' in publish_content}")
        print(f"发布页面是否包含'分享你的想法': {'分享你的想法' in publish_content}")

        # 返回
        page.go_back()
        time.sleep(2)
    else:
        print("✗ 未找到发布按钮")

    # 3. 点赞功能
    print("\n3. 测试点赞功能...")
    like_buttons = page.get_by_text("点赞")
    star_buttons = page.get_by_text("star_border")
    print(f"找到 {like_buttons.count()} 个'点赞'按钮")
    print(f"找到 {star_buttons.count()} 个'star_border'按钮")


def test_app():
    app_process = start_app()

    try:
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            page = browser.new_page()

            if not login_and_navigate(page):
                print("登录失败，退出")
                browser.close()
                return

            print("截图：完整朋友圈页面")
            page.screenshot(path="/tmp/test_pyq_complete.png", full_page=True)

            # 测试主要功能
            test_main_features(page)

            # 测试有评论的帖子
            test_specific_post_with_comment(page)

            print("\n最终截图...")
            page.screenshot(path="/tmp/test_final_state.png", full_page=True)

            browser.close()

    finally:
        if app_process:
            print("\n关闭应用...")
            app_process.send_signal(signal.SIGTERM)
            app_process.wait()

    print("\n测试完成！所有截图已保存到 /tmp/test_*.png")


if __name__ == "__main__":
    test_app()
