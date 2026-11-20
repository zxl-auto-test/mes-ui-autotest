"""阶段 3：新增弹窗第二轮探测 —— 容器、下拉、联动、自动计算。"""

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
DUMP = REPORT / "probe_dialog3.json"

JS_CONTAINERS = """
() => {
  const vis = el => { const r = el.getBoundingClientRect(); return r.width > 0 && r.height > 0; };
  const info = sel => Array.from(document.querySelectorAll(sel)).map(el => ({
    cls: (el.className || '').toString().slice(0, 90),
    visible: vis(el),
    text: (el.innerText || '').trim().slice(0, 40),
    inputs: el.querySelectorAll('input,textarea').length,
  }));
  const chainOf = sel => {
    const el = document.querySelector(sel);
    if (!el) return null;
    const out = [];
    let p = el;
    for (let i = 0; i < 9 && p; i++) { out.push(p.tagName.toLowerCase() + '.' + (p.className || '').toString().trim().replace(/\\s+/g, '.')); p = p.parentElement; }
    return out;
  };
  return {
    dialogs: info('.el-dialog'),
    wrappers: info('.el-dialog__wrapper'),
    drawers: info('.el-drawer'),
    avueDialog: info('.avue-dialog'),
    saveBtnChain: chainOf('.el-dialog button:not(.el-button--primary)') ,
    allBtnChain: (() => {
      const btns = Array.from(document.querySelectorAll('button')).filter(b => /保\\s*存/.test(b.innerText || ''));
      if (!btns.length) return null;
      const out = []; let p = btns[0];
      for (let i = 0; i < 9 && p; i++) { out.push(p.tagName.toLowerCase() + '.' + (p.className || '').toString().trim().replace(/\\s+/g, '.')); p = p.parentElement; }
      return out;
    })(),
  };
}
"""

JS_DROPDOWNS = """
() => Array.from(document.querySelectorAll('.el-select-dropdown')).map(d => ({
  cls: (d.className || '').toString(),
  visible: !!(d.offsetParent !== null),
  items: Array.from(d.querySelectorAll('.el-select-dropdown__item')).map(i => (i.innerText || '').trim()).slice(0, 20),
})).filter(d => d.visible && d.items.length);
"""


def main() -> int:
    REPORT.mkdir(parents=True, exist_ok=True)
    state = str(settings.LOGIN_STATE) if settings.LOGIN_STATE.exists() else None
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

        out["containers"] = page.evaluate(JS_CONTAINERS)
        print("=== 容器 ===")
        print(json.dumps(out["containers"], ensure_ascii=False, indent=2)[:2000])

        # 用「保 存」按钮所在容器作为弹窗作用域
        save_btn = page.get_by_role("button", name=re.compile(r"保\s*存"))
        out["save_btn_count"] = save_btn.count()
        scope = page.locator(".el-dialog:visible").last if out["containers"]["dialogs"] else page

        def field(ph: str):
            return scope.locator(f"input[placeholder*='{ph}']").first

        # 工作令号下拉（弹窗内）
        wo = field("工作令号")
        wo.click()
        page.wait_for_timeout(1200)
        out["dd_wo"] = page.evaluate(JS_DROPDOWNS)
        print("=== 工作令号下拉 ===")
        print(json.dumps(out["dd_wo"], ensure_ascii=False)[:600])
        opt = page.locator(".el-select-dropdown__item:visible").filter(has_text=settings.WORK_ORDER).first
        if opt.count():
            opt.click()
            page.wait_for_timeout(1500)
        proj = scope.locator("input[placeholder*='带出']").first
        out["project"] = proj.input_value() if proj.count() else "(无)"
        print(f"=== 选工作令后「项目名称」= {out['project']!r}")

        # 工种下拉
        field("工种").click()
        page.wait_for_timeout(1200)
        out["dd_craft"] = page.evaluate(JS_DROPDOWNS)
        print("=== 工种下拉 ===")
        print(json.dumps(out["dd_craft"], ensure_ascii=False)[:800])
        items = page.locator(".el-select-dropdown__item:visible")
        if items.count():
            txt = items.first.inner_text().strip()
            items.first.click()
            page.wait_for_timeout(800)
            print(f"=== 选中工种：{txt!r}")

        # 日期：直接点开始日期后按 Esc，观察面板结构
        d0 = scope.locator("input[placeholder='开始日期']").first
        d0.click()
        page.wait_for_timeout(1000)
        out["date_panel"] = page.evaluate(
            """() => { const p = document.querySelector('.el-picker-panel:not([style*="display: none"])');
                        return p ? p.className : null; }"""
        )
        page.keyboard.press("Escape")
        page.wait_for_timeout(500)
        print(f"=== 日期面板 class = {out['date_panel']!r}")

        # 数值联动：人数 2 / 总工时 16 / 时薪 50 → 总金额应 800
        field("人数").fill("2")
        page.keyboard.press("Tab")
        field("总工时").fill("16")
        page.keyboard.press("Tab")
        field("时薪").fill("50")
        page.keyboard.press("Tab")
        page.wait_for_timeout(1200)
        amt = field("总金额")
        out["amount_800"] = amt.input_value()
        print(f"=== 2人×16h×50 → 总金额 = {out['amount_800']!r}")

        # 总金额是否可手改
        amt.fill("1234.56")
        page.wait_for_timeout(600)
        out["amount_after_manual"] = amt.input_value()
        print(f"=== 手改总金额后 = {out['amount_after_manual']!r}，是否只读已在上轮字段表确认")

        # 改总工时看是否重算
        field("总工时").fill("20")
        page.keyboard.press("Tab")
        page.wait_for_timeout(1200)
        out["amount_after_hours20"] = amt.input_value()
        print(f"=== 总工时改 20 → 总金额 = {out['amount_after_hours20']!r}")

        page.screenshot(path=str(REPORT / "probe_dialog3.png"))
        DUMP.write_text(json.dumps(out, ensure_ascii=False, indent=2), encoding="utf-8")
        print(f"[OK] {DUMP}")
        browser.close()
    return 0


if __name__ == "__main__":
    sys.exit(main())
