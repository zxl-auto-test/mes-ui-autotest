"""阶段 3：弹窗剩余交互探测（工作令联动、工种选项、日期范围、保存校验）。"""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from playwright.sync_api import sync_playwright

from config import settings

DUMP = settings.REPORT_DIR / "probe_rest.json"


def dropdown_items(page):
    return page.eval_on_selector_all(
        ".el-select-dropdown:visible .el-select-dropdown__item", "els => els.map(e => e.innerText.trim())"
    )


def main() -> int:
    state = str(settings.LOGIN_STATE)
    out: dict = {}
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        ctx = browser.new_context(viewport=settings.VIEWPORT, storage_state=state, locale="zh-CN")
        ctx.set_default_timeout(15000)
        page = ctx.new_page()
        page.goto(settings.BASE_URL + "#/trace/outsourceWorkHour/outsourceWorkHour", wait_until="domcontentloaded")
        page.wait_for_timeout(3000)
        page.get_by_role("button", name=re.compile(r"新\s*增")).first.click()
        page.wait_for_timeout(2000)

        dlg = page.locator(".avue-dialog:visible").first

        # 1) 工作令号
        dlg.locator("input[placeholder*='工作令号']").first.click()
        page.wait_for_timeout(1200)
        out["wo_items"] = dropdown_items(page)
        page.locator(".el-select-dropdown__item:visible").filter(has_text=settings.WORK_ORDER).first.click()
        page.wait_for_timeout(1500)
        # 项目名称：选中工作令后 placeholder 会被值覆盖，改用 label 定位
        labels = page.eval_on_selector_all(
            ".avue-dialog:visible .el-form-item__label", "els => els.map(e => e.innerText.trim())"
        )
        out["form_labels"] = labels
        print(f"[1] 表单项 label：{labels}")
        proj = dlg.locator(".el-form-item").filter(has_text="项目名称").locator("input").first
        out["project_value"] = proj.input_value()
        out["project_disabled"] = proj.is_disabled()
        print(f"[1] 工作令选项 {len(out['wo_items'])} 个：{out['wo_items']}")
        print(f"[1] 选 {settings.WORK_ORDER} 后项目名称 = {out['project_value']!r} (disabled={out['project_disabled']})")

        # 2) 工种
        dlg.locator("input[placeholder*='工种']").first.click()
        page.wait_for_timeout(1200)
        out["craft_items"] = dropdown_items(page)
        print(f"[2] 工种选项 {len(out['craft_items'])} 个：{out['craft_items']}")
        if out["craft_items"]:
            page.locator(".el-select-dropdown__item:visible").filter(has_text="机加").first.click()
            page.wait_for_timeout(800)

        # 3) 日期范围
        start = dlg.locator("input[placeholder='开始日期']").first
        start.click()
        page.wait_for_timeout(1200)
        panel = page.locator(".el-picker-panel.el-date-range-picker:visible").first
        out["panel_visible"] = panel.count()
        out["panel_text"] = panel.inner_text()[:300] if panel.count() else ""
        left_days = page.locator(".el-date-range-picker__content.is-left td.available")
        out["left_days"] = [left_days.nth(i).inner_text().strip() for i in range(min(left_days.count(), 40))]
        print(f"[3] 面板出现={out['panel_visible']}，可点日期数={left_days.count()}，前 10 个={out['left_days'][:10]}")
        if left_days.count():
            left_days.nth(0).click()
            page.wait_for_timeout(800)
            out["start_value"] = start.input_value()
            right_days = page.locator(".el-date-range-picker__content.is-right td.available")
            print(f"[3] 点开始日后 value={out['start_value']!r}，右侧可点={right_days.count()}")
            if right_days.count():
                right_days.nth(1).click()
                page.wait_for_timeout(800)
        end = dlg.locator("input[placeholder='结束日期']").first
        out["start_final"] = start.input_value()
        out["end_final"] = end.input_value()
        print(f"[3] 日期最终值：{out['start_final']!r} ~ {out['end_final']!r}")

        page.screenshot(path=str(settings.REPORT_DIR / "probe_rest.png"))

        # 4) 不填必填项直接保存，看校验提示
        page.locator(".avue-dialog:visible").get_by_role("button", name=re.compile(r"取\s*消")).first.click()
        page.wait_for_timeout(1200)
        out["dialog_closed"] = page.locator(".avue-dialog:visible").count() == 0
        print(f"[4] 取消后弹窗关闭：{out['dialog_closed']}")

        # 5) 空表单直接保存
        page.get_by_role("button", name=re.compile(r"新\s*增")).first.click()
        page.wait_for_timeout(1500)
        page.locator(".avue-dialog:visible").get_by_role("button", name=re.compile(r"保\s*存")).first.click()
        page.wait_for_timeout(1500)
        out["toast_empty_save"] = page.eval_on_selector_all(
            ".el-message", "els => els.map(e => e.innerText.trim())"
        )
        out["field_errors"] = page.eval_on_selector_all(
            ".el-form-item__error", "els => els.map(e => e.innerText.trim())"
        )
        print(f"[5] 空表单保存 → 提示={out['toast_empty_save']}，字段错误={out['field_errors']}")
        page.screenshot(path=str(settings.REPORT_DIR / "probe_validate.png"))

        DUMP.write_text(json.dumps(out, ensure_ascii=False, indent=2), encoding="utf-8")
        print(f"[OK] {DUMP}")
        browser.close()
    return 0


if __name__ == "__main__":
    sys.exit(main())
