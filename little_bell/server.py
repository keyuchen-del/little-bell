import json
import uuid
import socket
import logging
import threading
from datetime import datetime
from flask import Flask, request, jsonify, Response
from collections import deque

logger = logging.getLogger("little-bell")

app = Flask(__name__)

event_history = deque(maxlen=50)
decision_history = deque(maxlen=200)
notifier = None
ui_callback = None
rule_engine = None

# Pending permission actions: {action_id: {event, tool, params, decision, decided_event}}
pending_actions = {}
pending_lock = threading.Lock()


def get_lan_ip():
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
        s.close()
        return ip
    except Exception:
        return "127.0.0.1"


def init_server(bark_notifier, on_event_callback=None, rules=None):
    global notifier, ui_callback, rule_engine
    notifier = bark_notifier
    ui_callback = on_event_callback
    rule_engine = rules


@app.route("/event", methods=["POST"])
def receive_event():
    try:
        payload = request.get_json(force=True)
    except Exception:
        return jsonify({"error": "invalid json"}), 400

    agent = payload.get("agent", "unknown")
    event_type = payload.get("event", "unknown")
    data = payload.get("data", {})
    session_id = data.get("session_id") if isinstance(data, dict) else None

    detail = None
    if isinstance(data, dict):
        detail = data.get("message") or data.get("notification") or data.get("detail")

    event_record = {
        "agent": agent,
        "event": event_type,
        "detail": detail,
        "session_id": session_id,
        "timestamp": datetime.now().isoformat(),
    }
    event_history.appendleft(event_record)
    logger.info(f"[{agent}] {event_type}: {detail or '(no detail)'}")

    if notifier:
        notifier.send_async(event_type, detail=detail, session_id=session_id)
    if ui_callback:
        ui_callback(event_record)

    return jsonify({"ok": True})


# ============================================================
# Permission Request — 手机远程批准/拒绝
# ============================================================

@app.route("/permission", methods=["POST"])
def handle_permission():
    """Claude Code PermissionRequest HTTP hook 端点。
    阻塞直到用户在手机上做出决定，或超时。
    """
    try:
        payload = request.get_json(force=True) or {}
    except Exception:
        payload = {}

    tool_name = payload.get("tool", payload.get("toolName", "unknown"))
    tool_input = payload.get("input", payload.get("toolInput", {}))
    session_id = payload.get("session_id", "")

    # Summarize what's being requested
    if isinstance(tool_input, dict):
        summary = tool_input.get("command", "") or tool_input.get("file_path", "") or json.dumps(tool_input, ensure_ascii=False)[:200]
    else:
        summary = str(tool_input)[:200]

    # Rule engine: auto-decide if matching
    if rule_engine:
        auto_decision = rule_engine.evaluate(tool_name, tool_input)
        if auto_decision:
            decision_history.appendleft({
                "tool": tool_name, "summary": summary[:100],
                "decision": auto_decision, "source": "rule",
                "timestamp": datetime.now().isoformat(),
            })
            return jsonify({"decision": auto_decision})

    action_id = uuid.uuid4().hex[:12]
    decided_event = threading.Event()

    action = {
        "id": action_id,
        "tool": tool_name,
        "summary": summary,
        "full_input": tool_input,
        "session_id": session_id,
        "decision": None,
        "decided_event": decided_event,
        "timestamp": datetime.now().isoformat(),
    }

    with pending_lock:
        pending_actions[action_id] = action

    logger.info(f"[Permission] {tool_name}: {summary[:60]}... (waiting for decision)")

    # Push notification with action URL
    lan_ip = get_lan_ip()
    port = request.host.split(":")[-1] if ":" in request.host else "6789"
    action_url = f"http://{lan_ip}:{port}/action/{action_id}"

    if notifier:
        notifier.send_permission(
            tool_name=tool_name,
            summary=summary,
            action_url=action_url,
            session_id=session_id,
        )

    if ui_callback:
        ui_callback({
            "agent": "claude-code",
            "event": "permission_request",
            "detail": f"[等待批准] {tool_name}: {summary[:50]}",
            "session_id": session_id,
            "timestamp": datetime.now().isoformat(),
        })

    # Block until user decides or timeout (5 min)
    decided_event.wait(timeout=300)

    decision = action.get("decision", "deny")
    reply_msg = action.get("reply_message")

    with pending_lock:
        pending_actions.pop(action_id, None)

    decision_history.appendleft({
        "tool": tool_name, "summary": summary[:100],
        "decision": decision, "source": "user",
        "reply": reply_msg,
        "timestamp": datetime.now().isoformat(),
    })

    logger.info(f"[Permission] {tool_name} → {decision}" + (f" (reply: {reply_msg})" if reply_msg else ""))

    if decision == "allow":
        return jsonify({"decision": "allow"})
    else:
        return jsonify({"decision": "deny", "reason": "User denied from mobile"})


@app.route("/action/<action_id>", methods=["GET"])
def action_page(action_id):
    """手机端操作页面 — 显示批准/拒绝按钮 + 富上下文 + 快捷回复。"""
    with pending_lock:
        action = pending_actions.get(action_id)

    if not action:
        return Response(ACTION_PAGE_EXPIRED, content_type="text/html; charset=utf-8")

    # Build rich context based on tool type
    tool = action["tool"]
    full_input = action.get("full_input", {})
    context_html = _build_context_html(tool, full_input)

    html = ACTION_PAGE_TEMPLATE.format(
        action_id=action_id,
        tool=tool,
        context=context_html,
        summary=action["summary"][:500],
        timestamp=action["timestamp"],
    )
    return Response(html, content_type="text/html; charset=utf-8")


def _build_context_html(tool, tool_input):
    """根据工具类型生成富上下文 HTML。"""
    if not isinstance(tool_input, dict):
        return f"<pre>{str(tool_input)[:500]}</pre>"

    if tool == "Bash":
        cmd = tool_input.get("command", "")
        desc = tool_input.get("description", "")
        html = f'<div class="ctx-label">命令</div><pre class="ctx-code">{cmd}</pre>'
        if desc:
            html += f'<div class="ctx-desc">{desc}</div>'
        return html

    elif tool == "Edit":
        fp = tool_input.get("file_path", "")
        old = tool_input.get("old_string", "")[:200]
        new = tool_input.get("new_string", "")[:200]
        html = f'<div class="ctx-label">文件</div><pre class="ctx-code">{fp}</pre>'
        if old:
            html += f'<div class="ctx-label">替换</div><pre class="ctx-diff ctx-del">{old}</pre>'
        if new:
            html += f'<pre class="ctx-diff ctx-add">{new}</pre>'
        return html

    elif tool == "Write":
        fp = tool_input.get("file_path", "")
        content = tool_input.get("content", "")[:300]
        html = f'<div class="ctx-label">写入文件</div><pre class="ctx-code">{fp}</pre>'
        if content:
            html += f'<div class="ctx-label">内容预览</div><pre class="ctx-code">{content}...</pre>'
        return html

    elif tool == "Read":
        fp = tool_input.get("file_path", "")
        return f'<div class="ctx-label">读取文件</div><pre class="ctx-code">{fp}</pre>'

    else:
        import json as _json
        formatted = _json.dumps(tool_input, ensure_ascii=False, indent=2)[:500]
        return f'<div class="ctx-label">参数</div><pre class="ctx-code">{formatted}</pre>'


@app.route("/action/<action_id>/approve", methods=["POST", "GET"])
def action_approve(action_id):
    return _resolve_action(action_id, "allow")


@app.route("/action/<action_id>/deny", methods=["POST", "GET"])
def action_deny(action_id):
    return _resolve_action(action_id, "deny")


@app.route("/action/<action_id>/reply", methods=["POST"])
def action_reply(action_id):
    """快捷回复 — 用户输入文字发回 agent。"""
    message = request.form.get("message", "") or (request.get_json(force=True) or {}).get("message", "")
    with pending_lock:
        action = pending_actions.get(action_id)
    if not action:
        return Response(ACTION_PAGE_DONE.format(result="已过期"), content_type="text/html; charset=utf-8")

    action["decision"] = "allow"
    action["reply_message"] = message
    action["decided_event"].set()
    return Response(ACTION_PAGE_DONE.format(result=f"✅ 已回复: {message[:30]}"), content_type="text/html; charset=utf-8")


def _resolve_action(action_id, decision):
    with pending_lock:
        action = pending_actions.get(action_id)

    if not action:
        return Response(ACTION_PAGE_DONE.format(result="已过期或已处理"), content_type="text/html; charset=utf-8")

    action["decision"] = decision
    action["decided_event"].set()

    result_text = "✅ 已批准" if decision == "allow" else "❌ 已拒绝"
    return Response(ACTION_PAGE_DONE.format(result=result_text), content_type="text/html; charset=utf-8")


@app.route("/actions", methods=["GET"])
def list_actions():
    """列出所有待处理的 permission 请求。"""
    with pending_lock:
        items = [
            {"id": a["id"], "tool": a["tool"], "summary": a["summary"], "timestamp": a["timestamp"]}
            for a in pending_actions.values()
            if a["decision"] is None
        ]
    return jsonify({"pending": items})


@app.route("/history", methods=["GET"])
def history():
    """决策审计历史。"""
    return jsonify({"decisions": list(decision_history)})


# ============================================================
# Existing endpoints
# ============================================================

@app.route("/status", methods=["GET"])
def status():
    with pending_lock:
        pending_count = sum(1 for a in pending_actions.values() if a["decision"] is None)
    return jsonify({
        "running": True,
        "events_count": len(event_history),
        "pending_actions": pending_count,
        "recent_events": list(event_history)[:10],
    })


@app.route("/health", methods=["GET"])
def health():
    return jsonify({"status": "ok", "lan_ip": get_lan_ip()})


def check_port(host, port):
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        try:
            s.bind((host, port))
            return True
        except OSError:
            return False


def run_server(host="0.0.0.0", port=6789):
    logging.getLogger("werkzeug").setLevel(logging.WARNING)
    if not check_port(host, port):
        logger.error(
            f"端口 {port} 已被占用! 可能原因:\n"
            f"  1. 小铃铛已在运行 (用 lsof -ti:{port} | xargs kill 关闭)\n"
            f"  2. 其他程序占用了该端口 (用 --port 指定其他端口)"
        )
        return
    app.run(host=host, port=port, threaded=True)


# ============================================================
# HTML Templates (inline, mobile-optimized)
# ============================================================

ACTION_PAGE_TEMPLATE = """<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1, user-scalable=no">
<title>小铃铛 - 权限请求</title>
<style>
* {{ margin: 0; padding: 0; box-sizing: border-box; }}
body {{ font-family: -apple-system, BlinkMacSystemFont, sans-serif; background: #0f0f1a; color: #eee; min-height: 100vh; padding: 16px; }}
.card {{ background: #1a1f36; border-radius: 16px; padding: 24px 20px; max-width: 420px; margin: 0 auto; box-shadow: 0 8px 32px rgba(0,0,0,0.4); }}
.header {{ display: flex; align-items: center; gap: 12px; margin-bottom: 16px; }}
.header .badge {{ background: #ff6b35; color: #fff; padding: 4px 10px; border-radius: 6px; font-size: 12px; font-weight: 600; }}
.header h1 {{ font-size: 18px; color: #fff; }}
.context {{ background: #0d1117; border: 1px solid #30363d; border-radius: 10px; padding: 14px; margin: 12px 0; max-height: 240px; overflow-y: auto; }}
.ctx-label {{ color: #8b949e; font-size: 11px; text-transform: uppercase; letter-spacing: 0.5px; margin-bottom: 4px; margin-top: 8px; }}
.ctx-label:first-child {{ margin-top: 0; }}
.ctx-code {{ font-family: 'SF Mono', Menlo, monospace; font-size: 13px; color: #c9d1d9; word-break: break-all; white-space: pre-wrap; }}
.ctx-diff {{ font-family: 'SF Mono', Menlo, monospace; font-size: 12px; padding: 6px 8px; border-radius: 4px; margin: 4px 0; white-space: pre-wrap; word-break: break-all; }}
.ctx-del {{ background: #3d1f1f; color: #f85149; }}
.ctx-add {{ background: #1f3d1f; color: #56d364; }}
.ctx-desc {{ color: #8b949e; font-size: 12px; font-style: italic; margin-top: 4px; }}
.buttons {{ display: flex; gap: 10px; margin-top: 16px; }}
.btn {{ flex: 1; padding: 14px; border: none; border-radius: 10px; font-size: 16px; font-weight: 600; cursor: pointer; transition: all 0.15s; }}
.btn:active {{ transform: scale(0.96); opacity: 0.9; }}
.btn-approve {{ background: #238636; color: #fff; }}
.btn-deny {{ background: #da3633; color: #fff; }}
.reply-section {{ margin-top: 12px; }}
.reply-toggle {{ color: #58a6ff; font-size: 13px; cursor: pointer; text-decoration: underline; }}
.reply-box {{ display: none; margin-top: 8px; }}
.reply-box.show {{ display: block; }}
.reply-input {{ width: 100%; padding: 10px 12px; border: 1px solid #30363d; border-radius: 8px; background: #0d1117; color: #c9d1d9; font-size: 14px; resize: none; }}
.reply-send {{ margin-top: 8px; width: 100%; padding: 10px; border: none; border-radius: 8px; background: #1f6feb; color: #fff; font-size: 14px; font-weight: 500; cursor: pointer; }}
.time {{ text-align: center; color: #484f58; font-size: 11px; margin-top: 12px; }}
</style>
</head>
<body>
<div class="card" id="main-card">
  <div class="header">
    <span class="badge">{tool}</span>
    <h1>请求权限</h1>
  </div>
  <div class="context">{context}</div>
  <div class="buttons">
    <button class="btn btn-approve" onclick="decide('approve')">批准</button>
    <button class="btn btn-deny" onclick="decide('deny')">拒绝</button>
  </div>
  <div class="reply-section">
    <span class="reply-toggle" onclick="toggleReply()">💬 快捷回复...</span>
    <div class="reply-box" id="reply-box">
      <textarea class="reply-input" id="reply-msg" rows="2" placeholder="输入消息发回 Agent..."></textarea>
      <button class="reply-send" onclick="sendReply()">发送回复</button>
    </div>
  </div>
  <div class="time">{timestamp}</div>
</div>
<script>
function decide(action) {{
  fetch('/action/{action_id}/' + action, {{method:'POST'}}).then(() => {{
    document.getElementById('main-card').innerHTML = '<div style="text-align:center;padding:40px"><p style="font-size:48px">' + (action==='approve'?'✅':'❌') + '</p><h2>' + (action==='approve'?'已批准':'已拒绝') + '</h2><p style="color:#8b949e;margin-top:8px">可关闭此页面</p></div>';
  }}).catch(() => alert('网络错误'));
}}
function toggleReply() {{
  document.getElementById('reply-box').classList.toggle('show');
  document.getElementById('reply-msg').focus();
}}
function sendReply() {{
  const msg = document.getElementById('reply-msg').value;
  if (!msg) return;
  fetch('/action/{action_id}/reply', {{method:'POST', headers:{{'Content-Type':'application/json'}}, body:JSON.stringify({{message:msg}})}}).then(() => {{
    document.getElementById('main-card').innerHTML = '<div style="text-align:center;padding:40px"><p style="font-size:48px">💬</p><h2>已回复</h2><p style="color:#8b949e;margin-top:8px">' + msg.slice(0,30) + '</p></div>';
  }});
}}
</script>
</body>
</html>"""

ACTION_PAGE_EXPIRED = """<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>小铃铛</title>
<style>
body { font-family: -apple-system, sans-serif; background: #1a1a2e; color: #eee; min-height: 100vh; display: flex; align-items: center; justify-content: center; }
.card { text-align: center; padding: 40px; }
</style>
</head>
<body><div class="card"><p style="font-size:48px">⏰</p><h2>请求已过期或已处理</h2></div></body>
</html>"""

ACTION_PAGE_DONE = """<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>小铃铛</title>
<style>
body {{ font-family: -apple-system, sans-serif; background: #1a1a2e; color: #eee; min-height: 100vh; display: flex; align-items: center; justify-content: center; }}
.card {{ text-align: center; padding: 40px; }}
</style>
</head>
<body><div class="card"><h2>{result}</h2><p style="color:#aaa;margin-top:12px">可以关闭此页面</p></div></body>
</html>"""
