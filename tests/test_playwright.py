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


def _login_via_ui(page, username: str, password: str) -> bool:
    """Fill the login form, submit, and return True if redirected to /home."""
    username_input = page.get_by_placeholder("用户名")
    if not username_input.is_visible():
        print("✗ 未找到用户名输入框")
        return False
    username_input.fill(username)
    time.sleep(1)

    page.get_by_placeholder("密码").fill(password)
    time.sleep(1)

    captcha_input = page.get_by_placeholder("请输入验证码")
    if captcha_input.is_visible():
        print("输入固定验证码: 1234")
        captcha_input.fill("1234")
        time.sleep(1)

    page.screenshot(path="/tmp/test_login_filled.png")

    page.get_by_text("登录").click()
    time.sleep(3)
    page.screenshot(path="/tmp/test_after_login.png")

    current_url = page.url
    print(f"当前URL: {current_url}")
    if "/home" not in current_url:
        print("✗ 登录失败，未能跳转到主页")
        page.screenshot(path="/tmp/test_login_failed.png")
        return False
    print("✓ 登录成功！")
    return True


def _check_pyq_features(page) -> None:
    """Run the post-login pyq feature checks."""
    print("检查朋友圈页面...")
    page_content = page.content()

    if "朋友圈" not in page_content:
        print("✗ 未进入朋友圈页面")
        return
    print("✓ 成功进入朋友圈页面")

    page.screenshot(path="/tmp/test_pyq.png", full_page=True)

    print("检查筛选班级功能...")
    filter_elements = page.get_by_text("筛选班级")
    if filter_elements.count() > 0:
        print("✓ 找到筛选班级功能")
    else:
        print("✗ 没有找到筛选班级功能")

    print("检查发布按钮...")
    publish_button = page.get_by_text("发布")
    if publish_button.is_visible():
        print("✓ 找到发布按钮")
        publish_button.click()
        page.wait_for_load_state("networkidle")
        time.sleep(2)

        page.screenshot(path="/tmp/test_publish.png")

        print("返回...")
        page.go_back()
        page.wait_for_load_state("networkidle")
        time.sleep(2)

    print("检查帖子...")
    if "暂无内容" in page_content:
        print("朋友圈暂无内容")
        return
    print("✓ 朋友圈有内容")

    print("检查评论、点赞等功能...")
    comment_buttons = page.get_by_text("评论")
    like_buttons = page.get_by_text("点赞")
    print(f"找到 {comment_buttons.count()} 个评论按钮")
    print(f"找到 {like_buttons.count()} 个点赞按钮")

    if comment_buttons.count() == 0:
        return
    print("✓ 评论功能存在")

    print("测试点击评论...")
    comment_buttons.first.click()
    time.sleep(2)
    page.screenshot(path="/tmp/test_comment_click.png")

    reply_buttons = page.get_by_text("回复")
    if reply_buttons.count() > 0:
        print("✓ 找到回复功能")
    else:
        print("✗ 没有找到回复功能")

    delete_buttons = page.get_by_text("删除")
    if delete_buttons.count() > 0:
        print("✓ 找到删除功能")
    else:
        print("✗ 没有找到删除功能")

    print("检查管理员屏蔽功能...")
    if "屏蔽" in page.content():
        print("✓ 找到管理员屏蔽功能")
    else:
        print("✗ 没有找到管理员屏蔽功能")


def test_app():
    app_process = start_app()

    try:
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            page = browser.new_page()

            print("正在访问应用...")
            page.goto("http://localhost:8080")
            page.wait_for_load_state("networkidle")
            time.sleep(2)

            print("截取首页...")
            page.screenshot(path="/tmp/test_home.png")

            print("检查登录页面...")
            login_button = page.get_by_text("登录")
            if not login_button.is_visible():
                print("✗ 未找到登录按钮")
                browser.close()
                return
            print("找到登录按钮，点击...")
            login_button.click()
            page.wait_for_load_state("networkidle")
            time.sleep(2)

            page.screenshot(path="/tmp/test_login_page.png")

            if _login_via_ui(page, "helaoshi", "123456"):
                _check_pyq_features(page)

            browser.close()

    finally:
        if app_process:
            print("关闭应用...")
            app_process.send_signal(signal.SIGTERM)
            app_process.wait()

    print("\n测试完成！截图已保存到 /tmp/test_*.png")


if __name__ == "__main__":
    test_app()
