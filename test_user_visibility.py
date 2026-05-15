#!/usr/bin/env python3
"""
测试用户管理页面是否显示学生和教师
"""

import asyncio
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from playwright.async_api import async_playwright

BASE_URL = "http://localhost:8080"
ADMIN_USERNAME = "admin"
ADMIN_PASSWORD = os.getenv("DEFAULT_PASSWORD")
TEST_CAPTCHA = "1234"


async def test_user_visibility():
    """测试用户管理页面是否显示学生和教师"""
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context()
        page = await context.new_page()
        
        try:
            print("1. 登录...")
            await page.goto(f"{BASE_URL}/login")
            await page.wait_for_load_state("networkidle")
            
            await page.locator('input[placeholder="请输入用户名"]').fill(ADMIN_USERNAME)
            await page.locator('input[type="password"]').fill(ADMIN_PASSWORD)
            await page.locator('input[placeholder="请输入验证码"]').fill(TEST_CAPTCHA)
            await page.locator('button:has-text("登录")').click()
            
            await page.wait_for_load_state("networkidle")
            await page.wait_for_timeout(2000)
            
            print("2. 导航到用户管理页面...")
            await page.goto(f"{BASE_URL}/admin/users")
            await page.wait_for_load_state("networkidle")
            await page.wait_for_timeout(2000)
            
            # 截图
            screenshot_dir = Path("/tmp/yzxnice_test_screenshots")
            screenshot_dir.mkdir(exist_ok=True)
            await page.screenshot(path=screenshot_dir / "05_user_management.png")
            print(f"  截图已保存: {screenshot_dir}/05_user_management.png")
            
            # 检查学校扩展面板
            school_expansions = page.locator('.q-expansion-item:has-text("向阳小学")')
            school_count = await school_expansions.count()
            print(f"  找到 {school_count} 个学校扩展面板")
            
            if school_count > 0:
                print("  ✅ 学校扩展面板显示正常")
                
                # 展开第一个学校
                await school_expansions.first().click()
                await page.wait_for_timeout(1000)
                
                # 检查教师部分
                teacher_expansion = page.locator('.q-expansion-item:has-text("教师")')
                teacher_count = await teacher_expansion.count()
                print(f"  找到 {teacher_count} 个教师扩展面板")
                
                if teacher_count > 0:
                    print("  ✅ 教师扩展面板显示正常")
                    await teacher_expansion.first().click()
                    await page.wait_for_timeout(1000)
                    
                    # 检查教师表格
                    teacher_table = page.locator('table')
                    if await teacher_table.count() > 0:
                        print("  ✅ 教师表格显示正常")
                        
                        # 检查教师行
                        teacher_rows = page.locator('table tbody tr')
                        row_count = await teacher_rows.count()
                        print(f"  找到 {row_count} 行教师数据")
                        
                        if row_count >= 3:  # 至少3个教师（Txy001001, Txy001admin, helaoshi）
                            print("  ✅ 教师数据显示正常")
                        else:
                            print(f"  ⚠️  教师行数不足: {row_count}")
                    else:
                        print("  ⚠️  未找到教师表格")
                else:
                    print("  ⚠️  未找到教师扩展面板")
                
                # 检查班级扩展面板
                class_expansion = page.locator('.q-expansion-item:has-text("1年级1班")')
                class_count = await class_expansion.count()
                print(f"  找到 {class_count} 个班级扩展面板")
                
                if class_count > 0:
                    print("  ✅ 班级扩展面板显示正常")
                    await class_expansion.first().click()
                    await page.wait_for_timeout(1000)
                    
                    # 检查学生表格
                    student_table = page.locator('table')
                    if await student_table.count() > 0:
                        print("  ✅ 学生表格显示正常")
                        
                        # 检查学生行
                        student_rows = page.locator('table tbody tr')
                        row_count = await student_rows.count()
                        print(f"  找到 {row_count} 行学生数据")
                        
                        if row_count > 0:
                            print("  ✅ 学生数据显示正常")
                        else:
                            print("  ⚠️  未找到学生数据")
                    else:
                        print("  ⚠️  未找到学生表格")
                else:
                    print("  ⚠️  未找到班级扩展面板")
                
                # 测试批量生成学生账号功能
                print("3. 测试批量生成学生账号功能...")
                
                # 选择学校（应该已默认选择）
                school_select = page.locator('select[label="选择学校"]')
                if await school_select.count() > 0:
                    print("  ✅ 学校选择框存在")
                    
                    # 选择操作
                    action_select = page.locator('select[label="操作"]')
                    if await action_select.count() > 0:
                        print("  ✅ 操作选择框存在")
                        
                        # 选择"批量生成学生账号"
                        await action_select.select_option("gen_students")
                        
                        # 点击执行按钮
                        execute_btn = page.locator('button:has-text("执行")')
                        if await execute_btn.count() > 0:
                            print("  ✅ 执行按钮存在")
                            # 注意：不实际点击，因为已经有很多学生了
                        else:
                            print("  ⚠️  未找到执行按钮")
                    else:
                        print("  ⚠️  未找到操作选择框")
                else:
                    print("  ⚠️  未找到学校选择框")
                
            else:
                print("  ❌ 未找到学校扩展面板")
                
                # 查看页面内容
                page_content = await page.content()
                if "向阳小学" in page_content:
                    print("  ⚠️  页面包含'向阳小学'但未找到扩展面板")
                else:
                    print("  ⚠️  页面不包含'向阳小学'")
            
        except Exception as e:
            print(f"  ❌ 测试过程中出现异常: {e}")
            import traceback
            traceback.print_exc()
            
        finally:
            await browser.close()


async def main():
    print("=" * 60)
    print("测试用户管理页面可见性")
    print("=" * 60)
    
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
        sys.exit(1)
    
    print()
    
    await test_user_visibility()
    
    print()
    print("=" * 60)
    print("测试完成!")
    print("=" * 60)


if __name__ == "__main__":
    asyncio.run(main())