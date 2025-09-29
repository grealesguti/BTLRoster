#!/bin/bash
# start_btloser.sh
# Builds and starts the BTL Roster app in Docker (folder: same as script)

# Go to the folder where the script is located
cd "$(dirname "$0")"

# Build Docker image (only rebuilds if Dockerfile changed)
docker compose build

# Start container in detached mode
docker compose up -d

echo "BTL Roster app is running in Docker. Access it on http://<server-ip>:5000"

