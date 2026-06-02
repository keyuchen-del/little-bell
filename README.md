# 小铃铛 (Little Bell) 🔔

> 当 AI Coding Agent 需要你操作时，推送通知到手机 — 再也不会错过等待。

## 痛点

使用 Claude Code / Cursor / Codex 等 AI Agent 编码时，agent 经常需要等待用户手动确认（权限批准、输入反馈、review 等）。如果你离开了电脑，这些等待会白白浪费时间。

**小铃铛**通过 Hook + 推送自动通知你的手机，确保执行不中断。

## 架构

```
Agent (Claude Code / Codex / Cursor)
       ↓ Hook 事件 (Stop / Notification / PermissionRequest)
    Shell 脚本 (curl → 本地服务)
       ↓
  Flask HTTP Server (:6789)
       ↓
  ┌─────────┬──────────────┐
  │         │              │
Bark推送  菜单栏图标   桌面浮窗宠物
 (手机)   (状态切换)  (动画提醒)
```

## 快速开始

### 1. 安装依赖

```bash
# 需要 uv (https://docs.astral.sh/uv/)
cd little-bell
uv sync
```

### 2. 配置

```bash
cp config.example.yaml config.yaml
# 编辑 config.yaml，填入你的 Bark Device Key
```

在 iOS App Store 下载 [Bark](https://apps.apple.com/app/bark/id1403753865)，打开后首页显示的 URL 中 `https://api.day.app/YOUR_KEY/...` 的 `YOUR_KEY` 部分即为 Device Key。

### 3. 注入 Claude Code Hook

```bash
uv run python install.py
```

自动向 `~/.claude/settings.json` 注入 Stop / Notification 事件 hook。

### 4. 启动

```bash
uv run python -m little_bell
```

菜单栏出现铃铛图标，桌面出现星星人宠物。当 Agent 停下等你时，手机会收到推送。

## 手动测试

```bash
# 模拟一个 Agent 事件
curl -X POST http://127.0.0.1:6789/event \
  -H "Content-Type: application/json" \
  -d '{"agent":"claude-code","event":"stop","data":{"message":"Build 完成，等你确认部署"}}'
```

## 支持的 Agent

| Agent | 接入方式 | 状态 |
|-------|---------|------|
| Claude Code | Hook (Stop/Notification) | ✅ 已支持 |
| OpenAI Codex CLI | Terminal 模式匹配 | 🚧 规划中 |
| Cursor | Accessibility API | 🚧 规划中 |
| 通用终端 | 关键词轮询 | 🚧 规划中 |

## 推送通道

| 通道 | 平台 | 状态 |
|------|------|------|
| Bark | iOS | ✅ 已支持 |
| Server酱 | 微信 | 🚧 规划中 |
| 钉钉/飞书 Webhook | 企业IM | 🚧 规划中 |
| Telegram Bot | 跨平台 | 🚧 规划中 |

## 项目结构

```
little_bell/
├── app.py          # 主入口 (menubar + server + pet)
├── server.py       # 本地 HTTP 事件接收
├── notifier.py     # Bark 推送 + 防抖
├── menubar.py      # macOS 菜单栏 (rumps)
├── pet_cocoa.py    # 桌面浮窗宠物 (PyObjC)
├── gen_assets.py   # 生成宠物精灵图
└── config.py       # 配置管理
hooks/
└── claude_code_hook.sh  # Claude Code hook 脚本
```

## 技术栈

- Python 3.12+
- rumps (macOS 菜单栏)
- PyObjC (原生浮窗)
- Flask (本地 HTTP)
- Pillow (精灵图生成)
- Bark API (iOS 推送)

## License

MIT
