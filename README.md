<div align="center">

# 🔔 小铃铛 Little Bell

**AI Agent 停下来等你的时候，你的手机会响。**

*Never miss when your AI coding agent needs you.*

[![Python](https://img.shields.io/badge/Python-3.12+-3776AB?logo=python&logoColor=white)](https://python.org)
[![macOS](https://img.shields.io/badge/macOS-Sonoma+-000000?logo=apple&logoColor=white)](https://apple.com/macos)
[![License](https://img.shields.io/github/license/keyuchen-del/little-bell)](LICENSE)
[![Last Commit](https://img.shields.io/github/last-commit/keyuchen-del/little-bell?logo=git&logoColor=white)](https://github.com/keyuchen-del/little-bell/commits)

</div>

---

## 🎯 这是什么

你一定经历过这个场景：

> 让 Claude Code 跑一个重构任务，去倒了杯咖啡。
> 回来一看 —— **它 10 分钟前就停了**，一直在等你点 "Allow"。

**10 分钟 × 一天 5 次 = 每天近 1 小时在等一个你不知道的等待。**

Claude Code、Cursor、Codex……所有 AI Agent 都有同一个问题：**需要人工介入时，没有任何方式主动通知你。**

小铃铛解决这个问题 —— **Agent 一停，你手机就响。**

---

## ✨ 功能一览

| 功能 | 说明 |
|------|------|
| 📱 多通道推送 | macOS 通知 (零配置) + Bark (iOS) + Webhook (飞书/钉钉/Slack/Discord) |
| 🎣 Claude Code Hook | 原生 Hook 事件接入，Stop / Notification 自动触发 |
| 🔔 菜单栏常驻 | 状态栏铃铛图标，有事件时变红 + 计数 |
| 🐾 桌面宠物 | 星星人风格浮窗宠物，收到通知跳起来 + 气泡消息 |
| ⏱ 智能防抖 | 同一会话 3 秒内不重复推送，不会轰炸你 |
| 🔌 通用 HTTP 接口 | 任何能发 curl 的工具都能接入 |

---

## 🚀 快速开始

### 前置条件

- macOS (Sonoma+)
- [uv](https://docs.astral.sh/uv/) (`brew install uv`)

### 安装 & 启动

```bash
git clone https://github.com/keyuchen-del/little-bell.git
cd little-bell
uv sync
uv run python -m little_bell
```

启动后你会看到：
- ✅ 菜单栏出现铃铛图标
- ✅ 桌面出现星星人小宠物
- ✅ 终端打印 `小铃铛启动完成! 等待 Agent 事件...`

### 验证通知

在另一个终端窗口执行：

```bash
curl -X POST http://127.0.0.1:6789/event \
  -H "Content-Type: application/json" \
  -d '{"agent":"claude-code","event":"stop","data":{"message":"重构完成，等你 review"}}'
```

你会看到 **macOS 系统通知弹出** + 宠物跳动 + 菜单栏变红。整个过程无需任何配置。

---

## 📱 配置推送通道

小铃铛支持三种推送方式，可叠加使用：

### 方式一：macOS 系统通知（默认开启，无需配置）

开箱即用。启动小铃铛后，所有 Agent 事件自动弹出 macOS 通知。

如需关闭：

```yaml
# config.yaml
macos_notification:
  enabled: false
```

### 方式二：Bark（推送到 iPhone）

适合离开电脑时接收通知。

**Step 1** — 在 App Store 搜索 [Bark](https://apps.apple.com/app/bark/id1403753865) 并下载

**Step 2** — 打开 Bark App，首页显示如下格式的 URL：

```
https://api.day.app/xxxxxxx/这里是推送内容
                    ↑↑↑↑↑↑↑
                 这就是你的 Device Key
```

**Step 3** — 创建配置文件并填入 Key：

```bash
cp config.example.yaml config.yaml
```

编辑 `config.yaml`：

```yaml
bark:
  server: "https://api.day.app"       # 官方服务器，自建则改为你的地址
  device_key: "你的DeviceKey"          # 从 Bark App 首页复制
```

**Step 4** — 重启小铃铛，终端会显示 `推送通道: macOS, Bark`

### 方式三：Webhook（飞书 / 钉钉 / Slack / Discord / 企业微信）

适合团队使用或不用 iOS 的场景。

**飞书机器人：**

```yaml
webhook:
  url: "https://open.feishu.cn/open-apis/bot/v2/hook/你的token"
  body_template: '{"msg_type":"text","content":{"text":"{{title}}: {{body}}"}}'
```

**钉钉机器人：**

```yaml
webhook:
  url: "https://oapi.dingtalk.com/robot/send?access_token=你的token"
  body_template: '{"msgtype":"text","text":{"content":"{{title}}: {{body}}"}}'
```

**Slack Incoming Webhook：**

```yaml
webhook:
  url: "https://hooks.slack.com/services/T.../B.../xxx"
  body_template: '{"text":"*{{title}}*\n{{body}}"}'
```

**Discord Webhook：**

```yaml
webhook:
  url: "https://discord.com/api/webhooks/你的ID/你的token"
  body_template: '{"content":"**{{title}}**\n{{body}}"}'
```

> `{{title}}` 和 `{{body}}` 会被自动替换为事件标题和内容。

---

## 🔗 接入 Claude Code

一键注入 Hook，之后 Claude Code 每次停下等你都会自动推送：

```bash
uv run python install.py
```

脚本会：
1. 备份你的 `~/.claude/settings.json`
2. 注入 `Stop` 和 `Notification` 事件 hook
3. 引导你配置 Bark（可跳过）

**验证**：启动小铃铛，在 Claude Code 中执行任意任务，当它完成一轮对话或请求权限时，你会收到通知。

---

## 🔌 接入其他 Agent / 自定义工具

小铃铛通过 HTTP 接口接收事件。任何能发 HTTP 请求的脚本/工具都能接入：

```bash
curl -X POST http://127.0.0.1:6789/event \
  -H "Content-Type: application/json" \
  -d '{"agent":"你的agent名","event":"stop","data":{"message":"描述信息"}}'
```

**event 类型说明：**

| event | 含义 | 推送标题 |
|-------|------|----------|
| `stop` | Agent 完成一轮，等待用户输入 | "Agent 等你继续" |
| `notification` | Agent 主动通知 | "Agent 通知" |
| `permission_request` | Agent 需要用户批准操作 | "需要你批准操作!" |

**示例：在 shell 脚本中接入**

```bash
#!/bin/bash
# 在你的 CI/CD 或自动化脚本末尾加一行
curl -s http://127.0.0.1:6789/event \
  -H "Content-Type: application/json" \
  -d "{\"agent\":\"my-script\",\"event\":\"stop\",\"data\":{\"message\":\"$1\"}}" \
  >/dev/null 2>&1 || true
```

---

## ⚙️ 完整配置参考

```bash
cp config.example.yaml config.yaml
```

<details>
<summary>📖 config.example.yaml 完整内容（点击展开）</summary>

```yaml
# --- macOS 系统通知 (默认开启，零配置) ---
macos_notification:
  enabled: true

# --- Bark (iOS 推送) ---
bark:
  server: "https://api.day.app"
  device_key: ""  # 填入你的 Bark Device Key

# --- 通用 Webhook ---
webhook:
  url: ""
  method: "POST"
  headers:
    Content-Type: "application/json"
  body_template: ""  # 留空使用默认 JSON

# --- 推送行为 ---
notification:
  debounce_seconds: 3           # 防抖间隔
  notify_on_stop: true          # Agent 完成时推送
  notify_on_notification: true  # Agent 通知时推送

# --- 桌面宠物 ---
pet:
  enabled: true
  position_x: 100
  position_y: 100
  size: 80

# --- 本地服务 ---
server:
  host: "127.0.0.1"
  port: 6789
```

</details>

---

## 🗺 支持矩阵 & Roadmap

### Agent 支持

| Agent | 接入方式 | 状态 |
|-------|---------|------|
| **Claude Code** | 原生 Hook | ✅ 已支持 |
| Codex CLI | Terminal 模式匹配 | 🚧 开发中 |
| Cursor | Accessibility API | 📋 规划中 |
| 任意工具 | HTTP API | ✅ 已支持 |

### Roadmap

- [ ] Codex CLI / Cursor 自动检测
- [ ] Telegram Bot 通道
- [ ] 通知历史 Web Dashboard
- [ ] 手机端快捷回复（Bark URL Scheme）
- [ ] py2app 打包为 .app 独立应用
- [ ] Linux 支持 (libnotify + gotify)

---

## 🛠 技术栈

| 组件 | 技术 |
|------|------|
| 菜单栏 | rumps (PyObjC) |
| 桌面宠物 | PyObjC 原生 NSWindow |
| 本地服务 | Flask |
| 推送 | Bark API / Webhook / osascript |
| 精灵图 | Pillow 程序化生成 |
| 包管理 | uv |

---

## 🤝 Contributing

欢迎 PR！特别欢迎：

- 🔌 新 Agent 接入适配器（Codex / Cursor / Copilot）
- 📡 新推送通道（Telegram / Gotify / Pushover）
- 🖥 跨平台支持（Linux / Windows）
- 🎨 新宠物形象 / 动画

## 📄 License

[MIT](./LICENSE) © [keyuchen-del](https://github.com/keyuchen-del)
