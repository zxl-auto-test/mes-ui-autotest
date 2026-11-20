"""外包工时管理页面对象（阶段 3 实测结果固化版）。

实测依据：reports/probe_*.png / probe_*.json（2026-11-16）
路由：/#/trace/outsourceWorkHour/outsourceWorkHour

踩过的坑（不要回退）：
1. ElementUI 两字按钮 DOM 文本带空格 —— "搜 索""新 增""保 存""取 消""清 空"，
   必须用正则（r"新\\s*增"），不能用 has-text('新增')。
2. 弹窗是 avue 的 `.el-dialog__wrapper.avue-dialog`，页面上另有 4 个隐藏的 `.el-dialog`；
   作用域必须用 `.avue-dialog:visible`，否则抓到空壳。
3. 表单控件不能按 placeholder 找：placeholder 带空格（"请选择 工作令号"），且
   工作令号选中后 placeholder 会消失、项目名称的 placeholder 被值覆盖。
   统一按 `.el-form-item` 的 label 文本定位。
4. 工作令号下拉实测可搜索（输入 2026111 → 只剩 1 项），input 初始 readonly 属性
   在聚焦后失效，用 type() 输入即可，不要用 fill（fill 对 readonly 抛错）。
"""

from __future__ import annotations

import re
from pathlib import Path

from playwright.sync_api import Locator, Page, expect

from config import settings
from pages.base_page import BasePage

DIALOG = ".avue-dialog:visible"
BTN_SEARCH = re.compile(r"搜\s*索")
BTN_CLEAR = re.compile(r"清\s*空")
BTN_ADD = re.compile(r"新\s*增")
BTN_SAVE = re.compile(r"(保\s*存|修\s*改)")  # 新增弹窗是「保 存」，编辑弹窗是「修 改」
BTN_CANCEL = re.compile(r"取\s*消")


class WorktimePage(BasePage):
    PATH = "/#/trace/outsourceWorkHour/outsourceWorkHour"

    # 列表业务列（表头实测顺序，首列为复选框、末列为操作）
    COLUMNS = [
        "工作令号", "项目名称", "工种", "日期", "人数",
        "总工时(h)", "时薪(元/h)", "总金额", "备注",
        "创建人", "创建时间", "更新人", "更新时间",
    ]
    # 实测 td 索引：0=复选框, 1=隐藏, 2~14=业务列, 15=操作, 16=隐藏
    COL_INDEX = {name: i + 2 for i, name in enumerate(COLUMNS)}

    def __init__(self, page: Page):
        super().__init__(page)

    # ---------- 打开 ----------
    def open(self) -> "WorktimePage":
        """直接跳路由（最快最稳），用于绝大多数用例。"""
        self.goto(self.PATH)
        self.wait_table_loaded()
        return self

    def open_by_menu(self) -> "WorktimePage":
        """走菜单：工时管理 → 外包工时。折叠态侧边栏需先点一级、再点弹层子项。"""
        title = self.page.locator(".el-submenu__title:has-text('工时管理')").first
        title.click()
        self.page.wait_for_timeout(1000)
        item = self.page.locator(".el-menu--popup:visible .el-menu-item:has-text('外包工时')").first
        item.click()
        self.wait_table_loaded()
        return self

    def wait_table_loaded(self) -> "WorktimePage":
        self.wait_loading_gone()
        self.page.locator(".el-table").first.wait_for(state="visible")
        self.page.wait_for_timeout(600)
        return self

    # ---------- 弹窗 ----------
    @property
    def dialog(self) -> Locator:
        return self.page.locator(DIALOG).last

    def dialog_opened(self) -> bool:
        return self.page.locator(DIALOG).count() > 0

    def dialog_title(self) -> str:
        return self.dialog.locator(".el-dialog__header").inner_text().strip().replace(" ", "")

    def field(self, label: str) -> Locator:
        """按表单项 label 取控件；label 非表单项名时（如"开始日期"）退回 placeholder 精确匹配。"""
        fi = self.dialog.locator(".el-form-item").filter(has_text=label)
        if fi.count():
            return fi.first.locator("input, textarea").first
        return self.dialog.locator(f"input[placeholder='{label}']").first

    def field_value(self, label: str) -> str:
        return self.field(label).input_value()

    # ---------- 列表 ----------
    def headers(self) -> list[str]:
        """业务列表头（跳过 # 与操作列）。"""
        cells = self.page.locator(".el-table__header-wrapper th .cell")
        all_txt = [cells.nth(i).inner_text().strip() for i in range(cells.count())]
        return [t for t in all_txt if t]

    def rows(self) -> Locator:
        return self.page.locator(".el-table__body-wrapper tbody tr")

    def row_count(self) -> int:
        self.wait_loading_gone()
        return self.rows().count()

    def fixed_rows(self) -> Locator:
        """右侧固定列的行（操作列按钮只渲染在 .el-table__fixed-right 里，主表体是空 div）。"""
        return self.page.locator(".el-table__fixed-right tbody tr")

    def row_action(self, index: int, action: str) -> Locator:
        """按主表体行号，取固定列里对应的操作按钮（详情/编辑/删除）。"""
        return self.fixed_rows().nth(index).get_by_role("button", name=action).first

    def index_by_remark(self, remark: str) -> int:
        """按备注定位主表体行号；找不到返回 -1。"""
        for i in range(self.row_count()):
            if remark in self.rows().nth(i).inner_text():
                return i
        return -1

    def click_row_action(self, remark: str, action: str) -> "WorktimePage":
        idx = self.index_by_remark(remark)
        assert idx >= 0, f"列表中未找到备注含 {remark!r} 的行"
        self.row_action(idx, action).click()
        self.page.wait_for_timeout(800)
        return self

    def total_text(self) -> str:
        el = self.page.locator(".el-pagination__total")
        return el.first.inner_text().strip() if el.count() else ""

    def row_by_remark(self, remark: str) -> Locator:
        return self.rows().filter(has_text=remark).first

    def cell(self, row: Locator, col: str) -> str:
        """按列名取某行单元格文本（断言展示值用）。"""
        return row.locator("td").nth(self.COL_INDEX[col]).inner_text().strip()

    def row_values(self, row: Locator) -> dict[str, str]:
        return {name: self.cell(row, name) for name in self.COLUMNS}

    # ---------- 查询 ----------
    def click_search(self) -> "WorktimePage":
        self.page.get_by_role("button", name=BTN_SEARCH).first.click()
        self.wait_table_loaded()
        return self

    def click_clear(self) -> "WorktimePage":
        self.page.get_by_role("button", name=BTN_CLEAR).first.click()
        self.wait_table_loaded()
        return self

    def _search_field(self, label: str) -> Locator:
        return self.page.locator(".avue-crud__search .el-form-item").filter(has_text=label).locator("input").first

    def select_search_option(self, label: str, keyword: str, option_text: str) -> "WorktimePage":
        """查询区可搜索下拉：点击 → 输入关键字 → 点选项。"""
        box = self._search_field(label)
        box.click()
        self.page.wait_for_timeout(400)
        box.type(keyword, delay=80)
        opt = self.page.locator(".el-select-dropdown:visible .el-select-dropdown__item:visible").filter(
            has_text=option_text
        ).first
        opt.wait_for(state="visible", timeout=8000)
        opt.click()
        self.page.wait_for_timeout(400)
        return self

    def search_by_work_order(self, work_order: str) -> "WorktimePage":
        self.select_search_option("工作令号", work_order, work_order)
        return self.click_search()

    # ---------- 新增 / 编辑表单 ----------
    def click_add(self) -> "WorktimePage":
        self.page.get_by_role("button", name=BTN_ADD).first.click()
        self.dialog.wait_for(state="visible")
        self.page.wait_for_timeout(600)
        return self

    def select_form_option(self, label: str, keyword: str, option_text: str) -> "WorktimePage":
        """表单内的可搜索下拉（工作令号）；支持改选（先全选再输入覆盖）。"""
        box = self.field(label)
        box.click()
        self.page.wait_for_timeout(400)
        box.press("Control+a")
        box.type(keyword, delay=80)
        opt = self.page.locator(".el-select-dropdown:visible .el-select-dropdown__item:visible").filter(
            has_text=option_text
        ).first
        opt.wait_for(state="visible", timeout=8000)
        opt.click()
        self.page.wait_for_timeout(800)
        return self

    def select_craft(self, craft: str = "机加") -> "WorktimePage":
        """工种下拉不可搜索，直接点选项。"""
        self.field("工种").click()
        opt = self.page.locator(".el-select-dropdown:visible .el-select-dropdown__item:visible").filter(
            has_text=craft
        ).first
        opt.wait_for(state="visible", timeout=8000)
        opt.click()
        self.page.wait_for_timeout(400)
        return self

    def fill_fields(self, **values: str) -> "WorktimePage":
        """按 label 填值，例：fill_fields(人数='2', 总工时='16')。"""
        for label, val in values.items():
            box = self.field(label)
            box.click()
            box.fill(str(val))
            box.press("Tab")
            self.page.wait_for_timeout(300)
        return self

    def pick_date_range(self, start_day: int, end_day: int) -> "WorktimePage":
        """日期范围：点开始日期 → 面板左月点开始日 → 左月点结束日（同月场景）。

        注意：不能用 has_text 正则匹配日期数字（td 文本带空白，^1$ 匹配不上），
        必须遍历取 inner_text().strip() 精确比较。
        """
        self.field("开始日期").click()
        panel = self.page.locator(".el-date-range-picker:visible").first
        panel.wait_for(state="visible")
        left = panel.locator(".el-date-range-picker__content.is-left")

        def pick(day: int) -> None:
            cells = left.locator("td.available:not(.prev-month):not(.next-month)")
            for i in range(cells.count()):
                if cells.nth(i).inner_text().strip() == str(day):
                    cells.nth(i).click()
                    self.page.wait_for_timeout(500)
                    return
            raise AssertionError(f"日期面板左月未找到 {day} 号")

        pick(start_day)
        pick(end_day)
        self.page.wait_for_timeout(600)
        return self

    def amount_value(self) -> str:
        return self.field_value("总金额")

    def field_errors(self) -> list[str]:
        return [
            self.page.locator(".el-form-item__error").nth(i).inner_text().strip()
            for i in range(self.page.locator(".el-form-item__error").count())
        ]

    def click_save(self) -> "WorktimePage":
        """新增 → 保 存；编辑 → 修 改。文案不同，用统一正则。"""
        self.dialog.get_by_role("button", name=BTN_SAVE).first.click()
        self.page.wait_for_timeout(800)
        return self

    def click_cancel(self) -> "WorktimePage":
        self.dialog.get_by_role("button", name=BTN_CANCEL).first.click()
        self.page.wait_for_timeout(600)
        return self

    # ---------- 组合动作 ----------
    def add_record(
        self,
        work_order: str,
        craft: str = "机加",
        people: str = "2",
        hours: str = "16",
        rate: str = "50",
        remark: str | None = None,
        days: tuple[int, int] | None = None,
    ) -> "WorktimePage":
        """一条正向新增；备注默认带 AUTO- 前缀，便于识别与清理。"""
        self.click_add()
        self.select_form_option("工作令号", work_order, work_order)
        self.select_craft(craft)
        if days:
            self.pick_date_range(*days)
        self.fill_fields(人数=people, 总工时=hours, 时薪=rate)
        self.field("备注").fill(remark or f"{settings.DATA_PREFIX}{work_order}")
        self.click_save()
        return self

    def delete_row_by_remark(self, remark: str) -> "WorktimePage":
        """只按 AUTO- 备注精确定位后删除，绝不碰真实数据。"""
        self.click_row_action(remark, "删除")
        confirm = self.page.locator(".el-message-box:visible")
        confirm.wait_for(state="visible")
        confirm.get_by_role("button", name="确定").first.click()
        self.wait_table_loaded()
        return self

    def screenshot(self, filename: str):
        settings.REPORT_DIR.mkdir(parents=True, exist_ok=True)
        path = settings.REPORT_DIR / filename
        self.page.screenshot(path=str(path), full_page=True)
        return path
