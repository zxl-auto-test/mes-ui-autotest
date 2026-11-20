"""阶段 4：登录一次，把会话存成 state/login.json，供所有用例复用。

背景：登录有 4 位图形验证码，脚本本身不识别图形。
做法：脚本把验证码截图落到 state/captcha.png，然后轮询等待 state/captcha_answer.txt
      被写入 4 位字符，读到后自动填入并登录，成功后保存会话。

用法（有头模式，能看到浏览器在动）：
    .venv/Scripts/python.exe utils/save_login_state.py                  # 默认账号 admin
    .venv/Scripts/python.exe utils/save_login_state.py --password xxx   # 指定密码
    .venv/Scripts/python.exe utils/save_login_state.py --headed 0       # 无头

退出码：0 成功；1 失败（密码错/验证码多次错/超时）
"""

from __future__ import annotations

import argparse
import sys
import time
from pathlib import Path

# 允许直接 python utils/save_login_state.py 运行
ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from playwright.sync_api import Page, TimeoutError as PWTimeout, sync_playwright

from config import settings

CAPTCHA_SHOT = settings.STATE_DIR / "captcha.png"
CAPTCHA_ANSWER = settings.STATE_DIR / "captcha_answer.txt"
ERROR_SHOT = settings.REPORT_DIR / "login_error.png"

USERNAME_INPUT = "input[placeholder*='账号']"
PASSWORD_INPUT = "input[placeholder*='密码']"
CAPTCHA_INPUT = "input[placeholder*='验证码']"
SUBMIT_BUTTON = "button:has-text('登录')"


def log(msg: str) -> None:
    print(msg, flush=True)


def find_captcha_img(page: Page):
    """验证码图片：取离「验证码输入框」最近的可见 img，避免误抓 logo。"""
    box = page.locator(CAPTCHA_INPUT).first.bounding_box()
    best, best_d = None, 1e18
    imgs = page.locator("img")
    for i in range(imgs.count()):
        img = imgs.nth(i)
        try:
            if not img.is_visible():
                continue
            ib = img.bounding_box()
        except Exception:
            continue
        if not ib or ib["width"] < 40 or ib["height"] < 15:
            continue
        if box:
            d = abs(ib["x"] - box["x"] - box["width"]) + abs(ib["y"] - box["y"])
        else:
            d = 0
        if d < best_d:
            best, best_d = img, d
    return best


def ask_captcha(page: Page, timeout: int = 240) -> str:
    """截图验证码并等待外部识别结果写入 answer 文件。"""
    settings.STATE_DIR.mkdir(parents=True, exist_ok=True)
    CAPTCHA_ANSWER.unlink(missing_ok=True)

    img = find_captcha_img(page)
    if img is None:
        raise RuntimeError("没找到验证码图片")
    img.screenshot(path=str(CAPTCHA_SHOT))
    log(f"[CAPTCHA] 已截图 -> {CAPTCHA_SHOT}，等待识别结果写入 {CAPTCHA_ANSWER}")

    end = time.time() + timeout
    while time.time() < end:
        if CAPTCHA_ANSWER.exists():
            code = CAPTCHA_ANSWER.read_text(encoding="utf-8").strip()
            CAPTCHA_ANSWER.unlink(missing_ok=True)
            if code:
                log(f"[CAPTCHA] 读到验证码：{code}")
                return code
        time.sleep(0.5)
    raise TimeoutError("等待验证码识别结果超时")


def current_toast(page: Page) -> str:
    try:
        msg = page.locator(".el-message:visible").last
        msg.wait_for(state="visible", timeout=4000)
        return msg.inner_text().strip()
    except Exception:
        return ""


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--user", default=settings.USERNAME)
    ap.add_argument("--password", default=settings.PASSWORD)
    ap.add_argument("--headed", default="1", help="1=有头（默认），0=无头")
    ap.add_argument("--retry", type=int, default=3, help="验证码最多重试次数")
    args = ap.parse_args()

    settings.STATE_DIR.mkdir(parents=True, exist_ok=True)
    settings.REPORT_DIR.mkdir(parents=True, exist_ok=True)

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=args.headed == "0", slow_mo=150)
        ctx = browser.new_context(
            viewport=settings.VIEWPORT,
            ignore_https_errors=True,
            locale="zh-CN",
        )
        ctx.set_default_timeout(settings.TIMEOUT)
        page = ctx.new_page()

        for attempt in range(1, args.retry + 1):
            log(f"--- 第 {attempt} 次登录尝试 ---")
            page.goto(settings.LOGIN_URL, wait_until="domcontentloaded")
            page.locator(USERNAME_INPUT).first.wait_for(state="visible")

            page.locator(USERNAME_INPUT).first.fill(args.user)
            page.locator(PASSWORD_INPUT).first.fill(args.password)

            code = ask_captcha(page)
            page.locator(CAPTCHA_INPUT).first.fill(code)
            page.locator(SUBMIT_BUTTON).first.click()

            try:
                page.wait_for_url(lambda url: "login" not in url, timeout=12000)
            except PWTimeout:
                toast = current_toast(page)
                log(f"[FAIL] 未跳转，提示：{toast or '（无提示）'}")
                if toast and ("密码" in toast or "账号" in toast):
                    log("[FAIL] 账号或密码不正确，请用 --password 指定正确密码")
                    page.screenshot(path=str(ERROR_SHOT), full_page=True)
                    browser.close()
                    return 1
                continue  # 验证码错，重来

            # 登录成功：等首页稳定后保存会话
            page.wait_for_timeout(2500)
            state_file = settings.LOGIN_STATE
            state_file.parent.mkdir(parents=True, exist_ok=True)
            ctx.storage_state(path=str(state_file))
            log(f"[OK] 登录成功，会话已保存 -> {state_file}")
            log(f"[OK] 当前地址：{page.url}")
            page.screenshot(path=str(settings.REPORT_DIR / "login_ok.png"), full_page=True)
            browser.close()
            return 0

        page.screenshot(path=str(ERROR_SHOT), full_page=True)
        log(f"[FAIL] {args.retry} 次均未登录成功，截图 -> {ERROR_SHOT}")
        browser.close()
        return 1


if __name__ == "__main__":
    sys.exit(main())
