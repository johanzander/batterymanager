# start-dev.sh
#!/bin/bash

echo "Killing any existing uvicorn processes..."
pkill -f uvicorn

echo "Starting uvicorn..."
PYTHONPATH=/workspaces/batterymanager/backend:/workspaces/batterymanager uvicorn backend.api:app --reload --port 8080 &

echo "Starting frontend server..."
cd /workspaces/batterymanager/frontend
npm run dev