"""编辑弹窗脚本：TC-051（改总工时 → 总金额重算并覆盖手改值）。

造数链路（全部 AUTO- 前缀，结束自动清理）：
    新增 16h×50=800.00 → 编辑手改总金额 100.00 保存 → 再编辑把总工时改 20 → 应重算 1000.00
"""

from __future__ import annotations

import pytest

from config import settings
from pages.worktime_page import WorktimePage
from utils.data_helper import unique_remark


@pytest.mark.edit
@pytest.mark.p0
def test_tc051_recalc_overrides_manual_amount(wt: WorktimePage, cleanup_zone):
    """TC-051 改总工时后总金额重算，覆盖此前手改值。"""
    remark = unique_remark("TC051")
    cleanup_zone.append(remark)

    # 1) 造一条 16h × 50 = 800.00 的记录
    wt.open()
    wt.add_record(
        work_order=settings.WORK_ORDER,
        craft=settings.CRAFT,
        people="2",
        hours="16",
        rate="50",
        remark=remark,
    )
    wt.wait_loading_gone()
    row = wt.row_by_remark(remark)
    assert row.count() == 1, "造数失败：列表未找到记录"
    assert wt.cell(row, "总金额") == "800.00"

    # 2) 手改总金额为 100.00 并保存
    wt.click_row_action(remark, "编辑")
    wt.dialog.wait_for(state="visible")
    assert wt.dialog_title() == "编辑"
    assert wt.amount_value() == "800.00", "编辑打开应原样带出已存总金额"
    wt.fill_fields(总金额="100")
    wt.click_save()
    wt.wait_loading_gone()

    row = wt.row_by_remark(remark)
    assert wt.cell(row, "总金额") == "100.00", f"手改后应保存 100.00，实际 {wt.cell(row, '总金额')!r}"

    # 3) 再编辑：只改总工时 16 → 20，时薪 50 不动
    wt.click_row_action(remark, "编辑")
    wt.dialog.wait_for(state="visible")
    assert wt.amount_value() == "100.00", "编辑打开应原样带出手改后的 100.00（不重算）"

    wt.fill_fields(总工时="20")
    recalculated = wt.amount_value()
    assert recalculated == "1000.00", f"改总工时后总金额应重算为 1000.00，实际 {recalculated!r}"

    wt.click_save()
    wt.wait_loading_gone()

    row = wt.row_by_remark(remark)
    values = wt.row_values(row)
    assert values["总金额"] == "1000.00", f"保存后列表总金额应为 1000.00，实际 {values['总金额']!r}"
    assert values["总工时(h)"] == "20.00"
    assert values["时薪(元/h)"] == "50.00"
