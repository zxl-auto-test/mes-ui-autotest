"""阶段 3：列表页专项探测（查询区、表头列序、分页、行内操作）。"""

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

DUMP = settings.REPORT_DIR / "probe_list2.json"


def main() -> int:
    state = str(settings.LOGIN_STATE)
    out: dict = {}
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        ctx = browser.new_context(viewport=settings.VIEWPORT, storage_state=state, locale="zh-CN")
        ctx.set_default_timeout(15000)
        page = ctx.new_page()
        page.goto(settings.BASE_URL + "#/trace/outsourceWorkHour/outsourceWorkHour", wait_until="domcontentloaded")
        page.wait_for_timeout(3500)

        # 查询区
        out["search_labels"] = page.eval_on_selector_all(
            ".avue-crud__search .el-form-item__label", "els => els.map(e => e.innerText.trim())"
        )
        out["search_inputs"] = page.eval_on_selector_all(
            ".avue-crud__search input",
            "els => els.map(e => ({ph: e.placeholder, ro: e.readOnly, cls: e.className}))",
        )
        out["top_buttons"] = page.eval_on_selector_all(
            ".avue-crud__menu button, .avue-crud__menu .el-button",
            "els => els.map(e => e.innerText.trim()).filter(t => t)",
        )
        print(f"[查询区] label={out['search_labels']}")
        for i in out["search_inputs"]:
            print(f"   input ph={i['ph']!r} readonly={i['ro']}")
        print(f"[顶部按钮] {out['top_buttons']}")

        # 表头：区分固定列 / 序号列 / 操作列
        out["th"] = page.eval_on_selector_all(
            ".el-table__header-wrapper tr th",
            "els => els.map((e,i) => ({i, cls: e.className, colspan: e.colSpan, text: (e.innerText||'').trim().replace(/\\n/g,' ')}))",
        )
        print("[表头]")
        for t in out["th"]:
            print(f"   {t['i']:2} colspan={t['colspan']} cls={t['cls']!r} text={t['text']!r}")

        # 首行单元格与行内按钮
        out["first_row_cells"] = page.eval_on_selector_all(
            ".el-table__body-wrapper tbody tr:first-child td",
            "els => els.map((e,i) => ({i, cls: e.className, text: (e.innerText||'').trim().replace(/\\n/g,' ')}))",
        )
        print("[首行单元格]")
        for c in out["first_row_cells"]:
            print(f"   {c['i']:2} text={c['text']!r}")

        out["pagination"] = page.eval_on_selector_all(
            ".el-pagination", "els => els.map(e => e.innerText.trim().replace(/\\n/g,' '))"
        )
        out["total_text"] = page.locator(".el-pagination__total").first.inner_text() if page.locator(".el-pagination__total").count() else ""
        print(f"[分页] text={out['pagination']} total={out['total_text']!r}")

        # 查询区工作令下拉是否可输入
        wo = page.locator(".avue-crud__search input[placeholder*='工作令号']").first
        wo.click()
        page.wait_for_timeout(1200)
        items = page.eval_on_selector_all(".el-select-dropdown:visible .el-select-dropdown__item", "els => els.map(e=>e.innerText.trim())")
        out["search_wo_items_count"] = len(items)
        out["search_wo_items_head"] = items[:10]
        print(f"[查询区工作令] 选项 {len(items)} 个，前 10={items[:10]}")
        page.locator(".el-select-dropdown__item:visible").filter(has_text=settings.WORK_ORDER).first.click()
        page.wait_for_timeout(800)
        page.get_by_role("button", name=re.compile(r"搜\s*索")).first.click()
        page.wait_for_timeout(3000)
        out["after_search_rows"] = page.locator(".el-table__body-wrapper tbody tr").count()
        out["after_search_total"] = page.locator(".el-pagination__total").first.inner_text() if page.locator(".el-pagination__total").count() else ""
        print(f"[查询后] 行数={out['after_search_rows']} total={out['after_search_total']!r}")

        page.screenshot(path=str(settings.REPORT_DIR / "probe_list2.png"), full_page=True)
        DUMP.write_text(json.dumps(out, ensure_ascii=False, indent=2), encoding="utf-8")
        print(f"[OK] {DUMP}")
        browser.close()
    return 0


if __name__ == "__main__":
    sys.exit(main())
