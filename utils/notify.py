"""企微群机器人通知（阶段 7）。

用法：python utils/notify.py "消息文本"
webhook 未配置时只写日志，不报错——方便未接入企微前先跑通全流程。
"""

from __future__ import annotations

import json
import sys
import urllib.request
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from config import settings  # noqa: E402


def send_text(text: str) -> bool:
    """推送文本消息到企微群机器人。返回是否真正发送。"""
    webhook = settings.WECOM_WEBHOOK.strip()
    if not webhook:
        print(f"[通知-未配置] {text}")
        return False
    payload = json.dumps({"msgtype": "text", "text": {"content": text}}).encode("utf-8")
    req = urllib.request.Request(
        webhook, data=payload, headers={"Content-Type": "application/json"}
    )
    try:
        with urllib.request.urlopen(req, timeout=10) as resp:
            body = json.loads(resp.read().decode("utf-8") or "{}")
            # 企微成功返回 {"errcode":0,"errmsg":"ok"}，关键词不匹配等错误仍是 HTTP 200
            if body.get("errcode", 0) == 0:
                print(f"[通知] 已推送成功：{text}")
                return True
            print(f"[通知-被拒] errcode={body.get('errcode')} errmsg={body.get('errmsg')}")
            return False
    except Exception as exc:  # 通知失败不影响主流程
        print(f"[通知-失败] {exc}：{text}")
        return False


if __name__ == "__main__":
    msg = sys.argv[1] if len(sys.argv) > 1 else "测试消息：MES 自动化通知链路"
    sys.exit(0 if send_text(msg) else 1)
