# CS2KZ QQ 小贴士机器人操作手册

面向零部署经验的维护者，从"什么都没有"到"正式 Target Group 按节奏收到 Tip"的全程操作手册。按章节顺序阅读、照做即可；每章的关键步骤都带验证检查点，确认通过再往下走。

术语以仓库根目录 `CONTEXT.md` 为准（Tip、Tip List、Send Window、Rotation、Target Group）。

**安全约定**：AppID/AppSecret 等凭据只保存在你私人的安全位置与服务器 `.env` 中，**永远不写入本手册、聊天记录或代码仓库**。

## 章节

| 章节 | 内容 | 状态 |
| --- | --- | --- |
| [第一章 平台之路](01-platform-setup.md) | 开放平台注册与个人实名、创建机器人、AppID/AppSecret、自建测试群、拉机器人入群、开启「机器人主动在群聊内发言」 | ✅ 可用 |
| [第二章 第一条 Tip](02-first-tip.md) | 运行机器人（Windows/Ubuntu）、@ 捕获 group_openid、测试群收到第一条 Tip；定时轮播、热加载与失败重试已接入 | ✅ 可用 |
| 后续章节 | Ubuntu 服务器部署、切换正式 Target Group、日常运维、排错对照表 | 计划中（见 `.scratch/tip-bot/issues/04-deploy-and-go-live.md`） |