# MES Web 端 UI 自动化测试

> 建立：2026-11-16 13:15:31 ｜ 最后更新：2026-11-20 16:13:48 ｜ 维护：张张 / 小爪
>
> 方法文档：`Web端UI自动化测试全流程.md` ｜ 范围清单：`自动化范围清单.md` ｜ 定位清单：`元素定位清单.md`

被测系统：MES 数据采集系统（Vue + Element UI + Avue/BladeX）  
测试环境：`http://your-mes-host:90/#/login`（默认账号 admin，密码走环境变量，见下节）  
本批范围：外包工时管理 —— 8 条业务脚本 + 1 条登录态前置，**11 个用例项连跑 3 轮 0 失败**

---

## ⚡ Quick Start（新环境从零跑通，约 10~15 分钟）

clone 之后**不能直接 `pytest`**——仓库不含解释器、浏览器内核、登录态和真实配置。按下面 5 步走（默认 Windows + Git Bash）：

```bash
# 1) 建 Python 3.10 虚拟环境并装依赖
python -m venv .venv
./.venv/Scripts/python.exe -m pip install -i https://pypi.tuna.tsinghua.edu.cn/simple -r requirements.txt

# 2) 下载 Playwright 浏览器内核（约 130MB，新环境必须执行一次）
./.venv/Scripts/python.exe -m playwright install chromium

# 3) 配置被测环境（7 个变量，见下一节「运行前配置」）
export MES_BASE_URL="http://你的MES地址:90"
export MES_USER="admin"
export MES_PASSWORD="你的密码"

# 4) 生成登录态。验证码是半自动闭环：
#    脚本把验证码截图到 state/captcha.png → 你打开图片看一眼，
#    把 4 位答案写进 state/captcha_answer.txt → 脚本轮询读到后自动填入并登录
./.venv/Scripts/python.exe utils/save_login_state.py

# 5) 先跑冒烟自检，绿了再跑全量
./.venv/Scripts/python.exe -m pytest -m smoke
./.venv/Scripts/python.exe -m pytest
```

**重要认知——这个仓库能复用什么、不能复用什么**：
- ✅ 可复用的是**框架层**：`pages/base_page.py`（等待/弹窗/表格/菜单等公共能力）、验证码登录态闭环、造数清理、HTML 报告、定时回归 + 通知；
- ❌ **用例层不可移植**：11 条用例是针对特定 MES 实例的「外包工时管理」页面编写的（15 列表头、工作令字典、字段联动都是实测写死的）。换一个被测系统，业务用例必然失败——需要按你的系统重写 `pages/` 里的页面对象和 `tests/` 里的用例。

---

## 〇、运行前配置（必读）

仓库里所有环境地址、账号、业务数据都是**占位符**，直接跑必失败。两种方式二选一：

**方式 A：环境变量（推荐，凭据不落盘）**

```bash
export MES_BASE_URL="http://你的MES地址:90"
export MES_USER="admin"
export MES_PASSWORD="你的密码"
export MES_WORK_ORDER="你的工作令号"        # 列表里数据较全的一条
export MES_WORK_ORDER_2="另一条工作令号"    # 用于字段联动用例
export MES_PROJECT="该工作令对应的项目名"
export MES_CRAFT="机加"
# 可选：企微群机器人通知
export MES_WECOM_WEBHOOK="https://qyapi.weixin.qq.com/cgi-bin/webhook/send?key=你的key"
```

Windows 用 `set`（cmd）或 `$env:MES_BASE_URL="..."`（PowerShell）。

**方式 B：本地改 `config/settings.py` 默认值**——方便，但**改完不要提交**（公网仓库 = 永久公开，含历史）。`.gitignore` 已预留 `config/local_settings.py` 与 `.env`。

| 变量 | 作用 | 默认 |
|---|---|---|
| `MES_BASE_URL` | 被测系统根地址 | `http://your-mes-host:90` |
| `MES_USER` / `MES_PASSWORD` | 登录账号（密码默认空） | `admin` / 空 |
| `MES_WORK_ORDER` / `MES_WORK_ORDER_2` | 用例依赖的工作令 | `WO-1001` / `WO-1002` |
| `MES_PROJECT` / `MES_CRAFT` | 联动校验的项目名、工种类别 | `示例项目` / `机加` |
| `MES_HEADLESS` | `1`＝无头执行 | `0` |
| `MES_WECOM_WEBHOOK` | 企微群机器人通知，留空只写日志 | 空 |


---

## 一、目录结构

```
09_自动化测试/
├─ .venv/              虚拟环境（Python 3.10.11，勿提交 git）
├─ config/settings.py  环境、账号、视口、超时、业务数据、造数前缀
├─ pages/              页面对象（元素与操作都在这里）
│  ├─ base_page.py     公共能力：等待、提示、弹窗、表格、菜单
│  ├─ login_page.py    登录页
│  └─ worktime_page.py 外包工时管理页（列表 + 查询 + 新增/编辑弹窗）
├─ tests/              用例（只写业务动作与断言）
│  ├─ conftest.py      浏览器/上下文/登录态/造数清理/失败截图
│  ├─ test_00_smoke.py 框架自检（3）
│  ├─ test_01_list.py  TC-001、TC-008
│  ├─ test_02_add.py   TC-018、TC-022、TC-024、TC-033、TC-039
│  └─ test_03_edit.py  TC-051
├─ utils/
│  ├─ save_login_state.py  登录一次、存会话
│  ├─ cleanup_auto.py      按 AUTO- 备注清理造数
│  ├─ data_helper.py       唯一备注、日期辅助
│  └─ probe_*.py           阶段 3 定位探测（留档，平时不用跑）
├─ state/              登录态 login.json（勿提交 git）
├─ reports/            失败截图、探测快照、HTML 报告
├─ check_env.py        阶段 1 环境验证
├─ pytest.ini          pytest 配置与 marker
└─ requirements.txt    依赖锁定
```



---

## 二、环境（已就绪）

| 项     | 值                                                              |
| ----- | -------------------------------------------------------------- |
| 解释器   | `<仓库路径>\.venv\Scripts\python.exe`（Python 3.10.11） |
| 依赖    | playwright 1.65.2 / pytest 9.2.0 / pytest-xdist / pytest-html  |
| 浏览器内核 | `%LOCALAPPDATA%\ms-playwright\`（**仅原作者机器**已缓存 chromium-1255）         |

**⚠️ 关于 `playwright install`，分两种情况**：
- **新环境（clone 本仓库的人）**：必须先执行 `./.venv/Scripts/python.exe -m playwright install chromium`，否则用例起不来；
- **原作者本机**：内核已缓存且与 playwright 1.65.2 匹配，**不要运行**——它装完会清理"过期内核"，可能删掉缓存里的其他浏览器版本。

换机器重建环境：

```bash
"C:\Program Files\Python310\python.exe" -m venv .venv
./.venv/Scripts/python.exe -m pip install -i https://pypi.tuna.tsinghua.edu.cn/simple -r requirements.txt
```

---

## 三、怎么跑

```bash
cd <仓库路径>

# 首次或会话失效后：先存登录态（脚本截图验证码 → 你人工把 4 位答案写入
# state/captcha_answer.txt → 脚本自动填入登录；详见第四节）
./.venv/Scripts/python.exe utils/save_login_state.py

./.venv/Scripts/python.exe -m pytest                       # 全部 11 项，约 85 秒
./.venv/Scripts/python.exe -m pytest -m smoke              # 只跑自检
./.venv/Scripts/python.exe -m pytest -m list               # 只跑列表
./.venv/Scripts/python.exe -m pytest -m add                # 只跑新增
./.venv/Scripts/python.exe -m pytest -m edit               # 只跑编辑
./.venv/Scripts/python.exe -m pytest --headed --slowmo=300  # 有头慢放，肉眼跟看
./.venv/Scripts/python.exe -m pytest --html=reports/report.html --self-contained-html
```

无头（CI）：`MES_HEADLESS=1`。

---

## 四、登录态（会话复用）

验证码是 4 位图形码，脚本本身不做 OCR，闭环是「截图 → **人工识别** → 自动填入」：

```bash
./.venv/Scripts/python.exe utils/save_login_state.py
```

1. 脚本打开登录页，把验证码截图到 `state/captcha.png`
2. 脚本轮询等待 `state/captcha_answer.txt` 被写入识别结果（最多 4 分钟）
3. 读到后自动填入并登录，会话落 `state/login.json`
4. 之后所有用例自动带该会话，不再碰验证码

会话有效期未知，失效时用例会 `SKIPPED` 并提示重跑上面的命令。

---

## 五、本批脚本清单

| # | 脚本                                             | 用例     | 验证内容                            | 耗时   |
| - | ---------------------------------------------- | ------ | ------------------------------- | ---- |
| 1 | `utils/save_login_state.py`                    | 前置链路   | 会话建立与复用                         | ~25s |
| 2 | `test_tc001_list_columns_complete`             | TC-001 | 13 业务列顺序、复选框、操作列 3 按钮           | 7s   |
| 3 | `test_tc008_search_by_work_order`              | TC-008 | 下拉输入过滤 → 选中 → 查询 → 逐行核对         | 8s   |
| 4 | `test_tc018_add_all_fields`                    | TC-018 | 9 字段全填、项目名带出、总金额 800.00、列表逐字段核对 | 15s  |
| 5 | `test_tc022_switch_work_order_updates_project` | TC-022 | 切换工作令 → 项目名称随之更新                | 9s   |
| 6 | `test_tc024_work_order_required`               | TC-024 | 工作令号必填拦截、弹窗不关、列表不增              | 9s   |
| 7 | `test_tc033_total_hours_zero_blocked`          | TC-033 | 总工时 0 → toast「工时须大于0」拦截         | 10s  |
| 8 | `test_tc039_total_hours_truncated`             | TC-039 | 1.236 截断 1.23、总金额 12.30         | 12s  |
| 9 | `test_tc051_recalc_overrides_manual_amount`    | TC-051 | 手改 100.00 → 改总工时 → 覆盖为 1000.00  | 22s  |

---

## 六、加用例的规矩

1. **元素定位只写 `pages/`**，用例层不出现选择器
2. **断言必须精确**：提示文案、具体数值、列名列表；禁止"页面正常"
3. **等待必须条件化**：只用 `expect` / `wait_for` / 文案轮询，禁止 `sleep`
4. **造数备注带 `AUTO-` 前缀**，登记到 `cleanup_zone`，用例结束自动删；不动真实业务数据
5. 一条用例一个检查点，失败能唯一定位
6. 新增一条脚本，必须同步更新本文第五节与 `自动化范围清单.md`

---

## 七、已知坑（全部实测踩过）

| #  | 现象                                 | 原因                                                     | 处理                                         |           |
| -- | ---------------------------------- | ------------------------------------------------------ | ------------------------------------------ | --------- |
| 1  | `has-text('新增')` 永远匹配不到            | ElementUI 两字按钮 DOM 文本带空格：`新 增`/`保 存`/`取 消`/`搜 索`/`清 空` | 一律用正则 `r"新\s*增"`                           |           |
| 2  | 弹窗里读到 0 个字段                        | 页面有 4 个隐藏 `.el-dialog`（用户选择/扫码/详情/导入）                  | 作用域用 `.avue-dialog:visible`                |           |
| 3  | 按 placeholder 定位失败                 | placeholder 含空格（`请选择 工作令号`）；工作令选中后 placeholder 消失      | 按 `.el-form-item` 的 label 文本定位             |           |
| 4  | `fill()` 报 Element is not editable | 工作令号 select 的 input 带 `readonly`                       | 聚焦后用 `type()`                              |           |
| 5  | 编辑弹窗点不到保存                          | 新增是「保 存」，编辑是「修 改」                                      | \`BTN_SAVE = r"(保\s*存                      | 修\s*改)"\` |
| 6  | 行内「删除」点不到（element is not visible）  | 操作列按钮只渲染在 `.el-table__fixed-right`，主表体该格是空 div         | 用 `fixed_rows()` 按行号取按钮                    |           |
| 7  | 日期面板匹配不到某一天                        | `td` 文本带空白，`has_text=^1$` 匹配不上                         | 遍历 `inner_text().strip()` 精确比较             |           |
| 8  | 打开登录页被重定向到工作台                      | 用例 context 带登录态                                        | 登录页检查用独立无状态 context（`anon_page`）           |           |
| 9  | 中文乱码 / 路径报错                        | Windows 默认 GBK                                         | 固定 `PYTHONIOENCODING=utf-8`，代码内用 `pathlib` |           |
| 10 | `el-message` 抓不到                   | 提示 3 秒自动消失                                             | 动作后立即读，或用内置轮询的 `toast_should_contain`      |           |
| 11 | 空表单保存抓不到 toast                     | 必填校验只出字段级红字，不出 toast                                   | 断言 `.el-form-item__error` 文案               |           |

---

## 八、常态化执行（阶段 7，2026-11-16 上线）

每日 **17:00** 由 Windows 任务计划自动执行：`run_nightly.bat` → `utils/nightly_run.py`

流程：**探活登录态 → 全量回归（11 项）→ 时间戳报告 `reports/run_YYYYMMDD_HHMM.html` → 企微通知**

| 情况    | 行为                                      | 退出码 |
| ----- | --------------------------------------- | --- |
| 登录态失效 | 不跑回归，企微发「请人工续登」通知                       | 3   |
| 回归有失败 | 企微发失败摘要 + 报告路径                          | 2   |
| 全绿    | 默认静默（配置 `MES_NOTIFY_SUCCESS=1` 可改为每日播报） | 0   |

手动执行：双击 `run_nightly.bat`，或 `./.venv/Scripts/python.exe utils/nightly_run.py`  
演练失效分支：`utils/nightly_run.py --simulate-invalid`

**企微通知配置**（发给自己）：企业微信建一个只有自己的群 → 群设置 → 群机器人 → 添加 → 复制 webhook 地址 → 填入 `config/settings.py` 的 `WECOM_WEBHOOK`（或环境变量 `MES_WECOM_WEBHOOK`）。未配置时通知只写 `logs/` 日志。

**注册任务计划**（管理员 PowerShell，执行一次即可）：

```powershell
Register-ScheduledTask -TaskName "MES-UI每日回归" `
  -Action (New-ScheduledTaskAction -Execute "<仓库路径>\run_nightly.bat") `
  -Trigger (New-ScheduledTaskTrigger -Daily -At 17:00) `
  -Settings (New-ScheduledTaskSettingsSet -StartWhenAvailable -WakeToRun -ExecutionTimeLimit (New-TimeSpan -Minutes 30)) -Force
```

`-StartWhenAvailable`＝错过（当天没开机）开机后自动补跑；`-WakeToRun`＝睡眠状态自动唤醒执行。

历史文件自动清理：报告保留 30 天、日志保留 90 天（`config/settings.py` 可调）。

---

## 九、数据纪律

- 只创建备注以 `AUTO-` 开头的记录，用例结束由 `cleanup_zone` 自动删除
- 清理兜底：`./.venv/Scripts/python.exe utils/cleanup_auto.py`（预览）／`--apply`（执行）
- 三轮回归后核对：外包工时列表恒为 **13 条**，`AUTO-` 残留 **0**
- 绝不删除、修改真实业务数据（含"通过导入过来的数据；"等历史记录）

---

## 变更记录

| 版本   | 时间                  | 内容                                                                                                    |
| ---- | ------------------- | ----------------------------------------------------------------------------------------------------- |
| v0.1 | 2026-11-16 13:31:00 | 框架搭建完成：配置、BasePage、登录页/工时页对象、conftest、自检用例                                                            |
| v1.0 | 2026-11-16 14:17:25 | 阶段 3~~7 完成：登录态自动闭环、9 条脚本上线、11 项连跑 3 轮全绿（85~~89s/轮）；新增定位清单与 11 条已知坑                                    |
| v1.1 | 2026-11-16 15:36:16 | 阶段 7 落地：run_nightly.bat + nightly_run.py（探活→回归→时间戳报告→企微通知），全链路实测通过（11 passed，109s）；17:00 任务计划注册命令见第八节 |
| v1.2 | 2026-11-20 16:13:48 | 开源适配：新增 Quick Start（新环境 5 步跑通）与"框架可复用/用例不可移植"说明；修正 playwright install 警告的作用范围；明确验证码为人工识别闭环 |
