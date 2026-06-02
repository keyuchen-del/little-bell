# Contributing to 小铃铛

欢迎贡献！以下是最常见的贡献方式。

## 开发环境

```bash
git clone https://github.com/keyuchen-del/little-bell.git
cd little-bell
uv sync
uv run python -m little_bell --test  # 验证环境正常
```

## 添加新推送通道

在 `little_bell/notifier.py` 中新增一个类继承 `BaseNotifier`：

```python
class TelegramNotifier(BaseNotifier):
    def __init__(self, config):
        tg_conf = config.get("telegram", {})
        self._token = tg_conf.get("bot_token", "")
        self._chat_id = tg_conf.get("chat_id", "")

    @property
    def name(self):
        return "Telegram"

    @property
    def enabled(self):
        return bool(self._token and self._chat_id)

    def send(self, title: str, body: str) -> bool:
        # 实现推送逻辑
        ...
```

然后在 `NotifierManager.__init__` 的 `self._notifiers` 列表中注册即可。

## 添加新 Agent 适配器

小铃铛通过 HTTP 接收事件，新 Agent 只需要一个 hook 脚本调用：

```bash
curl -s http://127.0.0.1:6789/event \
  -H "Content-Type: application/json" \
  -d '{"agent":"agent-name","event":"stop","data":{"message":"..."}}'
```

具体步骤：
1. 在 `hooks/` 下新建脚本（如 `codex_hook.sh`）
2. 在 `install.py` 中添加对应的 hook 注入逻辑
3. 更新 README 中的 Agent 支持表

## 跨平台支持

当前仅支持 macOS。如需添加 Linux/Windows 支持：

- **菜单栏**: 替换 `rumps` 为跨平台方案（如 `pystray`）
- **桌面宠物**: 替换 `pet_cocoa.py` 为 Qt/GTK 实现
- **系统通知**: `MacOSNotifier` 中的 `osascript` 替换为 `notify-send` (Linux) 或 `toast` (Windows)

## 提交规范

Commit message 格式：

```
feat: 新功能描述
fix: 修复描述
docs: 文档更新
refactor: 重构
```

## Issue / PR

- 提 Issue 前请先搜索是否已有相关讨论
- PR 请附带简要说明和测试方法
