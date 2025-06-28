import socket
import logging
from framework.nodes.base_node import BaseNode
from pydantic import BaseModel
from framework.data.data_packet import DataPacket
from framework.data.data_types import *
from framework.core.decorators import node_telemetry

class UDPOut(BaseNode):
    """Node for sending validated DataPackets via UDP"""
    node_type = "udp_out"
    accepted_data_types = set(DataType)
    accepted_formats = set(DataFormat)
    accepted_categories = set(DataCategory)

    class Params(BaseModel):
        ip: str = "127.0.0.1"
        port: int = 7000
        buffer_size: int = 1024

    def __init__(self, config):
        super().__init__(config)
        self.params = self.Params(**config.get('params', {}))
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.logger = logging.getLogger('udp_out')
        self.logger.info(f"Initialized UDP output to {self.params.ip}:{self.params.port}")

    @node_telemetry("on_data")
    def on_data(self, packet: DataPacket, _input_channel: str = None):
        """Handle incoming DataPacket using BaseNode validation"""

        try:
            # Extract raw content from DataPacket
            payload = packet.content
            
            # Convert to bytes if needed
            if not isinstance(payload, bytes):
                payload = str(payload).encode('utf-8')

            # Truncate to buffer size if necessary
            if len(payload) > self.params.buffer_size:
                payload = payload[:self.params.buffer_size]
                self.logger.warning("Truncated oversized payload")

            self.sock.sendto(payload, (self.params.ip, self.params.port))
            self.logger.debug(f"Sent {len(payload)} bytes to {self.params.ip}:{self.params.port}")
            
        except Exception as e:
            self.logger.error(f"Transmission failed: {str(e)}")

    def cleanup(self):
        """Close socket connection"""
        if self.sock:
            self.sock.close()
            self.logger.info("UDP connection closed")

NODE_CLASSES = [UDPOut]