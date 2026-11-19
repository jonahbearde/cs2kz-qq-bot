# 第二章 第一条 Tip：运行机器人、捕获群标识、测试群收到 Tip

> 本章是《CS2KZ QQ 小贴士机器人操作手册》的第二章，面向零部署经验的维护者。
>
> **本章目标**：把机器人程序跑起来，在测试群 @ 它拿到 `group_openid`，填进配置后重启，让测试群**真实收到第一条 Tip**。这一步验证全项目最大的风险：个人主体机器人的群聊主动推送真的能发出来。
>
> **完成标志**：测试群里出现一条机器人主动发来的纯文本 Tip（不带任何前缀）；你手里有了测试群的 `group_openid`；机器人对任何消息都不回复。
>
> **前提**：第一章验收清单全部勾选（凭据在手、测试群就位、「机器人主动在群聊内发言」已开、连接方式为 WebSocket）。

---

## 0. 先明白本章的机器人会做什么

本章的机器人是"曳光弹"——只打通最窄的一条完整链路，**还没有定时轮播**（那是后续章节的事）。它的行为只有三条：

1. **保持在线**：通过 WebSocket 出站连接挂在 QQ 平台上，不需要公网 IP、域名或 Webhook，家用电脑和服务器都能跑。
2. **被 @ 时只记日志**：把该群的 `group_openid` 醒目地打印出来，供你抄进配置。**绝不回复任何消息**，也不会自动改配置。
3. **启动时发一条 Tip**：如果 `.env` 里已配置 `TARGET_GROUP_OPENID`，上线后立刻向该群主动发送 Tip List 的第一条（纯文本、无前缀）；没配置就安静等待你去 @ 捕获。每次启动只发这一条，断线重连不会重发。

> 调试期间测试群临时充当 Target Group。机器人只向 `.env` 里配置的那个群发 Tip；它在别的群被 @ 也只会记日志，不会串线。

---

## 1. 准备 Python（≥3.8，推荐 3.10 及以上）

### Windows

1. 打开 <https://www.python.org/downloads/>，下载并运行安装包。
2. **安装第一屏务必勾选「Add python.exe to PATH」**，再点 Install Now（⚠️ UI 以实际为准）。
3. 验证：按 `Win + R`，输入 `cmd` 回车，在黑窗口里执行：

   ```bat
   python --version
   ```

   显示 `Python 3.x.x`（≥3.8）即通过。提示"不是内部或外部命令"：重装并勾选 Add to PATH，或重开一个 cmd 窗口。

### Ubuntu

```bash
sudo apt update
sudo apt install -y python3 python3-venv python3-pip
python3 --version
```

显示 `Python 3.x.x`（≥3.8）即通过。Ubuntu 20.04 及以上自带满足要求的版本。

> **✅ 检查点 1**：`python --version`（Windows）或 `python3 --version`（Ubuntu）显示 ≥3.8 的版本号。

---

## 2. 放置代码、创建虚拟环境、安装依赖

把整个项目文件夹放到你要运行机器人的机器上（`git clone` 或直接拷贝均可）。**`.env` 不在仓库里**，每台机器都要按第 3 节单独创建。以下命令都在**项目根目录**（能看到 `tips.txt`、`.env.example` 的那层）执行。

### Windows（cmd）

```bat
cd /d 项目文件夹路径
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
```

激活成功后命令行开头会出现 `(.venv)` 字样。用 PowerShell 的话激活命令是 `.venv\Scripts\Activate.ps1`；若提示"禁止运行脚本"，改用 cmd 最省事。

### Ubuntu

```bash
cd 项目文件夹路径
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

激活成功后命令行开头会出现 `(.venv)` 字样。

> 说明：虚拟环境（`.venv`）把依赖隔离在项目内，不污染系统 Python。以后每次新开终端运行机器人，都要先 `cd` 到项目根目录并重新激活（Windows：`.venv\Scripts\activate`；Ubuntu：`source .venv/bin/activate`）。
>
> 下载慢或超时：可换国内镜像，如 `pip install -r requirements.txt -i https://pypi.tuna.tsinghua.edu.cn/simple`。

> **✅ 检查点 2**：`pip install` 最后显示 `Successfully installed ... qq-botpy-1.2.1 ...`，无红色报错。

---

## 3. 创建 .env 并填入凭据

`.env` 是机器人的配置文件，**已被 git 忽略，永不入库**。先复制占位符示例：

- Windows（cmd）：`copy .env.example .env`
- Ubuntu：`cp .env.example .env`

用文本编辑器打开 `.env`（Windows 记事本即可，保存时编码选 UTF-8；Ubuntu 用 `nano .env`），填入第一章保存的两个值：

```ini
QQ_APP_ID=你的AppID（一串数字）
QQ_APP_SECRET=你的AppSecret
TARGET_GROUP_OPENID=
```

- `TARGET_GROUP_OPENID` **先留空**——下一节 @ 捕获后再填。
- 等号两边不要加引号、不要留多余空格；`#` 开头的行是注释。
- 安全约定不变：凭据只存在于这台机器的 `.env` 里，不进仓库、不进聊天记录、不写进任何文档。

> **✅ 检查点 3**：`.env` 已创建，`QQ_APP_ID`/`QQ_APP_SECRET` 已填真实值，`TARGET_GROUP_OPENID` 留空。

---

## 4. 首次启动：机器人上线

在项目根目录、已激活虚拟环境的终端里执行：

```bash
python -m tipbot
```

正常的话，日志会依次出现（措辞略有出入属正常）：

```
[botpy] 登录机器人账号中...
[botpy] 机器人「你的机器人昵称」启动成功！
机器人「你的机器人昵称」已上线（WebSocket 出站连接，无需公网 IP/域名/Webhook）
尚未配置 TARGET_GROUP_OPENID：请在测试群 @ 机器人，把日志里醒目显示的 group_openid 填入 .env 后重启。
```

机器人从此保持在线，终端不要关。**停止机器人**：在该终端按 `Ctrl + C`。

> 日志除了打印在终端，还会写入项目根目录的 `botpy.log` 与 `tipbot.log`（按天轮转），事后可以翻查。

> **✅ 检查点 4**：日志出现"启动成功"与"已上线"，进程不退出、无报错。
>
> 卡住时：提示缺少配置 → 回到第 3 节检查 `.env`；登录报错（如 appid/secret 无效）→ 核对凭据是否抄错、AppSecret 是否已被重置（重置后旧值作废，见第一章第 4 节）。

---

## 5. 在测试群 @ 机器人，捕获 group_openid

1. 手机或电脑 QQ 打开**测试群**。
2. 发一条 **@ 机器人** 的消息，内容随意（例如 `@CS2KZ 小贴士助手 测试`）。
3. 回到运行机器人的终端，日志里会出现醒目的横幅：

   ```
   ==============================================================
   捕获到群标识 group_openid：XXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXX
   把上面这串值填入 .env 的 TARGET_GROUP_OPENID，重启机器人即可向该群发送 Tip。
   ==============================================================
   ```

4. **完整复制**那串 `group_openid`（区分大小写，不要截断）。

> `group_openid` 是平台为"每个机器人 × 每个群"分配的标识，**不是 QQ 群号**，每个群各不相同。机器人不会回复你的 @ 消息——这是设计如此，不是故障。

> **✅ 检查点 5**：日志横幅里出现了测试群的 `group_openid`，你已复制保存。
>
> @ 了却没捕获到：确认机器人程序正在运行、@ 的是机器人本人；仍不行则按第一章第 7 节把「机器人可获取的群聊消息范围」设为"获取群内全部消息"后重试。

---

## 6. 填配置、重启，测试群收到第一条 Tip

1. 停止机器人（终端按 `Ctrl + C`）。
2. 编辑 `.env`，把刚复制的值填进去并保存：

   ```ini
   TARGET_GROUP_OPENID=刚复制的group_openid
   ```

3. 重新启动：

   ```bash
   python -m tipbot
   ```

4. 日志出现：

   ```
   已向 Target Group 主动发送第一条 Tip：【示例】空中加速：……
   ```

5. **打开测试群**：一条纯文本 Tip 已经躺在群里，没有前缀、不是卡片，手机 QQ 直接可读。内容带【示例】标记——因为随附的 `tips.txt` 里是示例贴士（见第 7 节）。

> **✅ 检查点 6**：测试群**实际收到**机器人主动发来的纯文本 Tip。这是全项目最关键的一步：它证明个人主体机器人的群聊主动推送链路可用。
>
> 发送失败时日志会给出异常详情。最常见错误码 `40034105`（主动消息无权限）：回第一章第 7 节确认**群主**已开启「机器人主动在群聊内发言」，开启后重启机器人再试。

---

## 7. 验证之后：换上真实贴士

随附的 `tips.txt` 是示例 Tip List（4 条，均带【示例】标记）。正式使用前：

1. 用文本编辑器打开项目根目录的 `tips.txt`，把示例行**逐行替换**为你手写的 CS2KZ 贴士（一两句话一条）。
2. 格式规则：**一行一条 Tip**；空行与 `#` 开头的注释行会被忽略，可用来分组和备注。保存为 UTF-8。
3. 本章的机器人每次启动发送列表第一条；改完文件后重启即可看到新内容。定时轮播、洗牌、热加载在后续章节接入。

日后切换 Target Group（例如从测试群切到正式群）也是同一套动作：在目标群 @ 一次机器人 → 从日志抄新的 `group_openid` → 改 `.env` → 重启。机器人在其他群永远保持沉默。

---

## 8. 本章验收清单（人工检查点）

逐项确认，全部通过本章才算完成：

- [ ] 凭据与 `TARGET_GROUP_OPENID` 均从 `.env` 读取；`.env` 不在版本库中（`git status` 看不到它）
- [ ] 机器人经 WebSocket 出站保持在线，全程未用公网 IP/域名/Webhook
- [ ] 测试群 @ 机器人后，日志醒目输出该群 `group_openid`；机器人对任何消息都不回复
- [ ] 填入 `group_openid` 重启后，测试群实际收到一条纯文本 Tip（无前缀、主动推送）
- [ ] `tips.txt` 示例为 3–5 条标注【示例】的条目；空行与 `#` 注释行不影响读取
- [ ] 按本章命令在 Windows 或 Ubuntu 上成功跑通（另一平台可留待部署章验证）

全部勾选后，本票（`.scratch/tip-bot/issues/02-tracer-bullet-first-tip.md`）的人工检查点即告完成，后续章节接入 Send Window 与 Rotation。

---

## 9. 常见问题速查（运行环节）

| 症状 | 原因 | 处理 |
| --- | --- | --- |
| `python` 不是内部或外部命令 | 安装时未勾选 Add to PATH | 重装勾选，或重开终端；Ubuntu 用 `python3` |
| PowerShell 提示禁止运行脚本 | 执行策略限制 | 改用 cmd，或 `.venv\Scripts\Activate.ps1` 前按提示放开当前用户策略 |
| 启动即退出：缺少配置 | `.env` 不存在或凭据为空 | 第 3 节：复制 `.env.example` 为 `.env` 并填值；确认在项目根目录运行 |
| 登录报错 / 鉴权失败 | AppID/AppSecret 抄错或 Secret 已重置 | 核对凭据；重置过的 Secret 用新值（第一章第 4 节） |
| @ 机器人后日志无捕获 | 程序没在运行 / @ 错对象 / 消息范围受限 | 确认进程在线；按第一章第 7 节调「机器人可获取的群聊消息范围」 |
| 发送报错 `40034105` | 群未开主动发言权限 | 群主开启「机器人主动在群聊内发言」（第一章第 7 节），重启再试 |
| 日志警告 Tip List 为空或文件缺失 | `tips.txt` 被删/清空/不在运行目录 | 在项目根目录运行；恢复 `tips.txt`（一行一条） |
| 群里收到的是旧内容 | 本章每次启动只发列表第一条 | 改 `tips.txt` 后重启；热加载与轮播见后续章节 |
| 机器人"不说话"也不报错 | `TARGET_GROUP_OPENID` 仍为空 | 第 5–6 节：@ 捕获 → 填配置 → 重启 |
| 担心断网/断电 | 本章为手动运行的验证形态 | 正常现象；开机自启与崩溃拉起在部署章（systemd）接入 |

求助渠道与平台频控背景见第一章第 10 节。本项目每天最多 30 条 Tip，远低于平台上限（个人认证 60 条/分钟、单群 20 条/分钟、单群 1000 条/天）。
