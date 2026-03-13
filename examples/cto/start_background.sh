#!/bin/bash

# Configuration
APP_DIR="/Users/aaronrodrigues/projects/clawgraph/examples/cto"
ROOT_DIR="/Users/aaronrodrigues/projects/clawgraph"
PORT=8000
LOG_FILE="${APP_DIR}/logs/background_server.log"
PID_FILE="${APP_DIR}/.server.pid"

echo "=========================================="
echo " CLAWGRAPH CTO - CANONICAL STARTUP"
echo "=========================================="

# 1. Kill any existing process on the port
echo "[1/4] Checking for existing server on port ${PORT}..."
EXISTING_PID=$(lsof -t -i:${PORT})
if [ -z "$EXISTING_PID" ]; then
    # Fallback: check pid file
    if [ -f "$PID_FILE" ]; then
        EXISTING_PID=$(cat "$PID_FILE")
    fi
fi

if [ ! -z "$EXISTING_PID" ]; then
    echo "Found existing process ${EXISTING_PID}. Killing..."
    kill -9 $EXISTING_PID 2>/dev/null
    sleep 2
fi

# 2. Setup environment
echo "[2/4] Setting up environment..."
cd "${ROOT_DIR}"
export PYTHONPATH=$PYTHONPATH:.

# 3. Start simulation in background
echo "[3/4] Starting simulation in background..."
mkdir -p "${APP_DIR}/logs"
# we use start_simulation.py as it is the reactive hub
nohup python examples/cto/start_simulation.py > "${LOG_FILE}" 2>&1 &
NEW_PID=$!
echo $NEW_PID > "$PID_FILE"

# 4. Verification
echo "[4/4] Verifying startup..."
sleep 3
if ps -p $NEW_PID > /dev/null; then
    echo "SUCCESS: CTO Simulation started with PID ${NEW_PID}"
    echo "HUD: http://localhost:${PORT}"
    echo "LOG: ${LOG_FILE}"
    # Extract the actual timestamped log file path from the redirect log
    ACTUAL_LOG=$(grep "reasoning being written to:" "${LOG_FILE}" | awk '{print $NF}')
    if [ ! -z "$ACTUAL_LOG" ]; then
        echo "REASONING LOG: ${ACTUAL_LOG}"
    fi
else
    echo "FAILURE: Server died shortly after startup. Check ${LOG_FILE}"
    exit 1
fi
