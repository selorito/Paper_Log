#!/usr/bin/env bash
# Installs Paper Log: venv, git repo, and systemd user units
# (web server always on + reminder emails at 10:00, 15:00, 20:00 until today's note is saved).
set -euo pipefail
cd "$(dirname "$0")"
DIR="$(pwd)"
PY="$DIR/.venv/bin/python"

if [ ! -x "$PY" ]; then
  if command -v uv >/dev/null; then uv venv -q .venv && uv pip install -q --python "$PY" -r requirements.txt
  else python3 -m venv .venv && "$PY" -m pip install -q -r requirements.txt; fi
fi

[ -f .env ] || { cp .env.example .env; chmod 600 .env; echo "Created .env — fill in your Gmail app password."; }

if [ ! -d .git ]; then
  git init -q -b main
  "$PY" -c "import store; store.write_readme()"
  git add .
  git commit -q -m "chore: set up paper log"
fi

UNIT_DIR="$HOME/.config/systemd/user"
mkdir -p "$UNIT_DIR"

cat > "$UNIT_DIR/paper-log-web.service" <<EOF
[Unit]
Description=Paper Log website

[Service]
WorkingDirectory=$DIR
ExecStart=$PY $DIR/app.py
Restart=on-failure

[Install]
WantedBy=default.target
EOF

cat > "$UNIT_DIR/paper-log-remind.service" <<EOF
[Unit]
Description=Paper Log reminder email
After=network-online.target

[Service]
Type=oneshot
WorkingDirectory=$DIR
ExecStart=$PY $DIR/remind.py
EOF

cat > "$UNIT_DIR/paper-log-remind.timer" <<EOF
[Unit]
Description=Paper Log reminders (10:00, 15:00, 20:00)

[Timer]
OnCalendar=*-*-* 10,15,20:00:00
Persistent=true

[Install]
WantedBy=timers.target
EOF

systemctl --user daemon-reload
systemctl --user enable --now paper-log-web.service paper-log-remind.timer
systemctl --user restart paper-log-web.service

echo
echo "Paper Log is running at http://localhost:$(grep -E '^PORT=' .env | cut -d= -f2 || echo 5050)"
systemctl --user list-timers paper-log-remind.timer --no-pager | head -2
