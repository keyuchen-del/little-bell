#!/bin/bash
# 小铃铛 - Claude Code Hook
# 由 Claude Code hooks 系统调用，将事件转发到小铃铛本地服务
# Usage: claude_code_hook.sh <event_type>

EVENT_TYPE="${1:-unknown}"
STDIN_DATA=$(cat 2>/dev/null || echo '{}')

# Validate JSON, fallback to empty object
echo "$STDIN_DATA" | python3 -c "import sys,json; json.load(sys.stdin)" 2>/dev/null || STDIN_DATA='{}'

curl -s -m 1 -X POST http://127.0.0.1:6789/event \
  -H "Content-Type: application/json" \
  -d "{\"agent\":\"claude-code\",\"event\":\"${EVENT_TYPE}\",\"data\":${STDIN_DATA}}" \
  >/dev/null 2>&1 || true
