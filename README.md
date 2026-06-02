<p align="center">
  <h1 align="center">小铃铛 Little Bell</h1>
  <p align="center"><strong>AI Agent 停下来等你的时候，你的手机会响。</strong></p>
  <p align="center">
    <em>Never miss when your AI coding agent needs you.</em>
  </p>
</p>

<p align="center">
  <a href="#30-秒体验">30 秒体验</a> •
  <a href="#为什么需要">为什么需要</a> •
  <a href="#支持的-agent">支持的 Agent</a> •
  <a href="#推送通道">推送通道</a> •
  <a href="#配置">配置</a>
</p>

---

## 为什么需要

你一定经历过这个场景：

> 让 Claude Code 跑一个大任务，去倒杯水、上个厕所、回个消息。
>
> 回来一看 —— **它 10 分钟前就停了**，一直在等你点 "Allow"。
>
> 10 分钟 × 一天 5 次 = **每天近 1 小时在等一个你不知道的等待**。

Cursor、Codex、Claude Code……所有 AI Agent 都有同一个问题：**需要人工介入时，没有任何方式通知你**。

**小铃铛**解决这个问题：Agent 一停，你手机就响。

---

## 它怎么工作

```
Claude Code / Codex / Cursor (Agent 停下等你)
         ↓ Hook 事件触发
      curl → 本地 Flask (:6789)
         ↓
   ┌──────┼──────────┐
   │      │          │
 手机推送  菜单栏    桌面宠物
(Bark等)  图标变红  跳起来提醒你
```

- **Claude Code**: 利用原生 Hook 机制，Stop / Notification 事件自动触发
- **零侵入**: 不修改任何 Agent 代码，不需要 root 权限
- **多通道推送**: macOS 通知 (零配置) + Bark (iOS) + Webhook (飞书/钉钉/Slack)
- **防抖**: 3 秒内同一会话不重复推送，不会轰炸你

---

## 30 秒体验

**无需任何配置**，clone 后即可看到 macOS 系统通知效果：

```bash
git clone https://github.com/keyuchen-del/little-bell.git
cd little-bell
uv sync                        # 安装依赖 (需要 uv: brew install uv)
uv run python -m little_bell   # 启动！菜单栏出现铃铛 + 桌面出现小宠物
```

然后在另一个终端模拟一个 Agent 事件：

```bash
curl -X POST http://127.0.0.1:6789/event \
  -H "Content-Type: application/json" \
  -d '{"agent":"claude-code","event":"stop","data":{"message":"重构完成，等你 review"}}'
```

你会看到：
1. macOS 右上角弹出系统通知
2. 菜单栏铃铛变红
3. 桌面小宠物跳起来 + 气泡消息

---

## 接入 Claude Code (一键)

```bash
uv run python install.py
```

这会自动向 `~/.claude/settings.json` 注入 hook。之后每次 Claude Code 停下来等你，你都会收到通知。

---

## 推送通道

| 通道 | 平台 | 配置 | 说明 |
|------|------|------|------|
| **macOS 通知** | macOS | 零配置 ✅ | 默认开启，开箱即用 |
| **Bark** | iOS | 填 Device Key | App Store 搜 "Bark" 下载 |
| **Webhook** | 任意 | 填 URL | 飞书/钉钉/Slack/Discord/企业微信 |

### 配置 Bark (推送到 iPhone)

1. App Store 下载 [Bark](https://apps.apple.com/app/bark/id1403753865)
2. 打开 App，首页显示 `https://api.day.app/YOUR_KEY/...`
3. 把 `YOUR_KEY` 填入 `config.yaml`:

```yaml
bark:
  device_key: "YOUR_KEY"
```

### 配置 Webhook (飞书/钉钉/Slack)

```yaml
webhook:
  url: "https://open.feishu.cn/open-apis/bot/v2/hook/your-token"
  body_template: '{"msg_type":"text","content":{"text":"{{title}}: {{body}}"}}'
```

---

## 支持的 Agent

| Agent | 接入方式 | 状态 |
|-------|---------|------|
| **Claude Code** | 原生 Hook (Stop/Notification) | ✅ 已支持 |
| Codex CLI | Terminal 模式匹配 | 🚧 开发中 |
| Cursor | Accessibility API | 🚧 规划中 |
| 通用终端 | 关键词轮询 | 🚧 规划中 |

### 扩展新 Agent

小铃铛通过 HTTP 接口接收事件，任何能发 HTTP 请求的工具都能接入：

```bash
# 在你的脚本/hook 里加一行
curl -s http://127.0.0.1:6789/event \
  -H "Content-Type: application/json" \
  -d '{"agent":"your-agent","event":"stop","data":{"message":"等你操作"}}'
```

---

## 配置参考

```bash
cp config.example.yaml config.yaml
```

完整配置见 [config.example.yaml](./config.example.yaml)。

---

## 技术栈

- Python 3.12+ / uv
- rumps (macOS 菜单栏)
- PyObjC (桌面浮窗宠物)
- Flask (本地事件 HTTP Server)
- Bark API / Webhook (远程推送)

## Roadmap

- [ ] Codex CLI / Cursor 监听
- [ ] Telegram Bot 通道
- [ ] 通知历史 Dashboard
- [ ] 手机端快捷回复 (Bark URL Scheme)
- [ ] py2app 打包为 .app
- [ ] Linux 支持 (libnotify)

## Contributing

欢迎 PR！特别欢迎：
- 新 Agent 接入适配器
- 新推送通道
- Linux/Windows 平台支持

## License

[MIT](./LICENSE)
