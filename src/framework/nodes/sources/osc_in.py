import socket
import logging
import threading
import time
from pythonosc import osc_packet
from framework.nodes.base_node import BaseNode
from pydantic import BaseModel
from framework.data.data_packet import DataPacket
from framework.data.data_types import *
from framework.core.decorators import node_telemetry

class OSCInNode(BaseNode):
    """Node for receiving OSC messages via UDP and emitting DataPackets"""
    node_type = "osc_in"
    tags = ["network", "osc"]
    MIN_INPUTS = 0
    MAX_INPUTS = 0
    IS_GENERATOR = True

    accepted_data_types = {DataType.STREAM, DataType.DERIVED, DataType.STATIC}
    accepted_formats = {DataFormat.BINARY}
    accepted_categories = set(DataCategory)

    class Params(BaseModel):
        listen_ip: str = "0.0.0.0"
        listen_port: int = 9000
        timeout: float = 0.1
        buffer_size: int = 2048

    def __init__(self, config):
        super().__init__(config)
        self.logger = logging.getLogger(self.node_type)
        self.params = self.Params(**config.get("params", {}))
        self._running = threading.Event()
        self._thread = None
        self.sock = None
        self.logger.info(f"Initializing OSC listener on {self.params.listen_ip}:{self.params.listen_port}")

    def should_process(self):
        return False

    def start(self):
        if self._running.is_set():
            return

        try:
            self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            self.sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            if hasattr(socket, "SO_REUSEPORT"):
                self.sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEPORT, 1)
            self.sock.settimeout(self.params.timeout)
            self.sock.bind((self.params.listen_ip, self.params.listen_port))

            self._running.set()
            self._thread = threading.Thread(
                target=self._receive_loop,
                name=f"OSCIn-{self.params.listen_port}",
                daemon=True
            )
            self._thread.start()
            self.logger.info(f"Started OSC listener on {self.params.listen_ip}:{self.params.listen_port}")
        except Exception as e:
            self.logger.error(f"Failed to start OSC listener: {e}", exc_info=True)
            raise

    @node_telemetry("receive")
    def _receive_loop(self):
        while self._running.is_set():
            try:
                data, addr = self.sock.recvfrom(self.params.buffer_size)
                self.logger.debug(f"Received {len(data)} bytes OSC packet from {addr}")

                pkt = osc_packet.OscPacket(data)
                for tm in pkt.messages:
                    # Unwrap TimedMessage if necessary
                    msg = tm.message if hasattr(tm, "message") else tm
                    # msg is now an OscMessage with .address and .params
                    address = getattr(msg, "address", None)
                    args = getattr(msg, "params", None) or getattr(msg, "params", [])
                    content = {
                        "address": address,
                        "args": args,
                        "remote_addr": addr
                    }
                    out_pkt = DataPacket(
                        data_type=DataType.STREAM,
                        format=DataFormat.TEXTUAL,
                        category=DataCategory.NETWORK,
                        source=DataSource.EXTERNAL,
                        content=content,
                        metadata={}
                    )
                    self.data_bus.publish(self.outputs[0], out_pkt)

            except socket.timeout:
                continue
            except Exception as e:
                if self._running.is_set():
                    self.logger.error(f"OSC receive error: {e}", exc_info=True)
                break

        self.logger.info("OSC receive thread exiting")

    def stop(self):
        if not self._running.is_set():
            return

        self.logger.debug("Stopping OSC listener")
        self._running.clear()

        if self.sock:
            try:
                self.sock.close()
            except Exception:
                pass
            finally:
                self.sock = None

        if self._thread and self._thread.is_alive():
            self._thread.join(timeout=2.0)
            if self._thread.is_alive():
                self.logger.warning("OSC listener thread did not exit cleanly")

        self.logger.info("OSC listener stopped")

    def cleanup(self):
        self.stop()

NODE_CLASSES = [OSCInNode]
