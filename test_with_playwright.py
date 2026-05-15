#!/usr/bin/env python3
"""
使用Playwright测试多学校朋友圈教学系统
在TEST_MODE=true环境下运行，验证码被绕过
"""

import asyncio
import os
import sys
from pathlib import Path

from playwright.async_api import async_playwright

# 确保在项目根目录
sys.path.insert(0, str(Path(__file__).parent))

# 测试配置
BASE_URL = "http://localhost:8080"
ADMIN_USERNAME = "admin"
ADMIN_PASSWORD = os.getenv("DEFAULT_PASSWORD")
TEST_CAPTCHA = "1234"  # TEST_MODE下验证码固定为1234
SCREENSHOT_DIR = Path("/tmp/yzxnice_test_screenshots")
SCREENSHOT_DIR.mkdir(exist_ok=True)


async def test_login():
    """测试登录功能"""
    async with async_playwright() as p:
        # 启动浏览器（无头模式）
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context()
        page = await context.new_page()
        
        try:
            print("1. 导航到登录页面...")
            await page.goto(f"{BASE_URL}/login")
            await page.wait_for_load_state("networkidle")
            
            # 截图登录页面
            await page.screenshot(path=SCREENSHOT_DIR / "01_login_page.png")
            print(f"  截图已保存: {SCREENSHOT_DIR}/01_login_page.png")
            
            # 检查页面元素
            page_title = await page.title()
            print(f"  页面标题: {page_title}")
            
            # 查找登录表单元素
            username_input = page.locator('input[placeholder="请输入用户名"]')
            password_input = page.locator('input[type="password"]')
            captcha_input = page.locator('input[placeholder="请输入验证码"]')
            login_button = page.locator('button:has-text("登录")')
            
            print("2. 填写登录表单...")
            await username_input.fill(ADMIN_USERNAME)
            await password_input.fill(ADMIN_PASSWORD)
            await captcha_input.fill(TEST_CAPTCHA)
            
            print("3. 点击登录按钮...")
            await login_button.click()
            
            # 等待导航完成
            await page.wait_for_load_state("networkidle")
            await page.wait_for_timeout(2000)  # 额外等待2秒
            
            # 检查是否登录成功（重定向到/home）
            current_url = page.url
            print(f"  当前URL: {current_url}")
            
            if "/home" in current_url:
                print("  ✅ 登录成功，已重定向到首页")
                
                # 截图首页
                await page.screenshot(path=SCREENSHOT_DIR / "02_home_page.png")
                print(f"  截图已保存: {SCREENSHOT_DIR}/02_home_page.png")
                
                # 检查首页元素
                home_title = await page.title()
                print(f"  首页标题: {home_title}")
                
                # 检查是否有"朋友圈"标题
                pyq_title = page.locator('text="朋友圈"')
                if await pyq_title.count() > 0:
                    print("  ✅ 首页朋友圈标题显示正常")
                else:
                    print("  ⚠️  未找到朋友圈标题")
                
                # 检查是否有"发布新帖"按钮
                publish_button = page.locator('button:has-text("发布新帖")')
                if await publish_button.count() > 0:
                    print("  ✅ 发布新帖按钮显示正常")
                else:
                    print("  ⚠️  未找到发布新帖按钮")
                
                # 测试导航到发布页面
                print("4. 测试发布页面...")
                await publish_button.click()
                await page.wait_for_load_state("networkidle")
                await page.wait_for_timeout(1000)
                
                current_url = page.url
                print(f"  当前URL: {current_url}")
                
                if "/publish" in current_url:
                    print("  ✅ 成功导航到发布页面")
                    
                    # 截图发布页面
                    await page.screenshot(path=SCREENSHOT_DIR / "03_publish_page.png")
                    print(f"  截图已保存: {SCREENSHOT_DIR}/03_publish_page.png")
                    
                    # 检查发布页面元素
                    publish_title = page.locator('text="发布新帖"')
                    if await publish_title.count() > 0:
                        print("  ✅ 发布新帖标题显示正常")
                    
                    # 测试返回首页
                    print("5. 测试返回首页...")
                    await page.go_back()
                    await page.wait_for_load_state("networkidle")
                    await page.wait_for_timeout(1000)
                    
                    if "/home" in page.url:
                        print("  ✅ 成功返回首页")
                    else:
                        print("  ⚠️  返回首页失败")
                else:
                    print("  ❌ 导航到发布页面失败")
                    
            else:
                print("  ❌ 登录失败，未重定向到首页")
                
                # 检查错误信息
                error_text = page.locator('.text-red-500')
                if await error_text.count() > 0:
                    error_content = await error_text.text_content()
                    print(f"  错误信息: {error_content}")
                
                # 截图错误页面
                await page.screenshot(path=SCREENSHOT_DIR / "02_login_failed.png")
                print(f"  截图已保存: {SCREENSHOT_DIR}/02_login_failed.png")
                
        except Exception as e:
            print(f"  ❌ 测试过程中出现异常: {e}")
            import traceback
            traceback.print_exc()
            
            # 出错时截图
            await page.screenshot(path=SCREENSHOT_DIR / "error.png")
            print(f"  错误截图已保存: {SCREENSHOT_DIR}/error.png")
            
        finally:
            await browser.close()


async def test_admin_pages():
    """测试管理员页面"""
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context()
        page = await context.new_page()
        
        try:
            print("\n6. 测试管理后台页面...")
            
            # 先登录
            await page.goto(f"{BASE_URL}/login")
            await page.wait_for_load_state("networkidle")
            
            await page.locator('input[placeholder="请输入用户名"]').fill(ADMIN_USERNAME)
            await page.locator('input[type="password"]').fill(ADMIN_PASSWORD)
            await page.locator('input[placeholder="请输入验证码"]').fill(TEST_CAPTCHA)
            await page.locator('button:has-text("登录")').click()
            
            await page.wait_for_load_state("networkidle")
            await page.wait_for_timeout(2000)
            
            # 导航到管理后台
            admin_url = f"{BASE_URL}/admin"
            print(f"  导航到管理后台: {admin_url}")
            await page.goto(admin_url)
            await page.wait_for_load_state("networkidle")
            await page.wait_for_timeout(1000)
            
            current_url = page.url
            print(f"  管理后台URL: {current_url}")
            
            if "/admin" in current_url:
                print("  ✅ 成功访问管理后台")
                
                # 截图管理后台
                await page.screenshot(path=SCREENSHOT_DIR / "04_admin_page.png")
                print(f"  截图已保存: {SCREENSHOT_DIR}/04_admin_page.png")
                
                # 检查管理后台元素
                admin_title = await page.title()
                print(f"  管理后台标题: {admin_title}")
                
                # 检查是否有管理标签页
                org_tab = page.locator('text="组织管理"')
                user_tab = page.locator('text="用户管理"')
                role_tab = page.locator('text="权限管理"')
                
                tabs_found = []
                if await org_tab.count() > 0:
                    tabs_found.append("组织管理")
                if await user_tab.count() > 0:
                    tabs_found.append("用户管理")
                if await role_tab.count() > 0:
                    tabs_found.append("权限管理")
                
                if tabs_found:
                    print(f"  ✅ 找到管理标签页: {', '.join(tabs_found)}")
                else:
                    print("  ⚠️  未找到管理标签页")
                    
            else:
                print("  ❌ 访问管理后台失败")
                await page.screenshot(path=SCREENSHOT_DIR / "04_admin_failed.png")
                
        except Exception as e:
            print(f"  ❌ 管理后台测试异常: {e}")
            
        finally:
            await browser.close()


async def main():
    """主测试函数"""
    print("=" * 60)
    print("多学校朋友圈教学系统 - Playwright测试")
    print("=" * 60)
    print(f"测试环境: {BASE_URL}")
    print(f"测试账号: {ADMIN_USERNAME}")
    print(f"截图目录: {SCREENSHOT_DIR}")
    print()
    
    # 确保应用正在运行
    import requests
    try:
        response = requests.get(f"{BASE_URL}/login", timeout=5)
        if response.status_code == 200:
            print("✅ 应用正在运行")
        else:
            print(f"⚠️  应用返回状态码: {response.status_code}")
    except Exception as e:
        print(f"❌ 无法连接到应用: {e}")
        print("请确保应用已启动: TEST_MODE=true python main.py")
        sys.exit(1)
    
    print()
    
    # 运行测试
    await test_login()
    await test_admin_pages()
    
    print()
    print("=" * 60)
    print("测试完成!")
    print(f"所有截图保存在: {SCREENSHOT_DIR}")
    print("=" * 60)


if __name__ == "__main__":
    asyncio.run(main())