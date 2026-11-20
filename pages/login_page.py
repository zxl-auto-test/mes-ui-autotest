"""登录页对象。

说明：验证码为 4 位图形码，自动化不识别，采用「人工登录一次 + 会话复用」方案：
    python utils/save_login_state.py
登录成功后保存 state/login.json，后续用例直接用该会话。
"""

from __future__ import annotations

from pathlib import Path

from playwright.sync_api import Page, expect

from config import settings
from pages.base_page import BasePage


class LoginPage(BasePage):
    # 元素定位（2026-11-16 阶段 3 实测）
    USERNAME_INPUT = "input[placeholder*='账号']"
    PASSWORD_INPUT = "input[placeholder*='密码']"
    CAPTCHA_INPUT = "input[placeholder*='验证码']"
    SUBMIT_BUTTON = "button:has-text('登')"  # 实际 DOM 文本是「登 录」（带空格）
    WORKBENCH_MARK = "text=待办中心"

    def open(self) -> "LoginPage":
        self.goto(settings.LOGIN_PATH)
        return self

    def captcha_image(self):
        """验证码图片元素（供人工识别或截图）。"""
        return self.page.locator("form img, .login-form img, img[src*='code'], img[src*='captcha']").first

    def save_captcha_shot(self, path: Path) -> Path:
        self.captcha_image().screenshot(path=str(path))
        return path

    def login(self, username: str, password: str, captcha: str) -> None:
        self.page.locator(self.USERNAME_INPUT).first.fill(username)
        self.page.locator(self.PASSWORD_INPUT).first.fill(password)
        self.page.locator(self.CAPTCHA_INPUT).first.fill(captcha)
        self.page.locator(self.SUBMIT_BUTTON).first.click()

    def wait_logged_in(self, timeout: int = 15000) -> None:
        """以「离开登录页 + 工作台标记出现」作为登录成功判据。"""
        expect(self.page).not_to_have_url(lambda url: "login" in url, timeout=timeout)
        self.wait_loading_gone()

    def is_logged_in(self) -> bool:
        """探活：当前上下文是否仍是有效登录态。"""
        self.page.goto(settings.BASE_URL + settings.WORKBENCH_PATH, wait_until="domcontentloaded")
        self.page.wait_for_timeout(1500)
        return "login" not in self.page.url
