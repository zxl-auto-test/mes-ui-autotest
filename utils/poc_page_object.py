"""阶段 3 POC：只读验证页面对象（不写任何数据）。"""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from playwright.sync_api import sync_playwright

from config import settings
from pages.worktime_page import WorktimePage


def main() -> int:
    with sync_playwright() as p:
        b = p.chromium.launch(headless=True)
        c = b.new_context(viewport=settings.VIEWPORT, storage_state=str(settings.LOGIN_STATE), locale="zh-CN")
        c.set_default_timeout(15000)
        pg = c.new_page()
        wt = WorktimePage(pg)

        wt.open()
        print("URL:", pg.url)
        print("表头:", wt.headers())
        print("行数:", wt.row_count(), "| 分页:", wt.total_text())

        wt.search_by_work_order(settings.WORK_ORDER)
        print("搜索后行数:", wt.row_count(), "| 分页:", wt.total_text())

        wt.click_add()
        print("弹窗标题:", wt.dialog_title())
        for lb in ["工作令号", "项目名称", "工种", "开始日期", "结束日期", "人数", "总工时", "时薪", "总金额", "备注"]:
            print(f"  {lb}: value={wt.field_value(lb)!r}")

        # 先验证空表单必填校验（不会落库）
        wt.click_save()
        print("空表单保存 → 校验错误:", wt.field_errors(), "| toast 数:", pg.locator(".el-message").count())

        wt.select_form_option("工作令号", settings.WORK_ORDER, settings.WORK_ORDER)
        print("选工作令后项目名称:", wt.field_value("项目名称"))
        wt.select_craft("机加")
        wt.fill_fields(人数="2", 总工时="16", 时薪="50")
        print("总金额自动算:", wt.amount_value())
        wt.fill_fields(总工时="20")
        print("总工时改 20 后总金额:", wt.amount_value())
        wt.click_cancel()
        print("弹窗已关:", not wt.dialog_opened(), "| 列表仍为:", wt.row_count(), wt.total_text())
        b.close()
    return 0


if __name__ == "__main__":
    sys.exit(main())
