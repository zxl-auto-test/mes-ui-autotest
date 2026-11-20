"""常态化执行入口（阶段 7）：探活 → 回归 → 时间戳报告 → 企微通知。

由 run_nightly.bat（任务计划）调用，也可手动运行：
    python utils/nightly_run.py              # 正常执行
    python utils/nightly_run.py --simulate-invalid   # 演练「登录态失效」分支

退出码：0=回归通过；2=回归有失败；3=登录态失效（未跑回归）；4=执行器崩溃（已通知人工）。
"""

from __future__ import annotations

import argparse
import datetime as dt
import subprocess
import sys
import time
import traceback
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from config import settings  # noqa: E402
from utils.notify import send_text  # noqa: E402


def log(msg: str) -> None:
    """同时打到控制台和 logs/nightly_YYYYMMDD.log。"""
    settings.LOG_DIR.mkdir(exist_ok=True)
    stamp = dt.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    line = f"[{stamp}] {msg}"
    print(line, flush=True)
    log_file = settings.LOG_DIR / f"nightly_{dt.datetime.now():%Y%m%d}.log"
    with open(log_file, "a", encoding="utf-8") as f:
        f.write(line + "\n")


def probe_login(retries: int = 2, delay_sec: int = 30) -> bool:
    """用已保存的登录态打开工作台，判断是否仍有效。

    网络抖动导致的瞬时超时不等于登录态失效——先重试，再下结论，
    避免把"环境慢"误报成"请人工续登"（2026-11-17 实测踩坑）。
    """
    if not settings.LOGIN_STATE.exists():
        return False
    from playwright.sync_api import sync_playwright

    last_exc: Exception | None = None
    for attempt in range(1, retries + 1):
        try:
            with sync_playwright() as p:
                browser = p.chromium.launch(headless=True)
                ctx = browser.new_context(viewport=settings.VIEWPORT, storage_state=str(settings.LOGIN_STATE), locale="zh-CN")
                # 探活只判断"能否打开"，超时放宽到 45s：后端慢时段（如 17:00 前后）
                # 页面加载实测可达 20s+，15s 会被误判为失效（2026-11-17 实测踩坑）
                ctx.set_default_timeout(45000)
                page = ctx.new_page()
                page.goto(settings.BASE_URL + settings.WORKBENCH_PATH, wait_until="domcontentloaded")
                page.wait_for_timeout(2000)
                valid = "login" not in page.url
                browser.close()
                return valid
        except Exception as exc:  # 超时/启动失败等瞬时故障
            last_exc = exc
            log(f"探活第 {attempt}/{retries} 次异常：{type(exc).__name__}: {exc}")
            if attempt < retries:
                time.sleep(delay_sec)
    raise RuntimeError(f"探活连续 {retries} 次失败") from last_exc


def run_regression() -> tuple[int, str, Path]:
    """跑全量回归，返回（退出码, 结果摘要行, 报告路径）。"""
    ts = dt.datetime.now().strftime("%Y%m%d_%H%M")
    report = settings.REPORT_DIR / f"run_{ts}.html"
    settings.REPORT_DIR.mkdir(exist_ok=True)
    cmd = [sys.executable, "-m", "pytest", "-q", "--html", str(report), "--self-contained-html"]
    proc = subprocess.run(cmd, cwd=ROOT, capture_output=True, text=True, encoding="utf-8", errors="replace")
    tail = [ln for ln in (proc.stdout or "").strip().splitlines() if ln.strip()]
    summary = tail[-1] if tail else "(无输出)"
    return proc.returncode, summary, report


def cleanup_old_reports() -> None:
    """按保留天数清理历史报告与日志，防止盘被吃满。"""
    now = dt.datetime.now()
    for pattern, keep in (("run_*.html", settings.REPORT_KEEP_DAYS), ("nightly_*.log", settings.LOG_KEEP_DAYS)):
        folder = settings.REPORT_DIR if pattern.startswith("run_") else settings.LOG_DIR
        if not folder.exists():
            continue
        for f in folder.glob(pattern):
            age_days = (now - dt.datetime.fromtimestamp(f.stat().st_mtime)).days
            if age_days > keep:
                f.unlink(missing_ok=True)
                log(f"清理过期文件：{f.name}（{age_days} 天前）")


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--simulate-invalid", action="store_true", help="演练登录态失效分支")
    args = ap.parse_args()

    log("===== 定时回归开始 =====")
    try:
        cleanup_old_reports()
    except Exception as exc:  # 清理失败不影响主流程
        log(f"清理过期文件异常（忽略）：{type(exc).__name__}: {exc}")

    # 1) 探活
    valid = False if args.simulate_invalid else probe_login()
    log(f"登录态探活：{'有效' if valid else '失效'}")
    if not valid:
        send_text(
            "【MES 自动化】登录态已失效，今晚回归未执行。\n"
            "请上班后运行：09_自动化测试 目录下\n"
            "  .venv\\Scripts\\python.exe utils\\save_login_state.py\n"
            "（验证码由张墨尘识别），保存后当晚自动恢复。"
        )
        log("退出码 3（登录态失效）")
        return 3

    # 2) 回归
    code, summary, report = run_regression()
    log(f"回归完成：{summary}")
    log(f"报告：{report}")

    # 3) 通知
    if code == 0:
        if settings.NOTIFY_ON_SUCCESS:
            send_text(f"【MES 自动化】每日回归全绿 ✅\n{summary}\n报告：reports\\{report.name}")
    else:
        send_text(
            f"【MES 自动化】夜间回归有失败 ❌\n{summary}\n"
            f"报告：reports\\{report.name}\n失败截图见 reports\\fail_*.png"
        )
    log(f"===== 定时回归结束，退出码 {code} =====")
    return 0 if code == 0 else 2


if __name__ == "__main__":
    try:
        sys.exit(main())
    except SystemExit:
        raise
    except Exception:
        # 崩溃兜底：任何未捕获异常都要留证据 + 叫人，不允许静默失败
        err = traceback.format_exc()
        log("执行器崩溃（未捕获异常），堆栈如下：")
        for ln in err.strip().splitlines():
            log(f"    {ln}")
        send_text(
            "【MES 自动化】定时回归执行器崩溃 ❌\n"
            f"原因摘要：{type(sys.exc_info()[1]).__name__}: {sys.exc_info()[1]}\n"
            "详见 logs\\nightly_*.log 堆栈；请手动运行 run_nightly.bat 复现。"
        )
        sys.exit(4)
