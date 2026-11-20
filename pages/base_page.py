"""页面基类：封装所有页面共用的等待、提示读取、表格加载判断。

原则：
1. 不用 sleep，全部用状态等待（visible / hidden / 文案出现）。
2. el-message 提示约 3 秒消失，必须在动作后立即读取。
3. 定位优先 label / 文本 / testid，禁止 nth-child 与绝对 XPath。
"""

from __future__ import annotations

from playwright.sync_api import Locator, Page, expect

from config import settings


class BasePage:
    """所有页面对象的基类。"""

    def __init__(self, page: Page):
        self.page = page
        self.page.set_default_timeout(settings.TIMEOUT)
        self.page.set_default_navigation_timeout(settings.NAV_TIMEOUT)

    # ---------- 导航 ----------
    def goto(self, path: str = ""):
        """打开相对路径（path 以 / 开头，如 '/#/login'）。"""
        url = settings.BASE_URL + path if path.startswith("/") else path
        self.page.goto(url, wait_until="domcontentloaded")
        return self

    # ---------- 等待 ----------
    def wait_loading_gone(self, timeout: int = 20000):
        """ElementUI 表格/页面加载完成 = loading 遮罩消失。"""
        masks = self.page.locator(".el-loading-mask")
        end = timeout
        while end > 0 and masks.count() > 0:
            try:
                masks.first.wait_for(state="hidden", timeout=2000)
            except Exception:
                pass
            end -= 2000
            if masks.count() == 0:
                break
        return self

    def wait_url_contains(self, fragment: str, timeout: int | None = None):
        expect(self.page).to_have_url(lambda url: fragment in url, timeout=timeout or settings.TIMEOUT)
        return self

    # ---------- 提示 ----------
    def toast_text(self, timeout: int = 6000) -> str:
        """读取 el-message 提示文案；多条时取最新一条。"""
        msg = self.page.locator(".el-message:visible")
        msg.last.wait_for(state="visible", timeout=timeout)
        return msg.last.inner_text().strip()

    def toast_should_contain(self, text: str, timeout: int = 6000):
        """断言提示包含指定文案（内部自带轮询，比取值再比较稳）。"""
        expect(self.page.locator(".el-message:visible").last).to_contain_text(text, timeout=timeout)

    def wait_toast_gone(self, timeout: int = 8000):
        """等提示自然消失，避免影响下一步操作。"""
        try:
            self.page.locator(".el-message:visible").last.wait_for(state="hidden", timeout=timeout)
        except Exception:
            pass
        return self

    # ---------- 弹窗 ----------
    @property
    def dialog(self) -> Locator:
        return self.page.locator(".el-dialog:visible").last

    def dialog_visible(self) -> bool:
        return self.page.locator(".el-dialog:visible").count() > 0

    def dialog_title(self) -> str:
        return self.dialog.locator(".el-dialog__header").inner_text().strip()

    # ---------- 表格 ----------
    def table_headers(self) -> list[str]:
        """返回表头文本列表（去掉首列序号与末尾操作列由调用方处理）。"""
        cells = self.page.locator(".el-table__header-wrapper th .cell")
        return [cells.nth(i).inner_text().strip() for i in range(cells.count())]

    def table_row_count(self) -> int:
        rows = self.page.locator(".el-table__body-wrapper tbody tr")
        return rows.count()

    def table_cell(self, row_index: int, col_index: int) -> Locator:
        """按行列下标取单元格（仅用于断言展示值，不用于定位可点击元素）。"""
        return self.page.locator(".el-table__body-wrapper tbody tr").nth(row_index).locator("td").nth(col_index)

    def row_by_text(self, text: str) -> Locator:
        """按行内文本定位整行（数据行断言用，比下标稳）。"""
        return self.page.locator(".el-table__body-wrapper tbody tr").filter(has_text=text).first

    # ---------- 菜单 ----------
    def click_menu(self, *names: str):
        """按菜单文本逐级点击，例：click_menu('工时管理', '外包工时管理')。"""
        for name in names:
            item = self.page.get_by_text(name, exact=True).first
            item.wait_for(state="visible")
            item.click()
            self.wait_loading_gone()
        return self

    # ---------- 截图 ----------
    def screenshot(self, filename: str):
        settings.REPORT_DIR.mkdir(parents=True, exist_ok=True)
        path = settings.REPORT_DIR / filename
        self.page.screenshot(path=str(path), full_page=True)
        return path
