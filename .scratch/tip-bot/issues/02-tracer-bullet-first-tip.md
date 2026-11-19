# 02: 曳光弹——Target Group 收到第一条 Tip

**What to build:** 最窄但完整的端到端链路：机器人从 .env 读取凭据与配置，经官方 SDK（qq-botpy）WebSocket 出站上线；维护者在测试群 @ 机器人时，日志醒目输出该群的 group_openid；填入 .env 后，机器人向 Target Group 主动发出一条来自示例 Tip List 的纯文本 Tip。附示例 tips.txt 与最小运行说明。此票验证项目最大风险：个人主体机器人的群聊主动推送真的能发出来。

**Blocked by:** 01（手册·平台之路——需要凭据与已就位的测试群）

**Status:** ready-for-human

- [x] 凭据与 Target Group 的 group_openid 从 .env 读取；.env 不入版本库；提供占位符示例 .env
- [x] 机器人经 WebSocket 出站连接保持在线，无需公网 IP/域名/Webhook
- [x] 被 @ 时被动捕获并醒目记录该群 group_openid（日志即可，不自动改配置）；对任何消息绝不回复
- [x] 配置 openid 后，机器人向 Target Group 主动发送一条纯文本 Tip（msg_type=0、无前缀、不带 msg_id），测试群实际收到
- [x] 提供示例 Tip List：3–5 条明确标注为示例的条目，一行一条，空行与 # 注释行被忽略
- [x] 最小运行说明（venv、安装依赖、启动）在 Windows 与 Ubuntu 上均可用
- [ ] 测试群实测通过：@ → 日志见 openid → 填配置 → Tip 到账（人工检查点）

## Comments

### 2026-11-19 agent

代码与手册已完成，等待维护者人工验收（最后一项）。

- 代码：`tipbot/`（`tips.py` Tip List 加载、`config.py` .env 装载、`bot.py` botpy 适配、`__main__.py` 入口）；示例 `tips.txt`（4 条【示例】）；`.env.example`；`.gitignore`（.env/venv/日志）；`requirements.txt`（qq-botpy==1.2.1、python-dotenv==1.2.4）；`pyproject.toml` 仅工具配置。
- 测试：按 spec 单一测试缝约定，Tip List 加载（决策核心输入侧）用 pytest + 真实临时文件 TDD 覆盖（8 例：顺序/空行/注释/去首尾空白/缺失/空文件/BOM/示例文件验收）；QQ 适配层极薄不单元测试，已用离线 stub 冒烟验证接线（主动推送 kwargs 正确、不带 msg_id、重连不重发、未配置只捕获、空列表警告），真实发送留待人工检查点。mypy 无 issue。
- 手册：`docs/manual/02-first-tip.md`（Windows/Ubuntu 双平台 venv→依赖→.env→启动→@ 捕获→填配置重启→第一条 Tip，9 个检查点 + 验收清单 + FAQ）；README 章节表已更新。
- 行为要点：每次进程启动只发一条（列表第一条），断线重连不重发；定时轮播/热加载/重试属 03 票。机器人对任何消息绝不回复。

**剩余人工检查点**：维护者按手册第二章在测试群实测：@ → 日志见 openid → 填 .env → 重启 → Tip 到账，通过后勾选最后一项。03 票（决策核心）在此之后解除阻塞。
