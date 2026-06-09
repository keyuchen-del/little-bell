<p align="center">
  <img src="little_bell/assets/bell.png" width="80" alt="Little Bell">
</p>

<h1 align="center">小铃铛 Little Bell</h1>

<p align="center">
  <strong>AI Agent 停下来时，你的手机会响 —— 还能远程批准或拒绝。</strong><br/>
  <sub>The only Agent notification tool that lets you approve permissions from your phone.</sub>
</p>

<p align="center">
  <a href="https://github.com/Jackychen-12/little-bell/stargazers"><img src="https://img.shields.io/github/stars/Jackychen-12/little-bell?style=flat&logo=github&color=yellow" alt="Stars"></a>
  <img src="https://img.shields.io/badge/Python-3.12+-3776AB?logo=python&logoColor=white" alt="Python">
  <img src="https://img.shields.io/badge/macOS-Sonoma+-000000?logo=apple&logoColor=white" alt="macOS">
  <a href="LICENSE"><img src="https://img.shields.io/github/license/Jackychen-12/little-bell" alt="License"></a>
  <a href="https://github.com/Jackychen-12/little-bell/commits"><img src="https://img.shields.io/github/last-commit/Jackychen-12/little-bell?logo=git&logoColor=white" alt="Last Commit"></a>
</p>

---

> 让 Claude Code 跑一个重构任务，去倒了杯咖啡。回来一看 —— **它 10 分钟前就停了**，一直在等你点 "Allow"。
>
> **10 分钟 x 一天 5 次 = 每天近 1 小时在等一个你不知道的等待。**

小铃铛解决这个问题 —— Agent 一停，你手机就响；需要权限时，**手机上直接批准或拒绝，不用跑回电脑**。

---

## 为什么选小铃铛

桌面宠物类工具（如 [Clawd on Desk](https://github.com/rullerzhou-afk/clawd-on-desk)）在**人坐在电脑前时**很好用。但真正痛的场景是 —— **你不在电脑前**。

| 能力 | 桌面宠物类工具 | 小铃铛 |
|------|:---:|:---:|
| 桌面通知 | ✅ | ✅ |
| 桌面宠物动画 | ✅ 丰富 | ✅ 基础 |
| 桌面权限气泡 | ✅ | - |
| **手机推送通知** | - | **✅ Bark / Webhook** |
| **手机远程批准/拒绝** | - | **✅ 操作页面** |
| **规则引擎自动放行** | - | **✅ auto_allow / auto_deny** |
| **快捷回复发回 Agent** | - | **✅ 手机端文字回复** |
| **飞书/钉钉/Slack 推送** | - | **✅ Webhook** |
| **决策审计历史** | - | **✅ /history API** |
| 零依赖安装 | 需要 Electron | **uv sync 即用** |

**一句话总结：桌面宠物是给"在座位上"的你准备的，小铃铛是给"去倒咖啡"的你准备的。**

---

## 核心功能

### 📲 手机远程批准/拒绝

这是小铃铛独有的核心能力。当 Claude Code 请求权限（执行命令、编辑文件），你不需要跑回电脑：

```
Claude Code: "Bash: npm install"  需要你批准
     ↓
小铃铛 /permission 端点接收，阻塞等待
     ↓
Bark 推送到你的 iPhone，附带操作链接
     ↓
你点击通知 → 打开手机端操作页面
看到: [Bash] npm install
      [批准]  [拒绝]  [💬 快捷回复...]
     ↓
点击批准 → Claude Code 继续执行
```

手机端操作页面提供：

- **富上下文** — Bash 显示完整命令，Edit 显示文件路径 + diff 预览，Write 显示内容预览
- **批准/拒绝** — 一键操作
- **快捷回复** — 输入文字发回给 Agent（如 "换个方案"）
- **5 分钟超时** — 超时自动拒绝，不会永远阻塞

### 🛡️ 规则引擎

不想每次 `git status` 都掏手机？配置规则自动处理：

```yaml
rules:
  auto_allow:
    - "Read"              # 所有读文件自动批准
    - "Bash:ls *"         # ls 命令自动批准
    - "Bash:git status"   # git status 自动批准
    - "Bash:git diff*"    # git diff 相关自动批准
  auto_deny:
    - "Bash:rm -rf /*"    # 根目录删除永远拒绝
    - "Bash:sudo *"       # sudo 永远拒绝
```

匹配规则的操作被自动处理，不匹配的才推送到手机。每条决策都写入审计日志（`/history` API）。

### 📱 多通道推送

三种方式可叠加使用：

| 通道 | 场景 | 配置难度 |
|------|------|:---:|
| **macOS 通知** | 坐在电脑前 | 零配置 |
| **Bark (iOS)** | 离开电脑 + 远程批准 | 30 秒 |
| **Webhook** | 团队通知 / 飞书 / 钉钉 / Slack / Discord | 1 分钟 |

### 🐾 桌面宠物 + 菜单栏

- 星星人风格浮窗宠物，收到通知跳起来 + 气泡消息
- 菜单栏铃铛图标常驻，有事件时变红 + 计数
- 智能防抖，同一会话 3 秒内不重复推送

---

## 快速开始

```bash
git clone https://github.com/Jackychen-12/little-bell.git
cd little-bell
uv sync
uv run python -m little_bell
```

启动后：✅ 菜单栏出现铃铛 → ✅ 桌面出现宠物 → ✅ 终端打印 `小铃铛启动完成!`

### 验证通知

```bash
curl -X POST http://127.0.0.1:6789/event \
  -H "Content-Type: application/json" \
  -d '{"agent":"claude-code","event":"stop","data":{"message":"重构完成，等你 review"}}'
```

### 接入 Claude Code

```bash
uv run python install.py
```

脚本会自动：备份 `~/.claude/settings.json` → 注入 Stop / Notification / PermissionRequest hooks → 引导配置 Bark。

---

## 配置推送通道

### Bark（推送到 iPhone + 远程批准）

```bash
cp config.example.yaml config.yaml
```

1. App Store 下载 [Bark](https://apps.apple.com/app/bark/id1403753865)
2. 打开 Bark，复制首页的 Device Key
3. 编辑 `config.yaml`：

```yaml
bark:
  server: "https://api.day.app"
  device_key: "你的DeviceKey"
```

### Webhook（飞书 / 钉钉 / Slack / Discord）

<details>
<summary>点击展开各平台配置示例</summary>

**飞书：**
```yaml
webhook:
  url: "https://open.feishu.cn/open-apis/bot/v2/hook/你的token"
  body_template: '{"msg_type":"text","content":{"text":"{{title}}: {{body}}"}}'
```

**钉钉：**
```yaml
webhook:
  url: "https://oapi.dingtalk.com/robot/send?access_token=你的token"
  body_template: '{"msgtype":"text","text":{"content":"{{title}}: {{body}}"}}'
```

**Slack：**
```yaml
webhook:
  url: "https://hooks.slack.com/services/T.../B.../xxx"
  body_template: '{"text":"*{{title}}*\n{{body}}"}'
```

**Discord：**
```yaml
webhook:
  url: "https://discord.com/api/webhooks/你的ID/你的token"
  body_template: '{"content":"**{{title}}**\n{{body}}"}'
```

</details>

---

## 接入其他 Agent

小铃铛通过 HTTP 接口接收事件。任何能发 curl 的工具都能接入：

```bash
curl -X POST http://127.0.0.1:6789/event \
  -H "Content-Type: application/json" \
  -d '{"agent":"你的agent名","event":"stop","data":{"message":"描述信息"}}'
```

| event | 含义 | 推送标题 |
|-------|------|----------|
| `stop` | Agent 完成一轮 | "Agent 等你继续" |
| `notification` | Agent 主动通知 | "Agent 通知" |
| `permission_request` | 需要用户批准 | "需要你批准操作!" |

---

## Agent 支持矩阵

| Agent | 接入方式 | 通知 | 远程批准 | 状态 |
|-------|---------|:---:|:---:|------|
| **Claude Code** | 原生 Hook (Stop + Notification + PermissionRequest) | ✅ | ✅ | 已支持 |
| **任意工具** | HTTP API (`/event` + `/permission`) | ✅ | ✅ | 已支持 |
| Codex CLI | Terminal 模式匹配 | 🚧 | 🚧 | 开发中 |
| Cursor | Accessibility API | 📋 | 📋 | 规划中 |

---

## 技术栈

| 组件 | 技术 |
|------|------|
| 菜单栏 | rumps (PyObjC) |
| 桌面宠物 | PyObjC 原生 NSWindow |
| 本地服务 | Flask (线程模式) |
| 推送 | Bark API / Webhook / osascript |
| 精灵图 | Pillow 程序化生成 |
| 包管理 | uv |

<details>
<summary>完整配置参考 (config.example.yaml)</summary>

```yaml
macos_notification:
  enabled: true

bark:
  server: "https://api.day.app"
  device_key: ""

webhook:
  url: ""
  method: "POST"
  headers:
    Content-Type: "application/json"
  body_template: ""

rules:
  auto_allow:
    - "Read"
    - "Bash:ls *"
    - "Bash:git status"
    - "Bash:git diff*"
  auto_deny:
    - "Bash:rm -rf /*"
    - "Bash:sudo *"

notification:
  debounce_seconds: 3
  notify_on_stop: true
  notify_on_notification: true

pet:
  enabled: true
  position_x: 100
  position_y: 100
  size: 80

server:
  host: "127.0.0.1"
  port: 6789
```

</details>

---

## Roadmap

- [x] 手机远程批准/拒绝 (Bark + 操作页面)
- [x] 规则引擎 (auto_allow / auto_deny)
- [x] 多通道推送 (macOS + Bark + Webhook)
- [x] 决策审计历史
- [ ] Codex CLI / Cursor 自动检测
- [ ] Telegram Bot 通道
- [ ] 通知历史 Web Dashboard
- [ ] py2app 打包为 .app 独立应用
- [ ] Linux 支持 (libnotify + gotify)

---

## Contributing

欢迎 PR！特别欢迎：

- 🔌 新 Agent 接入适配器（Codex / Cursor / Copilot / Gemini）
- 📡 新推送通道（Telegram / Gotify / Pushover）
- 🖥 跨平台支持（Linux / Windows）
- 🎨 新宠物形象 / 动画

## License

[MIT](./LICENSE) © [Jackychen-12](https://github.com/Jackychen-12)
