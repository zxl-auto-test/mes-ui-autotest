# GitHub 代码开源发布指南（从注册到公开展示）

> 适用场景：把自己的代码项目（如 `09_自动化测试` 自动化框架）推到 GitHub 公开仓库，供他人查看学习
> 版本：v1.0 ｜ 建立：2026-11-20 09:16:14 ｜ 维护：张墨尘 / 小爪

---

## 0. 推之前必读：四条脱敏红线（先看这个再动手）

**代码一旦推上公网，任何人都能下载，且 git 历史会永久保留**——就算以后删除，历史提交里仍然翻得到。所以发布前必须先做"安检"，本项目代码里实测存在以下敏感信息：

| 红线 | 当前位置 | 处理方式 |
|---|---|---|
| ① 真实密码 | `config/settings.py` 里 `PASSWORD` 的默认值，以及注释中记录过的登录密码 | 默认值改成空字符串 `""`，注释里的密码删掉；运行时靠环境变量注入 |
| ② 内网 IP/域名 | `BASE_URL = "http://10.x.x.x:90"` 这类硬编码地址 | 改成 `"http://your-mes-host:90"` 占位符 |
| ③ 企微机器人 webhook 密钥 | `config/settings.py` 的 `WECOM_WEBHOOK` | 默认值清空（代码本来就支持 `MES_WECOM_WEBHOOK` 环境变量） |
| ④ 公司业务文档 | 工作空间里的 PRD、测试用例、环境信息、报告 | **绝不进仓库**——只推代码目录（`09_自动化测试`），不推整个工作空间 |

另有一批产物目录不进仓库：`.venv/`（几百 MB 依赖）、`state/`（登录态 cookie）、`logs/`、`reports/`、`__pycache__/`、`.pytest_cache/`——靠 `.gitignore` 排除，见 4.3 节。

**自检口诀：密码、密钥、内网地址、公司文档，四样清零再 push。**

---

## 1. 注册 GitHub 账号（约 5 分钟）

1. 浏览器打开 `https://github.com` → 右上角 **Sign up**；
2. 填写邮箱（建议用常用邮箱）→ 设置密码（大小写+数字+符号）→ 起用户名（**对外展示的招牌，慎重起**，以后仓库地址都是 `github.com/你的用户名/仓库名`）；
3. 人机验证 → 邮箱收验证码填入 → 完成注册；
4. 免费个人账户（Free plan）对公开仓库没有数量限制，够用，不用付费。

---

## 2. 安装配置 Git（约 10 分钟）

### 2.1 安装 Git for Windows

1. 打开 `https://git-scm.com/download/win` → 下载 → 一路 Next 默认安装；
2. 装完桌面右键出现 **Open Git Bash here** 即成功。

### 2.2 首次配置（身份标识，提交记录要署名）

打开 Git Bash（或 cmd），逐行执行：

```bash
git config --global user.name "你的GitHub用户名"
git config --global user.email "你的注册邮箱"
```

---

## 3. 在 GitHub 上创建仓库（约 3 分钟）

1. 登录 GitHub → 右上角 **+** → **New repository**；
2. 填写：
   - **Repository name**：仓库名，如 `mes-ui-autotest`（英文小写+连字符最规范）；
   - **Description**：一句话介绍，如 `MES 系统 Web UI 自动化测试框架（pytest + Playwright）`；
   - **Public / Private**：选 **Public**（公开，别人可见）——这就是"公开展示"的开关；
   - **不要勾选** "Add a README"、"Add .gitignore"、"Choose a license"（本地已有代码，勾了会造成首次推送冲突）；
3. 点 **Create repository** → 页面会显示仓库地址，复制 HTTPS 地址备用：
   `https://github.com/你的用户名/mes-ui-autotest.git`

---

## 4. 本地准备（脱敏 + 初始化，关键步骤）

### 4.1 复制出一份"发布专用"目录（推荐做法）

不在原目录直接操作，复制一份干净副本再清理，原目录继续日常跑定时任务互不干扰：

```
把 `D:\MesTest\09_自动化测试` 复制为 `D:\MesTest\09_自动化测试 - publish`（名称随意，含空格要加引号）
```

以下命令都在发布目录里执行。

### 4.2 脱敏：改 config/settings.py

把默认值改为占位（对照 0 节红线逐条清）：

```python
BASE_URL = os.getenv("MES_BASE_URL", "http://your-mes-host:90")
PASSWORD = os.getenv("MES_PASSWORD", "")          # 空默认值，凭据不进代码
WECOM_WEBHOOK = os.getenv("MES_WECOM_WEBHOOK", "")  # 同上
```

并删除注释里出现过的真实密码。README 里注明"运行前需配置环境变量或本地修改 config"。

### 4.3 新建 .gitignore（排除产物与凭据）

在发布目录根下建 `.gitignore` 文件，内容：

```gitignore
.venv/
state/
logs/
reports/
__pycache__/
*.pyc
.pytest_cache/
.vscode/
.idea/
```

**验证方法**：`git status` 里不该出现以上任何文件。

### 4.4 最后安检

```bash
# 在发布目录全局搜一遍敏感特征，命中任何一处都回 4.2 重改
grep -rniE "qyapi\.weixin\.qq\.com/cgi-bin/webhook/send\?key=[0-9a-f-]{16}" .
grep -rniE "https?://(10|172|192)\.[0-9]+\.[0-9]+\.[0-9]+" .
grep -rni "password *=" --include=*.py .
```

前两条查密钥与内网地址，第三条人工看一遍 `settings.py` 里 `PASSWORD` 的默认值是否为空。
**建议把自己的密码片段也临时拼进 grep 里搜一次，搜完清掉历史命令记录**——最保险的是"搜自己知道的那个字符串"。

### 4.5 脱敏完成清单（发布前逐项打勾）

| # | 项 | 位置 | 状态 |
|---|---|---|---|
| 1 | 密码默认值清空 | `config/settings.py` `PASSWORD` | ☐ |
| 2 | 内网地址改占位符 | `config/settings.py` `BASE_URL`、`check_env.py` | ☐ |
| 3 | webhook 清空 | `config/settings.py` `WECOM_WEBHOOK` | ☐ |
| 4 | 业务数据（工作令号/项目名）占位 | `config/settings.py` 业务数据段 | ☐ |
| 5 | 文档里的地址/账号脱敏 | README、元素定位清单、全流程文档 | ☐ |
| 6 | `.gitignore` 生效 | 仓库根 `.gitignore` | ☐ |
| 7 | 全局 grep 无命中 | 全目录 | ☐ |

---

## 5. 初始化并首次推送（约 5 分钟）

在发布目录打开 Git Bash，按顺序执行：

```bash
cd "/d/MesTest/09_自动化测试 - publish"

# 1) 初始化本地仓库
git init

# 2) 建立主分支
git branch -M main

# 3) 添加文件（.gitignore 会自动过滤掉排除项）
git add .

# 4) 提交（-m 后是提交说明，写清楚这是什么）
git commit -m "MES Web UI 自动化测试框架：pytest + Playwright + 登录态复用 + 定时回归"

# 5) 关联远端仓库（地址换成你第 3 步复制的）
git remote add origin https://github.com/你的用户名/mes-ui-autotest.git

# 6) 推送（首次会弹浏览器要求登录 GitHub 授权，点授权即可）
git push -u origin main
```

> **认证说明**：新版 Git 首次 push 会弹浏览器登录 GitHub 授权，授权一次后续记住凭据。如果走的是 token 方式：GitHub → Settings → Developer settings → Personal access tokens → 生成后当密码用。

刷新 GitHub 仓库页面，代码上去了——**此刻起全世界都能看到**。

---

## 6. 公开展示的加分项（可选，约 20 分钟）

| 项目 | 怎么做 | 效果 |
|---|---|---|
| 完善 README | 顶部放项目简介 + 技术栈（pytest/Playwright）+ 运行方式 + 目录结构 | 别人 30 秒看懂这是什么 |
| 加 LICENSE | GitHub 页面 → Add file → Create new file → 输入 `LICENSE` → 右侧选 MIT → Commit | 没有许可证别人不敢用你的代码；个人展示 MIT 最常用 |
| 加 .gitignore 模板 | 建仓时 GitHub 提供 Python 模板，或参考 4.3 | 防止后续误传垃圾文件 |
| 仓库主页美化 | Settings → General 里可加 Website、Topics 标签（如 `pytest` `playwright` `automation-testing`） | 搜索曝光度 |
| 提交记录整洁 | 每次提交写有意义的 `-m` 说明 | 展示工程素养 |

---

## 7. 日常更新流程（以后改了代码怎么同步）

```bash
git add .                       # 暂存改动
git commit -m "本次改了什么"      # 提交
git push                        # 推上去（以后不用 -u origin main）
```

三步口诀：**add → commit → push**。GitHub 网页上改过的文件，本地先 `git pull` 拉下来再改，避免冲突。

---

## 8. 常见问题

| 问题 | 原因与解决 |
|---|---|
| push 提示 Authentication failed | 密码方式已废弃：用浏览器授权登录，或改用 Personal Access Token 当密码 |
| push 提示 rejected (fetch first) | 远端有你本地没有的提交（比如网页上建过 README）：先 `git pull --rebase` 再 push |
| `git add .` 后 venv/reports 还在列表里 | `.gitignore` 没生效：确认文件名无误；若已 add 过先 `git rm -r --cached .` 再重新 add |
| 手滑把密码推上去了 | **立即**改掉泄露的密码/webhook；仅删文件不够——历史提交里还在，最干净的做法是删仓库重建 |
| 想临时隐藏仓库 | Settings → General → 拉到底 Danger Zone → Change visibility → Private |

---

## 9. 安全红线回顾（每次发布前过一遍）

1. 密码/密钥/内网地址/公司文档——四样清零；
2. `.gitignore` 里的产物目录一个都不许进 `git status`；
3. 只推代码目录，不推整个工作空间；
4. push 前 `grep` 全局搜一遍敏感词；
5. 公开仓库 = 永久公开（含历史），拿不准的内容不要传。

---

## 变更记录

| 版本 | 时间 | 内容 | 作者 |
|---|---|---|---|
| v1.0 | 2026-11-20 09:16:14 | 建立指南：脱敏四红线、GitHub 注册、Git 安装配置、建仓、本地初始化、首次推送、公开展示加分项、日常更新、常见问题 | 小爪 |
