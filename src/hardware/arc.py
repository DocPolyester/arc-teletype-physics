"""
Arc Controller - Handles serialosc/OSC communication with Monome Arc
"""
import logging
import threading
from typing import Callable, List, Optional

from pythonosc import udp_client, dispatcher, osc_server

logger = logging.getLogger(__name__)

SERIALOSC_PORT = 12002


def discover_arc(host: str = "127.0.0.1", timeout: float = 2.0):
    """
    Query serialoscd on port 12002 to discover the Arc device.
    Returns (port, num_rings) or (None, 4) if no Arc is found.
    """
    result = {"port": None, "rings": 4}
    done = threading.Event()

    def handle_device(addr, serial, device_type, port):
        logger.info(f"serialosc device found: {serial} ({device_type}) on port {port}")
        result["port"] = int(port)
        # "monome arc 4" → 4, "monome arc 2" → 2, etc.
        for word in str(device_type).split():
            if word.isdigit():
                result["rings"] = int(word)
                break
        done.set()

    listen_port = 12099
    d = dispatcher.Dispatcher()
    d.map("/serialosc/device", handle_device)

    for attempt_port in (12099, 12098, 12097):
        try:
            srv = osc_server.ThreadingOSCUDPServer((host, attempt_port), d)
            listen_port = attempt_port
            break
        except OSError:
            continue
    else:
        logger.warning("Could not bind discovery listener port")
        return None, 4

    t = threading.Thread(target=srv.serve_forever, daemon=True)
    t.start()

    client = udp_client.SimpleUDPClient(host, SERIALOSC_PORT)

    # Retry up to 3× — serialosc-device may take a few seconds to connect at boot
    for attempt in range(3):
        client.send_message("/serialosc/list", [host, listen_port])
        done.wait(timeout=timeout)
        if result["port"] is not None:
            break
        if attempt < 2:
            logger.info(f"Discovery attempt {attempt+1} found nothing, retrying...")

    srv.shutdown()

    if result["port"] is None:
        logger.warning("No Arc device found via serialosc discovery")
    return result["port"], result["rings"]


class ArcController:
    """
    Communicates with Monome Arc via serialosc/OSC protocol.
    Uses python-osc for both sending and receiving.
    """

    def __init__(self, host: str = "127.0.0.1", port: int = 14951, prefix: str = "/monome"):
        self.host = host
        self.prefix = prefix

        discovered_port, self.num_rings = discover_arc(host)
        if discovered_port is not None:
            self.port = discovered_port
        else:
            self.port = port
            logger.warning(f"Discovery failed, falling back to configured port {port}")

        self.client = udp_client.SimpleUDPClient(host, self.port)
        self._server: Optional[osc_server.ThreadingOSCUDPServer] = None
        self._server_thread: Optional[threading.Thread] = None
        self.encoder_callback: Optional[Callable[[int, int], None]] = None
        self.press_callback:   Optional[Callable[[int], None]]      = None
        logger.info(f"ArcController initialized for {host}:{self.port} prefix={prefix}")

    def set_ring_led(self, ring: int, position: int, brightness: int):
        self.client.send_message(f"{self.prefix}/ring/set", [ring, position, brightness])

    def set_ring_all(self, ring: int, brightness: int):
        self.client.send_message(f"{self.prefix}/ring/all", [ring, brightness])

    def set_ring_map(self, ring: int, levels: List[int]):
        """Set all 64 LEDs on a ring atomically. levels: list of 64 ints (0-15)."""
        self.client.send_message(f"{self.prefix}/ring/map", [ring] + list(levels))

    def clear_ring(self, ring: int):
        self.set_ring_all(ring, 0)

    def start_receiver(self, listen_port: int,
                       encoder_callback: Callable[[int, int], None],
                       press_callback: Optional[Callable[[int], None]] = None):
        """
        Start OSC receiver and tell serialosc to send encoder events here.
        encoder_callback(ring, delta) is called on each encoder turn.
        press_callback(ring) is called on encoder press (key down).
        """
        self.encoder_callback = encoder_callback
        self.press_callback   = press_callback

        # Tell the Arc device where to send events
        self.client.send_message("/sys/host", ["127.0.0.1"])
        self.client.send_message("/sys/port", [listen_port])

        d = dispatcher.Dispatcher()
        d.map(f"{self.prefix}/enc/delta", self._handle_encoder_delta)
        d.map(f"{self.prefix}/enc/key",   self._handle_encoder_key)

        self._server = osc_server.ThreadingOSCUDPServer(("0.0.0.0", listen_port), d)
        self._server_thread = threading.Thread(target=self._server.serve_forever, daemon=True)
        self._server_thread.start()
        logger.info(f"OSC receiver started on port {listen_port}")

    def _handle_encoder_delta(self, addr: str, ring: int, delta: int):
        if self.encoder_callback:
            self.encoder_callback(ring, delta)

    def _handle_encoder_key(self, addr: str, ring: int, state: int):
        if state == 1 and self.press_callback:   # nur Key-Down, nicht Key-Up
            self.press_callback(ring)

    def close(self):
        if self._server:
            self._server.shutdown()
        logger.info("ArcController closed")
