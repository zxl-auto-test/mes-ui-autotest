"""新增弹窗脚本：TC-018（全字段正向）、TC-022（切换工作令联动）、
TC-024（工作令号必填）、TC-033（总工时 0）、TC-039（总工时截断 1.23）。

数据纪律：所有造数备注带 AUTO- 前缀并登记到 cleanup_zone，用例结束自动删除。
"""

from __future__ import annotations

import pytest

from config import settings
from pages.worktime_page import WorktimePage

from utils.data_helper import current_month_prefix, unique_remark


@pytest.mark.add
@pytest.mark.p0
def test_tc018_add_all_fields(wt: WorktimePage, cleanup_zone):
    """TC-018 新增：9 个字段全填，总金额自动算 800.00，保存后列表行逐字段核对。"""
    remark = unique_remark("TC018")
    cleanup_zone.append(remark)

    wt.open()
    wt.click_add()
    assert wt.dialog_title() == "新增"

    # 选工作令 → 项目名称自动带出且只读
    wt.select_form_option("工作令号", settings.WORK_ORDER, settings.WORK_ORDER)
    project = wt.field_value("项目名称")
    assert project == settings.PROJECT_OF_WO, f"项目名称应为 {settings.PROJECT_OF_WO}，实际 {project!r}"
    assert wt.field("项目名称").is_disabled(), "项目名称应只读"

    wt.select_craft(settings.CRAFT)
    wt.pick_date_range(1, 5)
    wt.fill_fields(人数="2", 总工时="16", 时薪="50")

    # 总金额自动 = 16 × 50
    assert wt.amount_value() == "800.00", f"总金额自动计算异常：{wt.amount_value()!r}"

    wt.field("备注").fill(remark)
    wt.click_save()
    wt.wait_loading_gone()
    assert not wt.dialog_opened(), "保存后弹窗应关闭"

    row = wt.row_by_remark(remark)
    assert row.count() == 1, "列表中未找到刚保存的行"

    values = wt.row_values(row)
    month = current_month_prefix()
    assert values["工作令号"] == settings.WORK_ORDER
    assert values["项目名称"] == settings.PROJECT_OF_WO
    assert values["工种"] == settings.CRAFT
    assert values["日期"] == f"{month}-01 ~ {month}-05", f"日期显示异常：{values['日期']!r}"
    assert values["人数"] == "2"
    assert values["总工时(h)"] == "16.00"
    assert values["时薪(元/h)"] == "50.00"
    assert values["总金额"] == "800.00"
    assert values["备注"] == remark
    assert values["创建人"] == "管理员"
    assert values["更新人"] == "管理员"


@pytest.mark.add
def test_tc022_switch_work_order_updates_project(wt: WorktimePage):
    """TC-022 切换工作令：项目名称随之更新，不残留上一个工作令的项目名称。"""
    wt.open()
    wt.click_add()

    wt.select_form_option("工作令号", settings.WORK_ORDER, settings.WORK_ORDER)
    first = wt.field_value("项目名称")
    assert first == settings.PROJECT_OF_WO, f"首个工作令项目名称异常：{first!r}"

    wt.select_form_option("工作令号", settings.WORK_ORDER_2, settings.WORK_ORDER_2)
    second = wt.field_value("项目名称")
    assert second, "切换工作令后项目名称为空"
    assert second != first, f"项目名称未随工作令更新，仍为 {second!r}"

    wt.click_cancel()


@pytest.mark.add
def test_tc024_work_order_required(wt: WorktimePage):
    """TC-024 工作令号为空：提示必填、弹窗不关闭、列表不新增。"""
    wt.open()
    total_before = wt.total_text()

    wt.click_add()
    wt.select_craft(settings.CRAFT)
    wt.fill_fields(人数="2", 总工时="8", 时薪="50")
    wt.click_save()

    errors = wt.field_errors()
    assert any("工作令号" in e for e in errors), f"未提示工作令号必填，实际错误：{errors}"
    assert wt.dialog_opened(), "校验失败时弹窗不应关闭"

    wt.click_cancel()
    wt.open()
    assert wt.total_text() == total_before, "校验失败却新增了数据"


@pytest.mark.add
def test_tc033_total_hours_zero_blocked(wt: WorktimePage, cleanup_zone):
    """TC-033 总工时输入 0：应拦截（PRD：总工时 > 0）。"""
    remark = unique_remark("TC033")
    cleanup_zone.append(remark)

    wt.open()
    wt.click_add()
    wt.select_form_option("工作令号", settings.WORK_ORDER, settings.WORK_ORDER)
    wt.select_craft(settings.CRAFT)
    wt.fill_fields(人数="2", 总工时="0", 时薪="50")
    wt.field("备注").fill(remark)
    wt.click_save()

    errors = wt.field_errors()
    toast = wt.toast_text(timeout=3000) if wt.page.locator(".el-message:visible").count() else ""
    # 实测：拦截方式为顶部 toast「工时须大于0」，不是字段红字
    intercepted = wt.dialog_opened() and any("工时" in msg for msg in [*errors, toast])
    assert intercepted, f"总工时 0 未被拦截（字段错误={errors}，提示={toast!r}）"

    wt.click_cancel()


@pytest.mark.add
def test_tc039_total_hours_truncated(wt: WorktimePage, cleanup_zone):
    """TC-039 总工时 1.236 → 截断为 1.23（非四舍五入），总金额 1.23×10=12.30。"""
    remark = unique_remark("TC039")
    cleanup_zone.append(remark)

    wt.open()
    wt.click_add()
    wt.select_form_option("工作令号", settings.WORK_ORDER, settings.WORK_ORDER)
    wt.select_craft(settings.CRAFT)
    wt.fill_fields(人数="2", 时薪="10", 总工时="1.236")

    hours_shown = wt.field_value("总工时")
    amount = wt.amount_value()
    assert amount == "12.30", f"总金额应按 1.23×10=12.30，实际 {amount!r}（输入框显示 {hours_shown!r}）"

    wt.field("备注").fill(remark)
    wt.click_save()
    wt.wait_loading_gone()

    row = wt.row_by_remark(remark)
    assert row.count() == 1, "未找到保存后的行"
    assert wt.cell(row, "总工时(h)") == "1.23", f"列表总工时应为 1.23，实际 {wt.cell(row, '总工时(h)')!r}"
