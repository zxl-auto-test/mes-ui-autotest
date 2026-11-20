"""全局配置：环境变量优先，便于在本地 / 测试 / CI 之间切换。

约定：脚本里禁止硬编码地址与账号，一律从这里取。

⚠️ 开源版说明：本文件里所有与具体环境相关的值都是**占位符**，
运行前必须通过环境变量（或本地临时改默认值）注入真实值，否则连不上被测系统。
凭据请勿写回本文件并提交，详见 README「运行前配置」。
"""

import os
from pathlib import Path

# ---------- 路径 ----------
ROOT = Path(__file__).resolve().parent.parent
STATE_DIR = ROOT / "state"
REPORT_DIR = ROOT / "reports"
LOG_DIR = ROOT / "logs"
LOGIN_STATE = STATE_DIR / "login.json"

# ---------- 环境 ----------
# 换成自己的被测系统地址，如 http://mes.example.com:90
BASE_URL = os.getenv("MES_BASE_URL", "http://your-mes-host:90")
LOGIN_PATH = "/#/login"
LOGIN_URL = BASE_URL + LOGIN_PATH
WORKBENCH_PATH = "/#/basic/workbench/manageWorkbench"

# ---------- 账号 ----------
# 凭据不进代码：用环境变量 MES_USER / MES_PASSWORD 注入。
# 本机临时调试可改默认值，但改动不要提交（发到公网等于把密码贴出去）。
USERNAME = os.getenv("MES_USER", "admin")
PASSWORD = os.getenv("MES_PASSWORD", "")

# ---------- 浏览器 ----------
VIEWPORT = {"width": 1366, "height": 768}  # 对齐车间工控机
HEADLESS = os.getenv("MES_HEADLESS", "0") == "1"  # 默认有头，便于观察；CI 置 1
SLOW_MO = int(os.getenv("MES_SLOWMO", "0"))

# ---------- 超时（毫秒） ----------
TIMEOUT = int(os.getenv("MES_TIMEOUT", "15000"))
NAV_TIMEOUT = int(os.getenv("MES_NAV_TIMEOUT", "30000"))

# ---------- 业务数据（示例值，按被测环境替换） ----------
# 工作令/项目名都是环境绑定数据，通过环境变量注入；保留默认值只是为了脚本能 import。
WORK_ORDER = os.getenv("MES_WORK_ORDER", "WO-1001")  # 主用工作令（数据量较全、可搜索）
WORK_ORDER_2 = os.getenv("MES_WORK_ORDER_2", "WO-1002")  # 字段联动切换用的第二个工作令
PROJECT_OF_WO = os.getenv("MES_PROJECT", "示例项目")  # WORK_ORDER 对应的项目名称
CRAFT = os.getenv("MES_CRAFT", "机加")  # 工种字典首项
DATA_PREFIX = "AUTO-"  # 自动化造数统一前缀，便于识别与清理

# ---------- 常态化执行 ----------
# 企业微信群机器人 webhook：建一个只有自己的企微群 → 群设置 → 群机器人 → 添加，
# 把 webhook 地址设到环境变量 MES_WECOM_WEBHOOK。留空 = 只写日志不推送。
WECOM_WEBHOOK = os.getenv("MES_WECOM_WEBHOOK", "")
NOTIFY_ON_SUCCESS = os.getenv("MES_NOTIFY_SUCCESS", "0") == "1"  # 全绿也播报（默认静默）

REPORT_KEEP_DAYS = 30  # 历史报告保留天数，过期自动清理
LOG_KEEP_DAYS = 90
