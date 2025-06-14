import socket
import logging
import threading
from framework.nodes.base_node import BaseNode
from pydantic import BaseModel
from framework.data.data_packet import DataPacket
from framework.data.data_types import *

class UDPIn(BaseNode):
    """Node for receiving data via UDP and emitting DataPackets"""
    node_type = "udp_in"
    IS_ACTIVE = True
    accepted_formats = {DataFormat.BINARY}
    accepted_categories = {DataCategory.NETWORK}

    class Params(BaseModel):
        listen_ip: str = "0.0.0.0"
        listen_port: int = 7000
        timeout: float = 0.1
        buffer_size: int = 1024

    def __init__(self, config):
        super().__init__(config)
        self.logger = logging.getLogger('udp_in')
        self.logger.setLevel(logging.DEBUG)
        
        try:
            self.params = self.Params(**config.get('params', {}))
            self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            self.sock.settimeout(self.params.timeout)
            self.sock.bind((self.params.listen_ip, self.params.listen_port))
            
            self._running = threading.Event()
            self._thread = None
            self.logger.info(f"Initialized UDP listener on {self.params.listen_ip}:{self.params.listen_port}")
            
            # Start thread immediately on init
            self.run()
            
        except Exception as e:
            self.logger.error(f"Init failed: {str(e)}", exc_info=True)
            raise

    def should_process(self):
        """Override for active nodes - return False since we manage our own thread"""
        return False  # Critical change!

    def process(self):
        """Main receive loop - now only called by our dedicated thread"""
        while self._running.is_set():
            try:
                data, addr = self.sock.recvfrom(self.params.buffer_size)
                self.logger.debug(f"Received {len(data)} bytes from {addr}")
                
                packet = self.create_packet(
                    content=data,
                    metadata={"remote_addr": addr}
                )
                
                self.data_bus.publish(self.outputs[0], packet)
                
                
            except socket.timeout:
                continue
            except Exception as e:
                self.logger.error(f"Receive error: {str(e)}")
                break

        self.logger.info("Receive thread exiting")

    def run(self):
        """Start the listener thread"""
        if self._thread and self._thread.is_alive():
            self.logger.warning("Thread already running")
            return
            
        self._running.set()
        self._thread = threading.Thread(
            target=self.process,
            name=f"UDPIn-{self.params.listen_port}",
            daemon=True
        )
        self._thread.start()
        self.logger.debug("Started listener thread")

    def cleanup(self):
        """Stop the thread and close socket"""
        self.logger.debug("Beginning cleanup")
        self._running.clear()
        
        if self._thread:
            self._thread.join(timeout=2)
            if self._thread.is_alive():
                self.logger.warning("Thread did not exit cleanly")
        
        if self.sock:
            self.sock.close()
            self.logger.debug("Socket closed")
        
        self.logger.info("Cleanup complete")

NODE_CLASSES = [UDPIn]