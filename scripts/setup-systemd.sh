#!/bin/bash
# Systemd Service auf Raspberry Pi einrichten
# Ausführen mit: ssh seek@monome-arc.local 'bash -s' < scripts/setup-systemd.sh

SERVICE_NAME="arc-cycles"
REMOTE_DIR="/home/seek/arc-middleware"
SERVICE_FILE="/etc/systemd/system/${SERVICE_NAME}.service"

echo "Setting up ${SERVICE_NAME} as systemd service..."

mkdir -p "${REMOTE_DIR}/logs"

sudo tee "${SERVICE_FILE}" > /dev/null <<EOF
[Unit]
Description=Monome Arc Cycles
After=network.target

[Service]
Type=simple
User=seek
WorkingDirectory=${REMOTE_DIR}
ExecStart=/usr/bin/python3 ${REMOTE_DIR}/src/arc_cycles_app.py
Restart=always
RestartSec=5
StandardOutput=append:${REMOTE_DIR}/logs/arc_cycles.log
StandardError=append:${REMOTE_DIR}/logs/arc_cycles.log

[Install]
WantedBy=multi-user.target
EOF

sudo systemctl daemon-reload
sudo systemctl enable "${SERVICE_NAME}"
sudo systemctl start "${SERVICE_NAME}"

echo "Done! Service '${SERVICE_NAME}' is running."
echo "Status: sudo systemctl status ${SERVICE_NAME}"
echo "Logs:   tail -f ${REMOTE_DIR}/logs/arc_cycles.log"
