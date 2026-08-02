#!/usr/bin/env bash
# Deploy canyon_lake_monitor to production (iscanyonlakefullyet.org).
#
# Production is canyon-lake.service: a systemd unit that runs app.py as
# user richard straight out of this working tree. Deploying is therefore:
#   1. fast-forward this tree to latest origin/main
#   2. sync venv dependencies
#   3. restart the service — no root needed: the unit has Restart=always,
#      so killing the main PID makes systemd relaunch it (~10s, RestartSec)
#   4. verify the app answers before calling it a deploy
set -euo pipefail

cd "$(dirname "$0")"

SERVICE=canyon-lake
HEALTH_URL=http://localhost:8081/

branch=$(git rev-parse --abbrev-ref HEAD)
if [[ "$branch" != "main" ]]; then
    echo "ERROR: working tree is on '$branch', not main. Production deploys only from main." >&2
    exit 1
fi

echo "==> Pulling latest main"
git pull --ff-only

echo "==> Syncing dependencies"
./venv/bin/pip install -q -r requirements.txt

old_pid=$(systemctl show "$SERVICE" -p MainPID --value)
if [[ -z "$old_pid" || "$old_pid" == "0" ]]; then
    echo "ERROR: $SERVICE has no main PID — is it running? Try: systemctl status $SERVICE" >&2
    exit 1
fi

echo "==> Restarting $SERVICE (kill $old_pid; systemd relaunches it)"
kill "$old_pid"

echo "==> Waiting for the service to come back"
for _ in $(seq 1 12); do
    sleep 5
    new_pid=$(systemctl show "$SERVICE" -p MainPID --value)
    if [[ -n "$new_pid" && "$new_pid" != "0" && "$new_pid" != "$old_pid" ]] \
        && curl -sf -o /dev/null "$HEALTH_URL"; then
        echo "==> Deployed: $SERVICE running as PID $new_pid and $HEALTH_URL responds ($(git rev-parse --short HEAD))"
        exit 0
    fi
done

echo "ERROR: service did not come back healthy within 60s. Check: systemctl status $SERVICE" >&2
exit 1
