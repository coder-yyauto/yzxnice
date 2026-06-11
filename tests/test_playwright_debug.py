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


def test_login(page):
    """测试登录过程，添加调试信息"""
    print("正在访问应用...")
    page.goto("http://localhost:8080")
    page.wait_for_load_state("networkidle")
    time.sleep(2)

    print("点击登录按钮...")
    login_button = page.get_by_text("登录")
    login_button.click()
    page.wait_for_load_state("networkidle")
    time.sleep(2)

    print("截图：登录页面")
    page.screenshot(path="/tmp/test_login_page_debug.png")

    print("填写表单...")
    username_input = page.get_by_placeholder("用户名")
    username_input.fill("helaoshi")
    time.sleep(1)

    password_input = page.get_by_placeholder("密码")
    password_input.fill("123456")
    time.sleep(1)

    captcha_input = page.get_by_placeholder("请输入验证码")
    captcha_input.fill("1234")
    time.sleep(1)

    print("截图：填写后的表单")
    page.screenshot(path="/tmp/test_form_filled_debug.png")

    print("点击登录...")
    login_submit = page.get_by_text("登录")
    login_submit.click()

    print("等待登录处理...")
    time.sleep(5)  # 增加等待时间

    print("截图：点击登录后")
    page.screenshot(path="/tmp/test_after_click_debug.png")

    current_url = page.url
    print(f"当前URL: {current_url}")

    if "/login" in current_url:
        print("❌ 仍在登录页面")
        # 检查错误信息
        page_content = page.content()
        if "错误" in page_content or "失败" in page_content:
            print("页面包含错误信息")

    elif "/home" in current_url:
        print("✓ 成功进入朋友圈")
        page.wait_for_load_state("networkidle")
        time.sleep(2)
        return True
    else:
        print(f"⚠️ 重定向到其他页面: {current_url}")

    return False


def test_app():
    app_process = start_app()

    try:
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True, slow_mo=500)  # 慢速模式以便观察
            page = browser.new_page()

            # 设置超时
            page.set_default_timeout(10000)

            if test_login(page):
                print("\n登录成功，测试朋友圈功能...")

                print("截图：朋友圈页面")
                page.screenshot(path="/tmp/test_pyq_debug.png", full_page=True)

                # 检查关键功能
                page_content = page.content()

                print(f"页面是否包含'朋友圈': {'朋友圈' in page_content}")
                print(f"页面是否包含'筛选班级': {'筛选班级' in page_content}")
                print(f"页面是否包含'发布': {'发布' in page_content}")
                print(f"页面是否包含'评论': {'评论' in page_content}")
                print(f"页面是否包含'点赞': {'点赞' in page_content}")

                # 检查按钮数量
                filter_elements = page.get_by_text("筛选班级")
                print(f"筛选班级元素数量: {filter_elements.count()}")

                publish_elements = page.get_by_text("发布")
                print(f"发布元素数量: {publish_elements.count()}")

                comment_elements = page.get_by_text("评论")
                print(f"评论元素数量: {comment_elements.count()}")

                like_elements = page.get_by_text("点赞")
                print(f"点赞元素数量: {like_elements.count()}")

                # 如果有评论，点击测试
                if comment_elements.count() > 0:
                    print("\n点击评论按钮...")
                    comment_elements.first.click()
                    time.sleep(3)

                    print("截图：评论展开后")
                    page.screenshot(path="/tmp/test_comment_expanded_debug.png")

                    comment_content = page.content()
                    print(f"评论区域是否包含'回复': {'回复' in comment_content}")
                    print(f"评论区域是否包含'删除': {'删除' in comment_content}")
                    print(f"评论区域是否包含'屏蔽': {'屏蔽' in comment_content}")

            else:
                print("登录失败，跳过功能测试")

            browser.close()

    finally:
        if app_process:
            print("\n关闭应用...")
            app_process.send_signal(signal.SIGTERM)
            app_process.wait()

    print("\n测试完成！所有截图已保存到 /tmp/test_*_debug.png")


if __name__ == "__main__":
    test_app()
