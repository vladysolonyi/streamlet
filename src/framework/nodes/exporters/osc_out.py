# framework/nodes/exporters/osc_out.py
import logging
from pythonosc import udp_client
from framework.nodes.base_node import BaseNode
from pydantic import BaseModel
from framework.data.data_types import *

class OSCOutNode(BaseNode):
    """Node for sending DataPackets as OSC messages"""
    node_type = "osc_out"
    MIN_INPUTS = 1
    MAX_INPUTS = 1
    IS_GENERATOR = False
    accepted_data_types = set(DataType)
    accepted_formats = set(DataFormat)
    accepted_categories = set(DataCategory)


    class Params(BaseModel):
        ip: str = "127.0.0.1"
        port: int = 9001
        default_address: str = "/data"
        send_as_bundle: bool = False

    def __init__(self, config):
        super().__init__(config)
        self.logger = logging.getLogger('osc_out')
        self.logger.setLevel(logging.DEBUG)
        
        self.params = self.Params(**config.get('params', {}))
        self.client = None
        self._setup_client()

    def _setup_client(self):
        """Create and configure OSC client"""
        try:
            self.client = udp_client.SimpleUDPClient(self.params.ip, self.params.port)
            self.logger.info(f"Configured OSC output to {self.params.ip}:{self.params.port}")
        except Exception as e:
            self.logger.error(f"Client setup failed: {str(e)}")
            raise

    def process(self):
        """Process incoming data and send as OSC"""
        if not self.input_buffers[self.inputs[0]]:
            return
            
        while self.input_buffers[self.inputs[0]]:
            packet = self.input_buffers[self.inputs[0]].pop(0)
            self._send_packet(packet)

    def _send_packet(self, packet):
        """Convert and send a DataPacket as OSC message"""
        try:
            content = packet.content
            
            address = content.get("address", self.params.default_address)
            
            # Handle different content types
            if isinstance(content, dict) and "arguments" in content:
                # Direct OSC format
                self.client.send_message(address, content["arguments"])
            elif isinstance(content, (list, tuple)):
                # List of values
                self.client.send_message(address, content)
            elif isinstance(content, dict):
                # Dictionary as named arguments
                self.client.send_message(address, list(content.values()))
            else:
                # Single value
                self.client.send_message(address, content)
                
            self.logger.debug(f"Sent OSC: {address} with {type(content).__name__}")
            
        except Exception as e:
            self.logger.error(f"Send failed: {str(e)}", exc_info=True)

    def send_message(self, address: str, *args):
        """Direct send method for manual control"""
        if not self.client:
            return
            
        try:
            self.client.send_message(address, args)
            self.logger.debug(f"Sent manual OSC: {address} {args}")
        except Exception as e:
            self.logger.error(f"Manual send failed: {str(e)}")

    def cleanup(self):
        """Clean up resources"""
        self.client = None
        self.logger.info("OSC client cleaned up")

NODE_CLASSES = [OSCOutNode]