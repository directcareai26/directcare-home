#!/usr/bin/env bash
# daily_publish.sh — the OS-level daily publish entry point.
#
# Invoked by ~/Library/LaunchAgents/com.directcareai.daily-blog.plist
# at 8 AM Eastern every day AND on every login. The "already-ran-today"
# flag below prevents double-posting when both fire on the same day.
#
# Why launchd instead of cron/Claude-Code-scheduled-tasks:
#   - launchd fires whether any apps are open or not
#   - launchd catches up if the Mac was off at 8 AM (fires on next boot/login)
#   - Independent of the Claude Code app being open

set -euo pipefail

REPO="/Users/dachewilliams/Desktop/Claude Code/Home Page (DCAI)"
LOG_DIR="$REPO/.daily-publish-logs"
FLAG_FILE="$LOG_DIR/last-run.txt"
TODAY=$(date "+%Y-%m-%d")
NOW=$(date "+%Y-%m-%d %H:%M:%S %Z")
LOG_FILE="$LOG_DIR/run-$TODAY.log"

mkdir -p "$LOG_DIR"

# Tee stdout+stderr into the log so we can diagnose silent failures later
exec > >(tee -a "$LOG_FILE") 2>&1

echo ""
echo "============================================================"
echo "Daily publish triggered: $NOW"
echo "============================================================"

# ---- 1. Already ran today? --------------------------------------------------
# Both StartCalendarInterval (8 AM) and RunAtLoad (every login) can fire on the
# same day. The flag file ensures we only actually publish once per calendar day.

if [ -f "$FLAG_FILE" ]; then
  LAST=$(cat "$FLAG_FILE" 2>/dev/null || echo "")
  if [ "$LAST" = "$TODAY" ]; then
    echo "Already published on $TODAY. Skipping."
    exit 0
  fi
fi

# ---- 2. Build a working environment ----------------------------------------
# launchd starts processes with a minimal PATH and no shell rc loaded.
# Source the user's zshrc to pick up ANTHROPIC_API_KEY, then layer on the
# binary paths we need for python3, git, npx (Homebrew, system, Python.framework).

if [ -f "$HOME/.zshrc" ]; then
  # shellcheck disable=SC1091
  set +u  # zshrc may reference unset vars
  source "$HOME/.zshrc" 2>/dev/null || true
  set -u
fi

export PATH="/opt/homebrew/bin:/usr/local/bin:/Library/Frameworks/Python.framework/Versions/3.14/bin:/usr/bin:/bin:$PATH"

if [ -z "${ANTHROPIC_API_KEY:-}" ]; then
  echo "ERROR: ANTHROPIC_API_KEY not set after sourcing ~/.zshrc."
  echo "Fix: open Terminal and verify 'echo \$ANTHROPIC_API_KEY' prints your key."
  exit 1
fi

echo "Environment OK (API key length: ${#ANTHROPIC_API_KEY}, PATH set)"

# ---- 3. Run the publish pipeline --------------------------------------------
cd "$REPO"

echo ""
echo "Invoking publish_now.sh..."
echo "------------------------------------------------------------"

if ./scripts/publish_now.sh; then
  echo ""
  echo "============================================================"
  echo "Publish succeeded. Marking $TODAY as done."
  echo "============================================================"
  echo "$TODAY" > "$FLAG_FILE"
  exit 0
else
  EXIT=$?
  echo ""
  echo "============================================================"
  echo "Publish FAILED (exit $EXIT). NOT marking flag — will retry next trigger."
  echo "============================================================"
  exit $EXIT
fi
