"""测试数据辅助：唯一备注生成、动态日期计算。"""

from __future__ import annotations

import time
from datetime import datetime

from config import settings


def unique_remark(tag: str) -> str:
    """造数备注：AUTO-<用例号>-<时间戳>，保证唯一且可识别、可清理。"""
    return f"{settings.DATA_PREFIX}{tag}-{int(time.time())}"


def current_month_prefix() -> str:
    """当前年月，如 2026-11，用于拼日期断言。"""
    return datetime.now().strftime("%Y-%m")
