"""阶段 3：定位 POC —— 一次性打印页面真实 DOM 结构，产出可靠选择器。

不猜 selector，全部实测：
    1) 侧边栏菜单（折叠态 → 一级菜单弹层）
    2) 列表页：查询条件字段、按钮、表头、行数
    3) 新增弹窗：全部表单项（label + placeholder + 是否只读）
    4) 每步截图

用法：
    .venv/Scripts/python.exe utils/probe_dom.py
输出：
    reports/probe_list.png / probe_dialog.png / probe_dom.json
"""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from playwright.sync_api import Page, sync_playwright

from config import settings

REPORT = settings.REPORT_DIR
DUMP = REPORT / "probe_dom.json"

TOP_MENU = "工时管理"
SUB_MENU = "外包工时"

JS_FORM_ITEMS = """
(scope) => {
  const root = document.querySelector(scope) || document.body;
  const items = Array.from(root.querySelectorAll('.el-form-item'));
  return items.map(fi => {
    const labelEl = fi.querySelector('.el-form-item__label');
    const label = labelEl ? labelEl.innerText.trim() : '';
    const fields = Array.from(fi.querySelectorAll('input, textarea')).map(i => ({
      tag: i.tagName.toLowerCase(),
      ph: i.placeholder || '',
      type: i.type || '',
      value: i.value || '',
      readonly: !!i.readOnly,
      disabled: !!i.disabled,
      cls: (i.className || '').toString().slice(0, 60),
    }));
    return { label, required: (fi.className || '').includes('is-required'), fields };
  }).filter(x => x.label || x.fields.length);
}
"""

JS_BUTTONS = """
(scope) => {
  const root = document.querySelector(scope) || document.body;
  return Array.from(root.querySelectorAll('button, .el-button'))
    .map(b => ({ text: (b.innerText || '').trim().slice(0, 30), cls: (b.className || '').toString().slice(0, 60) }))
    .filter(b => b.text);
}
"""

JS_TABLE = """
() => {
  const t = document.querySelector('.el-table');
  if (!t) return null;
  const heads = Array.from(t.querySelectorAll('.el-table__header-wrapper th .cell')).map(c => c.innerText.trim());
  const rows = t.querySelectorAll('.el-table__body-wrapper tbody tr').length;
  const firstRow = Array.from(t.querySelectorAll('.el-table__body-wrapper tbody tr:first-child td .cell')).map(c => c.innerText.trim());
  return { heads, rows, firstRow };
}
"""


def open_menu(page: Page, top: str, sub: str) -> bool:
    """折叠态侧边栏：点一级 → 弹层里点子项。"""
    title = page.locator(f".el-submenu__title:has-text('{top}')").first
    if title.count() == 0:
        print(f"[menu] 一级菜单未找到：{top}")
        return False
    title.scroll_into_view_if_needed()
    title.click()
    page.wait_for_timeout(1200)

    for scope in (".el-menu--popup:visible ", ""):
        item = page.locator(f"{scope}.el-menu-item:has-text('{sub}')").first
        if item.count() > 0:
            item.click()
            page.wait_for_timeout(2500)
            print(f"[menu] 点击 {top} → {sub}，当前地址：{page.url}")
            return True
    print(f"[menu] 子菜单未找到：{sub}")
    return False


def main() -> int:
    REPORT.mkdir(parents=True, exist_ok=True)
    state = str(settings.LOGIN_STATE) if settings.LOGIN_STATE.exists() else None
    if not state:
        print("缺少 state/login.json，先跑 utils/save_login_state.py")
        return 1

    out: dict = {}
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        ctx = browser.new_context(viewport=settings.VIEWPORT, storage_state=state, locale="zh-CN")
        ctx.set_default_timeout(15000)
        page = ctx.new_page()

        page.goto(settings.BASE_URL + settings.WORKBENCH_PATH, wait_until="domcontentloaded")
        page.wait_for_timeout(2500)

        if not open_menu(page, TOP_MENU, SUB_MENU):
            page.screenshot(path=str(REPORT / "probe_menu_fail.png"))
            browser.close()
            return 2

        page.wait_for_timeout(2000)
        page.locator(".el-loading-mask").first.wait_for(state="hidden", timeout=15000) if page.locator(".el-loading-mask").count() else None
        out["url_list"] = page.url
        out["table"] = page.evaluate(JS_TABLE)
        out["query_form"] = page.evaluate(JS_FORM_ITEMS, "body")
        out["buttons"] = page.evaluate(JS_BUTTONS, "body")
        page.screenshot(path=str(REPORT / "probe_list.png"), full_page=True)

        t = out["table"] or {}
        print(f"[list] 地址：{page.url}")
        print(f"[list] 表头 {len(t.get('heads', []))} 列：{t.get('heads')}")
        print(f"[list] 行数：{t.get('rows')}")
        print(f"[list] 首行：{t.get('firstRow')}")
        print(f"[list] 按钮：{[b['text'] for b in out['buttons']][:20]}")
        print("[list] 查询表单：")
        for item in out["query_form"]:
            desc = ", ".join(f"{f['ph'] or f['type']}" for f in item["fields"])
            print(f"      - {item['label']!r} required={item['required']} -> {desc}")

        # 注意：ElementUI 两字按钮中间有空格（"新 增"），必须用正则
        add = page.get_by_role("button", name=re.compile(r"新\s*增")).first
        if add.count() == 0:
            print("[dialog] 未找到「新增」按钮")
        else:
            add.click()
            page.wait_for_timeout(2500)
            dlg = page.locator(".el-dialog:visible").last
            out["dialog_title"] = dlg.locator(".el-dialog__header").inner_text().strip() if dlg.count() else ""
            out["dialog_form"] = page.evaluate(JS_FORM_ITEMS, ".el-dialog")
            out["dialog_buttons"] = page.evaluate(JS_BUTTONS, ".el-dialog")
            page.screenshot(path=str(REPORT / "probe_dialog.png"))
            print(f"[dialog] 标题：{out['dialog_title']}")
            for item in out["dialog_form"]:
                desc = ", ".join(
                    f"{f['tag']}(ph={f['ph']}|t={f['type']}|v={f['value']}|ro={f['readonly']})" for f in item["fields"]
                )
                print(f"      - {item['label']!r} required={item['required']} -> {desc}")
            print(f"[dialog] 按钮：{[b['text'] for b in out['dialog_buttons']]}")

        DUMP.write_text(json.dumps(out, ensure_ascii=False, indent=2), encoding="utf-8")
        print(f"[OK] 结构已存：{DUMP}")
        browser.close()
    return 0


if __name__ == "__main__":
    sys.exit(main())
