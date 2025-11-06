#!/bin/bash
# start_btloser.sh - debug version

cd "$(dirname "$0")"

# Remove old container if it exists
docker rm -f btloser_app 2>/dev/null || true

# Build Docker image
docker compose build

# Start container in detached mode
docker compose up -d

echo "BTL Roster app is running in Docker. Access it on http://<server-ip>:8501"

# ------------------------------
# Debug: check folder mappings
# ------------------------------

echo "=== Host folder contents ==="
echo "Newdles:"
ls -l /mnt/VDEV/appData/Stacks/BTLApps/BTLRoster/app/Newdles
echo "weekly_rosters:"
ls -l /mnt/VDEV/appData/Stacks/BTLApps/BTLRoster/app/weekly_rosters
echo "Availability:"
ls -l /mnt/VDEV/appData/Stacks/BTLApps/BTLRoster/app/Availability

echo
echo "=== Container folder contents ==="
docker exec btloser_app ls -l /app/Newdles
docker exec btloser_app ls -l /app/weekly_rosters
docker exec btloser_app ls -l /app/Availability

