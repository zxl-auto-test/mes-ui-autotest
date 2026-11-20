"""列表页脚本：TC-001（15 列完整展示）、TC-008（工作令号下拉可搜索命中）。

对应用例：04_测试用例/工时管理测试用例.md
"""

from __future__ import annotations

import pytest

from config import settings
from pages.worktime_page import WorktimePage


@pytest.mark.list
@pytest.mark.p0
def test_tc001_list_columns_complete(wt: WorktimePage):
    """TC-001 列表 15 列字段完整展示（顺序按 2026-11-16 实测，已与张墨尘确认）。"""
    wt.open()

    heads = wt.headers()
    assert heads == WorktimePage.COLUMNS, f"表头不符，实际：{heads}"

    # 复选框列在图（行首可勾选）
    first_row = wt.rows().first
    assert first_row.locator(".el-checkbox").count() >= 1, "行首复选框缺失"

    # 操作列 3 个按钮齐全（按钮渲染在右侧固定列）
    fixed_first = wt.fixed_rows().first
    for btn in ("详情", "编辑", "删除"):
        assert fixed_first.get_by_role("button", name=btn).count() == 1, f"操作列缺少「{btn}」"

    # # 序号列：第 2 行序号应递增（td0 为空、序号由表格索引渲染）
    if wt.row_count() >= 2:
        assert wt.rows().nth(0).inner_text().strip() != wt.rows().nth(1).inner_text().strip()

    # 列数与 PRD 一致：13 业务列
    assert len(heads) == 13


@pytest.mark.list
def test_tc008_search_by_work_order(wt: WorktimePage):
    """TC-008 工作令号下拉可搜索：输入关键字过滤 → 选中 → 查询只显示该工作令的行。"""
    wt.open()
    total_before = wt.total_text()

    wt.search_by_work_order(settings.WORK_ORDER)

    total_after = wt.total_text()
    rows = wt.row_count()
    assert rows > 0, f"按工作令 {settings.WORK_ORDER} 查询应有数据，实际 0 行（查询前 {total_before}）"

    for i in range(rows):
        value = wt.cell(wt.rows().nth(i), "工作令号")
        assert value == settings.WORK_ORDER, f"第 {i + 1} 行工作令号为 {value!r}，应为 {settings.WORK_ORDER}"

    assert f"共 {rows} 条" in total_after, f"分页总数与行数不一致：{total_after}"
