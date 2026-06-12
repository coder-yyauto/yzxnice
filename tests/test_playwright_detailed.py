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


def login_and_get_to_pyq(page):
    """登录并进入朋友圈页面"""
    print("正在访问应用...")
    page.goto("http://localhost:8080")
    page.wait_for_load_state("networkidle")
    time.sleep(2)

    print("点击登录...")
    login_button = page.get_by_text("登录")
    login_button.click()
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

    print("检查是否进入朋友圈...")
    if "/home" in page.url:
        print("✓ 成功进入朋友圈")
        page.wait_for_load_state("networkidle")
        time.sleep(2)
        return True
    else:
        print(f"✗ 未进入朋友圈，当前URL: {page.url}")
        return False


def _inspect_comment_area(page) -> None:
    """Inspect the expanded comment area (steps 5-10)."""
    print("点击第一个评论按钮...")
    comment_buttons = page.get_by_text("评论")
    if comment_buttons.count() == 0:
        return
    print(f"找到 {comment_buttons.count()} 个'评论'按钮")
    print("✓ 评论功能存在")
    comment_buttons.first.click()
    time.sleep(2)

    print("截图：评论区域")
    page.screenshot(path="/tmp/test_comment_area.png")

    comment_area_content = page.content()

    print("\n6. 检查评论区域功能...")

    if "写评论" in comment_area_content:
        print("✓ 找到'写评论'输入框")
    else:
        print("✗ 没有找到'写评论'输入框")

    if "还不错" in comment_area_content:
        print("✓ 找到现有评论内容")
    else:
        print("✗ 没有找到现有评论内容")

    print("\n7. 检查回复功能...")
    reply_elements = page.get_by_text("回复")
    if reply_elements.count() > 0:
        print(f"✓ 找到 {reply_elements.count()} 个回复按钮")
    else:
        print("✗ 没有找到回复按钮")

    print("\n8. 检查删除功能...")
    delete_elements = page.get_by_text("删除")
    if delete_elements.count() > 0:
        print(f"✓ 找到 {delete_elements.count()} 个删除按钮")
    else:
        print("✗ 没有找到删除按钮")

    print("\n9. 检查管理员屏蔽功能...")
    hide_texts = ["屏蔽", "visibility_off", "visibility"]
    hide_found = False
    for text in hide_texts:
        elements = page.get_by_text(text)
        if elements.count() > 0:
            print(f"✓ 找到 '{text}' 相关元素: {elements.count()} 个")
            hide_found = True
    if not hide_found:
        print("✗ 没有找到屏蔽相关功能")

    print("\n10. 检查被屏蔽提示...")
    if "被屏蔽" in comment_area_content:
        print("✓ 找到被屏蔽提示")
    else:
        print("✗ 没有找到被屏蔽提示")

    print("\n点击返回...")
    page.screenshot(path="/tmp/test_before_back.png")
    page.go_back()
    time.sleep(2)

    page.screenshot(path="/tmp/test_full_page_after_test.png", full_page=True)


def test_features_detailed(page):
    """详细测试朋友圈功能"""
    print("\n=== 详细功能测试 ===")

    # 1. 检查筛选班级
    print("\n1. 检查筛选班级功能...")
    filter_select = page.get_by_text("筛选班级")
    if filter_select.count() > 0:
        print("✓ 找到筛选班级组件")
        page_content = page.content()
        if "全部" in page_content:
            print("✓ 包含'全部'选项")
    else:
        print("✗ 没有找到筛选班级组件")

    # 2. 检查发布按钮
    print("\n2. 检查发布功能...")
    publish_btn = page.get_by_text("发布")
    if publish_btn.is_visible():
        print("✓ 找到发布按钮")
    else:
        print("✗ 没有找到发布按钮")

    # 3. 检查帖子内容
    print("\n3. 检查帖子...")
    page_content = page.content()

    if "暂无内容" in page_content:
        print("朋友圈暂无内容")
        return
    print("✓ 有内容显示")

    # 4. 检查点赞功能
    print("\n4. 检查点赞功能...")
    like_buttons = page.get_by_text("点赞")
    star_buttons = page.get_by_text("star")
    print(f"找到 {like_buttons.count()} 个'点赞'按钮")
    print(f"找到 {star_buttons.count()} 个'star'相关元素")

    # 5-10. 检查评论功能（抽到辅助函数）
    print("\n5. 检查评论功能...")
    _inspect_comment_area(page)


def test_app():
    app_process = start_app()

    try:
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            page = browser.new_page()

            # 登录并进入朋友圈
            if not login_and_get_to_pyq(page):
                print("登录失败，退出测试")
                browser.close()
                return

            # 截图朋友圈页面
            print("\n截图朋友圈完整页面...")
            page.screenshot(path="/tmp/test_pyq_full.png", full_page=True)

            # 详细测试功能
            test_features_detailed(page)

            browser.close()

    finally:
        if app_process:
            print("\n关闭应用...")
            app_process.send_signal(signal.SIGTERM)
            app_process.wait()

    print("\n测试完成！所有截图已保存到 /tmp/test_*.png")


if __name__ == "__main__":
    test_app()
