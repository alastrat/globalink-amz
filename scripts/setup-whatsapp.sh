#!/bin/bash
set -e

IP="${1:?Usage: setup-whatsapp.sh <vps-ip>}"

echo ""
echo "=== WhatsApp Setup for $IP ==="
echo "Scan the QR code with WhatsApp → Settings → Linked Devices → Link a Device"
echo ""

ssh -t "root@$IP" "docker stop globalink-fba-nanoclaw 2>/dev/null || true; cd /opt/nanoclaw && node setup-wa.js"

echo ""
echo "Starting NanoClaw..."
ssh "root@$IP" "docker start globalink-fba-nanoclaw"

sleep 5

STATUS=$(ssh "root@$IP" "docker inspect globalink-fba-nanoclaw --format '{{.State.Status}}'" 2>/dev/null)
if [ "$STATUS" = "running" ]; then
  echo "✅ WhatsApp connected and NanoClaw running!"
else
  echo "⚠️  NanoClaw status: $STATUS — check logs with: ssh root@$IP docker logs globalink-fba-nanoclaw"
fi
