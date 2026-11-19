# 02: 曳光弹——Target Group 收到第一条 Tip

**What to build:** 最窄但完整的端到端链路：机器人从 .env 读取凭据与配置，经官方 SDK（qq-botpy）WebSocket 出站上线；维护者在测试群 @ 机器人时，日志醒目输出该群的 group_openid；填入 .env 后，机器人向 Target Group 主动发出一条来自示例 Tip List 的纯文本 Tip。附示例 tips.txt 与最小运行说明。此票验证项目最大风险：个人主体机器人的群聊主动推送真的能发出来。

**Blocked by:** 01（手册·平台之路——需要凭据与已就位的测试群）

**Status:** ready-for-agent

- [ ] 凭据与 Target Group 的 group_openid 从 .env 读取；.env 不入版本库；提供占位符示例 .env
- [ ] 机器人经 WebSocket 出站连接保持在线，无需公网 IP/域名/Webhook
- [ ] 被 @ 时被动捕获并醒目记录该群 group_openid（日志即可，不自动改配置）；对任何消息绝不回复
- [ ] 配置 openid 后，机器人向 Target Group 主动发送一条纯文本 Tip（msg_type=0、无前缀、不带 msg_id），测试群实际收到
- [ ] 提供示例 Tip List：3–5 条明确标注为示例的条目，一行一条，空行与 # 注释行被忽略
- [ ] 最小运行说明（venv、安装依赖、启动）在 Windows 与 Ubuntu 上均可用
- [ ] 测试群实测通过：@ → 日志见 openid → 填配置 → Tip 到账（人工检查点）
