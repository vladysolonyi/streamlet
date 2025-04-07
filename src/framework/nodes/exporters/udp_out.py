import socket
import logging
from framework.nodes.base_node import BaseNode

class UDPOut(BaseNode):
    """Node for sending processed data via UDP"""
    node_type = "udp_out"
    
    def __init__(self, config):
        super().__init__(config)
        params = config.get('params', {})
        
        # Network configuration
        self.target_ip = params.get('ip', '127.0.0.1')
        self.target_port = params.get('port', 12345)
        self.protocol = params.get('protocol', 'UDP').upper()
        
        # Socket setup
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.logger = logging.getLogger('udp_out')
        
        self.logger.info(f"Initialized UDP output to {self.target_ip}:{self.target_port}")

    def on_data(self, data):
        """Handle incoming data from DataBus"""
        try:
            if isinstance(data, bytes):
                payload = data
            else:
                payload = str(data).encode('utf-8')
            
            self.sock.sendto(payload, (self.target_ip, self.target_port))
            self.logger.debug(f"Sent {len(payload)} bytes to {self.target_ip}:{self.target_port}")
        except Exception as e:
            self.logger.error(f"Failed to send UDP packet: {str(e)}")

    def cleanup(self):
        """Close network connection"""
        self.sock.close()
        self.logger.info("Closed UDP connection")

NODE_CLASSES = [UDPOut]