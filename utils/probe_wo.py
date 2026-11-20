"""阶段 3：工作令号下拉专项探测（组件类型、选项、选中后联动）。"""

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

DUMP = settings.REPORT_DIR / "probe_wo.json"

JS_POPPERS = """
() => {
  const vis = el => { const r = el.getBoundingClientRect(); return r.width > 0 && r.height > 0; };
  return Array.from(document.querySelectorAll('.el-popper, .el-select-dropdown, .el-autocomplete-suggestion, .el-scrollbar'))
    .filter(vis)
    .map(el => ({
      cls: (el.className || '').toString().slice(0, 100),
      html: el.outerHTML.slice(0, 600),
      items: Array.from(el.querySelectorAll('li, .el-select-dropdown__item')).map(i => (i.innerText || '').trim().slice(0, 30)).slice(0, 15),
    }));
}
"""


def main() -> int:
    state = str(settings.LOGIN_STATE)
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
        print(f"弹窗可见：{dlg.count()}")
        wo = dlg.locator("input[placeholder*='工作令号']").first
        print(f"工作令号控件 class：{wo.get_attribute('class')}")
        parent_cls = wo.evaluate("el => el.parentElement.className")
        print(f"父元素 class：{parent_cls}")
        wo.click()
        page.wait_for_timeout(1500)
        poppers = page.evaluate(JS_POPPERS)
        print(f"点击后浮层 {len(poppers)} 个：")
        for pp in poppers:
            print(f"  - {pp['cls']} items={pp['items']}")

        # 试着输入关键字过滤
        wo.fill(settings.WORK_ORDER)
        page.wait_for_timeout(1500)
        poppers2 = page.evaluate(JS_POPPERS)
        print(f"输入 {settings.WORK_ORDER} 后浮层 {len(poppers2)} 个：")
        for pp in poppers2:
            print(f"  - {pp['cls']} items={pp['items']}")

        page.screenshot(path=str(settings.REPORT_DIR / "probe_wo.png"))
        DUMP.write_text(json.dumps({"after_click": poppers, "after_input": poppers2}, ensure_ascii=False, indent=2), encoding="utf-8")
        print(f"[OK] {DUMP}")
        browser.close()
    return 0


if __name__ == "__main__":
    sys.exit(main())
