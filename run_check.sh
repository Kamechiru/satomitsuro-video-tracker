#!/bin/bash
set -uo pipefail

export PATH="/opt/homebrew/bin:/usr/local/bin:$PATH"

REPO_DIR="$HOME/Documents/satomitsuro-video-tracker"
LOG_FILE="$REPO_DIR/last_run.log"

cd "$REPO_DIR" || exit 1

echo "=== Run started: $(date -u +%Y-%m-%dT%H:%M:%SZ) ===" >> "$LOG_FILE"

rm -f notify_status.txt new_summaries.txt

claude -p "$(cat task_prompt.md)" \
  --permission-mode bypassPermissions \
  --allowedTools "Bash,Read,Write,Edit,Glob,Grep,Artifact" \
  --output-format text \
  >> "$LOG_FILE" 2>&1

echo "=== Run finished: $(date -u +%Y-%m-%dT%H:%M:%SZ) ===" >> "$LOG_FILE"

if [ -f notify_status.txt ]; then
  STATUS=$(cat notify_status.txt)
  if [[ "$STATUS" == NEW:* ]]; then
    MSG="${STATUS#NEW:}"
    osascript -e "display notification \"$MSG\" with title \"YouTube新着チェッカー\" sound name \"Glass\""
  fi
fi
