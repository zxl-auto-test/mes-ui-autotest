"""阶段 2 骨架自检：不需要登录，验证框架能启动浏览器、打开页面、断言界面。

注意：其余用例的 context 带登录态（storage_state），直接打开登录页会被重定向到工作台，
所以这里用独立的无状态 context。
"""

from __future__ import annotations

import re

import pytest
from playwright.sync_api import expect

from config import settings


@pytest.fixture(scope="session")
def anon_page(pw):
    """无登录态的页面，专门看登录页。"""
    browser = pw.chromium.launch(headless=True)
    ctx = browser.new_context(viewport=settings.VIEWPORT, locale="zh-CN")
    ctx.set_default_timeout(settings.TIMEOUT)
    page = ctx.new_page()
    yield page
    browser.close()


@pytest.mark.smoke
def test_login_page_opens(anon_page):
    """登录页能打开，标题、系统名、账号输入框、验证码图片都存在。"""
    anon_page.goto(settings.LOGIN_URL, wait_until="domcontentloaded")

    expect(anon_page).to_have_title(re.compile("登录"))
    expect(anon_page.get_by_text("数据采集系统")).to_be_visible()
    expect(anon_page.locator("input[placeholder*='账号']").first).to_be_visible()
    expect(anon_page.locator("input[placeholder*='密码']").first).to_be_visible()
    expect(anon_page.locator("input[placeholder*='验证码']").first).to_be_visible()
    expect(anon_page.get_by_role("button", name=re.compile(r"登\s*录"))).to_be_visible()


@pytest.mark.smoke
def test_viewport_is_workshop_1366(page):
    """视口固定 1366×768，对齐车间工控机。"""
    assert page.viewport_size == {"width": 1366, "height": 768}


@pytest.mark.smoke
def test_config_loaded():
    """配置项齐全，且造数前缀符合约定。"""
    assert settings.BASE_URL.startswith("http")
    assert settings.WORK_ORDER
    assert settings.DATA_PREFIX == "AUTO-"
