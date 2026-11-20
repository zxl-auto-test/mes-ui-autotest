"""清理自动化造数：只删除「备注」列以 AUTO- 开头的行，其他数据一律不动。

用法：
    .venv/Scripts/python.exe utils/cleanup_auto.py           # 预览要删的行（不删）
    .venv/Scripts/python.exe utils/cleanup_auto.py --apply   # 真正删除
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from playwright.sync_api import sync_playwright

from config import settings
from pages.worktime_page import WorktimePage


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--apply", action="store_true", help="真正执行删除，缺省只预览")
    args = ap.parse_args()

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        ctx = browser.new_context(
            viewport=settings.VIEWPORT, storage_state=str(settings.LOGIN_STATE), locale="zh-CN"
        )
        ctx.set_default_timeout(15000)
        page = ctx.new_page()
        wt = WorktimePage(page)
        wt.open()

        removed = 0
        for _ in range(30):  # 安全上限
            idx = -1
            remark = ""
            for i in range(wt.row_count()):
                row = wt.rows().nth(i)
                text = wt.cell(row, "备注")
                if text.startswith(settings.DATA_PREFIX):
                    idx, remark = i, text
                    break
            if idx < 0:
                break
            print(f"[{'删除' if args.apply else '待删'}] 第 {idx + 1} 行 备注={remark}")
            if not args.apply:
                break  # 预览：只报一条示例，避免刷屏
            wt.row_action(idx, "删除").click()
            box = page.locator(".el-message-box:visible")
            box.wait_for(state="visible")
            box.get_by_role("button", name="确定").first.click()
            wt.wait_table_loaded()
            removed += 1

        print(f"[完成] 共 {removed if args.apply else '（预览）'} 条；当前列表：{wt.total_text()}")
        browser.close()
    return 0


if __name__ == "__main__":
    sys.exit(main())
