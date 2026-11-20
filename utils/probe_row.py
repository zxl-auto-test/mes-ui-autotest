"""阶段 3 补充：确认数据行 td 索引（有 fixed 列时 body 可能重复）。"""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from playwright.sync_api import sync_playwright

from config import settings


def main() -> int:
    with sync_playwright() as p:
        b = p.chromium.launch(headless=True)
        c = b.new_context(viewport=settings.VIEWPORT, storage_state=str(settings.LOGIN_STATE), locale="zh-CN")
        c.set_default_timeout(15000)
        pg = c.new_page()
        pg.goto(settings.BASE_URL + "/#/trace/outsourceWorkHour/outsourceWorkHour", wait_until="domcontentloaded")
        pg.wait_for_timeout(4000)

        info = pg.evaluate(
            """() => Array.from(document.querySelectorAll('.el-table__body-wrapper')).map((w, i) => ({
                i, cls: w.className, rows: w.querySelectorAll('tbody tr').length,
                firstRow: Array.from(w.querySelectorAll('tbody tr:first-child td')).map(td => (td.innerText||'').trim().replace(/\\n/g,' '))
            }))"""
        )
        for it in info:
            print(f"wrapper{it['i']} cls={it['cls']!r} rows={it['rows']}")
            print(f"   firstRow={it['firstRow']}")

        print("全局 tr 数:", pg.locator(".el-table__body-wrapper tbody tr").count())
        tr = pg.locator(".el-table__body-wrapper tbody tr").first
        print("tr 内 td 数:", tr.locator("td").count())
        for i in range(tr.locator("td").count()):
            print(f"   td{i}: {tr.locator('td').nth(i).inner_text().strip()!r}")
        print("行内按钮:", [tr.get_by_text(t, exact=True).count() for t in ("详情", "编辑", "删除")])
        b.close()
    return 0


if __name__ == "__main__":
    sys.exit(main())
