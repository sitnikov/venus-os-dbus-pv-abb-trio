#!/bin/bash
SCRIPT_DIR=$( cd -- "$( dirname -- "${BASH_SOURCE[0]}" )" &> /dev/null && pwd )
SERVICE_NAME=$(basename "$SCRIPT_DIR")

echo "Kill $SERVICE_NAME.py"
pgrep -f "$SERVICE_NAME.py" |  xargs -r kill
