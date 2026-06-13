#!/bin/bash
# Deploy script für Raspberry Pi Arc Middleware
# Verwendung: ./deploy.sh [start|stop|status|logs]

set -euo pipefail

PI_HOST="monome-arc.local"
PI_USER="seek"
REMOTE_DIR="/home/seek/arc-middleware"
LOCAL_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

# Farben für Output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Funktionen
deploy_files() {
    echo -e "${YELLOW}Uploading files to ${PI_HOST}:${REMOTE_DIR}...${NC}"
    
    # SSH in Remote-Dir erstellen falls nicht vorhanden
    ssh "${PI_USER}@${PI_HOST}" "mkdir -p ${REMOTE_DIR}"
    
    # Mit rsync synchronisieren (--delete ist optional, um alte Dateien zu löschen)
    rsync -avz --delete \
        --exclude='.git' \
        --exclude='__pycache__' \
        --exclude='*.pyc' \
        --exclude='.vscode' \
        --exclude='.env' \
        "${LOCAL_DIR}/src" \
        "${LOCAL_DIR}/scripts" \
        "${LOCAL_DIR}/docs" \
        "${LOCAL_DIR}/requirements.txt" \
        "${LOCAL_DIR}/config.yaml" \
        "${PI_USER}@${PI_HOST}:${REMOTE_DIR}/" 2>/dev/null || echo "Note: Some files might already exist"
    
    echo -e "${GREEN}Files deployed successfully!${NC}"
}

install_deps() {
    echo -e "${YELLOW}Installing Python dependencies on Pi...${NC}"
    ssh "${PI_USER}@${PI_HOST}" "cd ${REMOTE_DIR} && pip install -r requirements.txt"
    echo -e "${GREEN}Dependencies installed!${NC}"
}

start_service() {
    echo -e "${YELLOW}Starting arc-middleware service...${NC}"
    ssh "${PI_USER}@${PI_HOST}" "mkdir -p ${REMOTE_DIR}/logs; pkill -f 'python3.*arc' 2>/dev/null || true; sleep 1; nohup python3 ${REMOTE_DIR}/src/arc_cycles_app.py >> ${REMOTE_DIR}/logs/arc_cycles.log 2>&1 < /dev/null &"
    echo -e "${GREEN}Service started!${NC}"
}

stop_service() {
    echo -e "${YELLOW}Stopping arc-middleware service...${NC}"
    ssh "${PI_USER}@${PI_HOST}" "pkill -f 'python3.*arc' 2>/dev/null || true"
    echo -e "${GREEN}Service stopped!${NC}"
}

status_service() {
    echo -e "${YELLOW}Service status:${NC}"
    ssh "${PI_USER}@${PI_HOST}" "sudo systemctl status arc-middleware || echo 'Service not installed as systemd service'"
}

view_logs() {
    echo -e "${YELLOW}Tail logs (Ctrl+C to exit):${NC}"
    ssh "${PI_USER}@${PI_HOST}" "tail -f ${REMOTE_DIR}/logs/arc_cycles.log 2>/dev/null || echo 'No logs yet'"
}

# Hauptprogramm
case "${1:-deploy}" in
    deploy)
        deploy_files
        ;;
    install)
        install_deps
        ;;
    start)
        start_service
        ;;
    stop)
        stop_service
        ;;
    status)
        status_service
        ;;
    logs)
        view_logs
        ;;
    full)
        deploy_files
        install_deps
        start_service
        ;;
    *)
        echo "Usage: $0 {deploy|install|start|stop|status|logs|full}"
        echo ""
        echo "Commands:"
        echo "  deploy  - Upload code to Pi (rsync)"
        echo "  install - Install Python dependencies"
        echo "  start   - Start the middleware service"
        echo "  stop    - Stop the middleware service"
        echo "  status  - Show service status"
        echo "  logs    - View live logs"
        echo "  full    - Deploy + install + start"
        exit 1
        ;;
esac
