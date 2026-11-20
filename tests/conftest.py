"""pytest 全局装置：浏览器生命周期、登录态复用、失败自动截图。

运行方式：
    pytest                       # 默认无头模式（settings.HEADLESS 默认有头，见下）
    pytest --headed              # 有头模式，观察浏览器操作
    pytest --slowmo=300          # 每步慢放 300ms，便于肉眼跟看
    pytest -m smoke              # 只跑冒烟
"""

from __future__ import annotations

import pytest
from playwright.sync_api import Browser, BrowserContext, Page, sync_playwright

from config import settings
from pages.login_page import LoginPage
from pages.worktime_page import WorktimePage


# ---------- 命令行选项 ----------
def pytest_addoption(parser):
    parser.addoption("--headed", action="store_true", default=False, help="有头模式运行浏览器")
    parser.addoption("--slowmo", action="store", default="0", help="每步操作慢放毫秒数")


def pytest_configure(config):
    if config.getoption("--headed"):
        settings.HEADLESS = False
    slow = int(config.getoption("--slowmo") or 0)
    if slow:
        settings.SLOW_MO = slow


# ---------- 浏览器 ----------
@pytest.fixture(scope="session")
def pw():
    with sync_playwright() as p:
        yield p


@pytest.fixture(scope="session")
def browser(pw) -> Browser:
    browser = pw.chromium.launch(headless=settings.HEADLESS, slow_mo=settings.SLOW_MO)
    yield browser
    browser.close()


@pytest.fixture(scope="session")
def context(browser: Browser) -> BrowserContext:
    state = str(settings.LOGIN_STATE) if settings.LOGIN_STATE.exists() else None
    ctx = browser.new_context(
        viewport=settings.VIEWPORT,
        storage_state=state,
        ignore_https_errors=True,
        locale="zh-CN",
    )
    ctx.set_default_timeout(settings.TIMEOUT)
    ctx.set_default_navigation_timeout(settings.NAV_TIMEOUT)
    yield ctx
    ctx.close()


@pytest.fixture()
def page(context: BrowserContext, request) -> Page:
    """每条用例独立页面；失败自动截图留证。"""
    p = context.new_page()
    yield p

    rep = getattr(request.node, "rep_call", None)
    if rep is not None and rep.failed:
        settings.REPORT_DIR.mkdir(parents=True, exist_ok=True)
        shot = settings.REPORT_DIR / f"fail_{request.node.name}.png"
        try:
            p.screenshot(path=str(shot), full_page=True)
            print(f"\n[失败截图] {shot}")
        except Exception:
            pass
    p.close()


# ---------- 登录态 ----------
@pytest.fixture(scope="session")
def session_valid(context: BrowserContext) -> bool:
    """整个会话只探活一次，避免每条用例都跳一次工作台。"""
    p = context.new_page()
    try:
        ok = LoginPage(p).is_logged_in()
        print(f"\n[探活] 登录态={ok} url={p.url} state={settings.LOGIN_STATE.exists()}")
        return ok
    finally:
        p.close()


@pytest.fixture()
def logged_in_page(page: Page, session_valid: bool) -> Page:
    if not session_valid:
        pytest.skip("登录态无效：先运行 python utils/save_login_state.py 保存会话")
    return page


# ---------- 页面对象 ----------
@pytest.fixture()
def wt(logged_in_page: Page) -> WorktimePage:
    return WorktimePage(logged_in_page)


@pytest.fixture()
def cleanup_zone(wt: WorktimePage):
    """登记本次用例造的 AUTO- 备注，结束后按备注删行 —— 只删自己造的，绝不动真实数据。"""
    remarks: list[str] = []
    yield remarks
    for remark in remarks:
        try:
            wt.open()
            if wt.row_by_remark(remark).count() > 0:
                wt.delete_row_by_remark(remark)
                print(f"\n[清理] 已删除自动化数据：{remark}")
            else:
                print(f"\n[清理] 列表中无该行（保存可能失败）：{remark}")
        except Exception as exc:  # noqa: BLE001
            print(f"\n[清理失败] {remark}：{exc}，请人工在界面删除（备注含 AUTO-）")


# ---------- 失败留证 ----------
@pytest.hookimpl(hookwrapper=True, tryfirst=True)
def pytest_runtest_makereport(item, call):
    outcome = yield
    rep = outcome.get_result()
    setattr(item, f"rep_{rep.when}", rep)
