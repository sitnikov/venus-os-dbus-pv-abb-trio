#!/bin/bash
SCRIPT_DIR=$( cd -- "$( dirname -- "${BASH_SOURCE[0]}" )" &> /dev/null && pwd )
SERVICE_NAME=$(basename "$SCRIPT_DIR")

sed -i "/$SERVICE_NAME/d" /data/rc.local

SERVICE_FILE=/service/$SERVICE_NAME

echo "Remove service: $SERVICE_NAME ($SCRIPT_DIR)"
rm -rf "$SERVICE_FILE"

echo "Stop supervise $SERVICE_NAME"
pgrep -f "supervise $SERVICE_NAME" | xargs -r kill

"$SCRIPT_DIR"/restart.sh
