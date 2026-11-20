"""阶段 3：验证「工作令号下拉可搜索」是否成立（PRD 要求可搜索）。"""

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

OUT = settings.REPORT_DIR / "probe_searchable.json"


def items(page):
    return page.eval_on_selector_all(
        ".el-select-dropdown:visible .el-select-dropdown__item", "els => els.map(e => e.innerText.trim())"
    )


def main() -> int:
    res: dict = {}
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        ctx = browser.new_context(viewport=settings.VIEWPORT, storage_state=str(settings.LOGIN_STATE), locale="zh-CN")
        ctx.set_default_timeout(15000)
        page = ctx.new_page()
        page.goto(settings.BASE_URL + "#/trace/outsourceWorkHour/outsourceWorkHour", wait_until="domcontentloaded")
        page.wait_for_timeout(3500)

        # A. 查询区工作令号
        wo_search = page.locator(".avue-crud__search input[placeholder*='工作令号']").first
        res["search_readonly"] = wo_search.get_attribute("readonly")
        res["search_class"] = wo_search.get_attribute("class")
        wo_search.click()
        page.wait_for_timeout(1200)
        res["search_items_before_typing"] = len(items(page))
        try:
            wo_search.type("2026111", delay=120)
            page.wait_for_timeout(1500)
            res["search_typing_ok"] = True
            res["search_input_value"] = wo_search.input_value()
            res["search_items_after_typing"] = len(items(page))
        except Exception as e:
            res["search_typing_ok"] = False
            res["search_typing_error"] = str(e)[:200]
        print(json.dumps(res, ensure_ascii=False, indent=2)[:1200])
        page.screenshot(path=str(settings.REPORT_DIR / "probe_search_wo.png"))

        # B. 表单工作令号
        page.keyboard.press("Escape")
        page.get_by_role("button", name=re.compile(r"新\s*增")).first.click()
        page.wait_for_timeout(2000)
        dlg = page.locator(".avue-dialog:visible").first
        wo_form = dlg.locator("input[placeholder*='工作令号']").first
        res["form_readonly"] = wo_form.get_attribute("readonly")
        wo_form.click()
        page.wait_for_timeout(1200)
        res["form_items_before_typing"] = len(items(page))
        try:
            wo_form.type("2026111", delay=120)
            page.wait_for_timeout(1500)
            res["form_typing_ok"] = True
            res["form_input_value"] = wo_form.input_value()
            res["form_items_after_typing"] = len(items(page))
        except Exception as e:
            res["form_typing_ok"] = False
            res["form_typing_error"] = str(e)[:200]
        print(json.dumps({k: v for k, v in res.items() if k.startswith("form")}, ensure_ascii=False, indent=2)[:800])
        page.screenshot(path=str(settings.REPORT_DIR / "probe_search_wo_form.png"))

        OUT.write_text(json.dumps(res, ensure_ascii=False, indent=2), encoding="utf-8")
        browser.close()
    return 0


if __name__ == "__main__":
    sys.exit(main())
