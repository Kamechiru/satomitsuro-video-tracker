#!/bin/bash
# 手動実行用(旧launchd用)。毎朝6時の定期実行は Claude の「ルーティン」(スケジュールタスク)が行う。
# 通知は task_prompt.md の手順9が terminal-notifier で出す。
set -uo pipefail

export PATH="/opt/homebrew/bin:/usr/local/bin:$PATH"

REPO_DIR="$HOME/satomitsuro-video-tracker"
LOG_FILE="$REPO_DIR/last_run.log"

cd "$REPO_DIR" || exit 1

echo "=== Run started: $(date -u +%Y-%m-%dT%H:%M:%SZ) ===" >> "$LOG_FILE"

claude -p "$(cat task_prompt.md)" \
  --permission-mode bypassPermissions \
  --allowedTools "Bash,Read,Write,Edit,Glob,Grep,Artifact" \
  --output-format text \
  >> "$LOG_FILE" 2>&1

echo "=== Run finished: $(date -u +%Y-%m-%dT%H:%M:%SZ) ===" >> "$LOG_FILE"
