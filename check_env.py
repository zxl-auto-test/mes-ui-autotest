"""阶段 1 环境验证脚本：用 Playwright 打开测试环境登录页并截图。

用法：
    ./.venv/Scripts/python.exe check_env.py
"""
from pathlib import Path

from playwright.sync_api import sync_playwright

from config.settings import LOGIN_URL

ROOT = Path(__file__).resolve().parent
URL = LOGIN_URL


def main() -> None:
    shot = ROOT / "reports" / "smoke_login.png"
    shot.parent.mkdir(parents=True, exist_ok=True)

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(viewport={"width": 1366, "height": 768})
        page = context.new_page()
        resp = page.goto(URL, wait_until="domcontentloaded", timeout=30_000)
        page.wait_for_timeout(2_500)

        print("HTTP 状态:", resp.status if resp else "无响应")
        print("页面标题:", page.title())
        print("当前地址:", page.url)
        print("可视文本片段:", page.inner_text("body")[:120].replace("\n", " | "))
        page.screenshot(path=str(shot))
        print("截图:", shot)
        browser.close()


if __name__ == "__main__":
    main()
