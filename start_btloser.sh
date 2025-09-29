#!/bin/bash
# start_btloser.sh

cd "$(dirname "$0")"

# Remove old container if it exists
docker rm -f btloser_app 2>/dev/null || true

# Build Docker image
docker compose build

# Start container in detached mode
docker compose up -d

echo "BTL Roster app is running in Docker. Access it on http://<server-ip>:8501"

