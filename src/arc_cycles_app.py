#!/usr/bin/env python3
"""
Arc Cycles Application
"""
import sys
import logging
import yaml
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from hardware.arc import ArcController
from hardware.arduino_serial import ArduinoSerialHandler
from apps.arc_cycles.main import ArcCyclesApp

PROJECT_ROOT = Path(__file__).parent.parent
LOG_DIR = PROJECT_ROOT / "logs"
LOG_DIR.mkdir(exist_ok=True)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[
        logging.FileHandler(LOG_DIR / "arc_cycles.log"),
        logging.StreamHandler(sys.stdout),
    ],
)
logger = logging.getLogger(__name__)

OSC_LISTEN_PORT = 13001


def main():
    logger.info("=" * 60)
    logger.info("Arc Cycles starting")
    logger.info("=" * 60)

    config_path = PROJECT_ROOT / "config.yaml"
    with open(config_path) as f:
        config = yaml.safe_load(f)

    arc = ArcController(
        host=config.get("arc_host", "127.0.0.1"),
        port=config.get("arc_port", 14951),
        prefix=config.get("arc_prefix", "/monome"),
    )

    num_rings = arc.num_rings
    logger.info(f"Detected {num_rings} ring(s)")

    i2c_slave = None
    arduino_cfg = config.get("arduino_serial", {})
    if arduino_cfg.get("enabled", False):
        port    = arduino_cfg.get("port", "/dev/ttyUSB1")
        address = arduino_cfg.get("address", 0x31)
        i2c_slave = ArduinoSerialHandler(port=port, address=address)
        logger.info(f"Arduino Serial Bridge: {port}  I2C-Adresse=0x{address:02x}")

    default_mode = config.get("default_mode", "cycles")
    ring_modes   = config.get("ring_modes", None)

    app = ArcCyclesApp(
        arc=arc,
        num_rings=num_rings,
        i2c_slave=i2c_slave,
        default_mode=default_mode,
        ring_modes=ring_modes,
    )

    arc.start_receiver(
        listen_port=OSC_LISTEN_PORT,
        encoder_callback=app.on_encoder_turn,
        press_callback=app.on_encoder_press,
        release_callback=app.on_encoder_release,
    )

    logger.info(f"Listening for encoder events on port {OSC_LISTEN_PORT}")
    logger.info(f"Ring modes: {app.ring_mode_names}")

    app.start()


if __name__ == "__main__":
    main()
