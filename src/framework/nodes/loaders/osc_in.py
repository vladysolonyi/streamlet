# framework/nodes/loaders/osc_in.py
import logging
from pythonosc import dispatcher, osc_server
from threading import Thread
from framework.nodes.base_node import BaseNode
from pydantic import BaseModel
from framework.data.data_packet import DataPacket
from framework.data.data_types import *

class OSCInNode(BaseNode):
    """Node for receiving OSC messages and converting to DataPackets"""
    node_type = "osc_in"
    MIN_INPUTS = 0
    MAX_INPUTS = 0
    IS_ACTIVE = True
    accepted_data_types = set(DataCategory)
    accepted_formats = set(DataCategory)
    accepted_categories = set(DataCategory)

    class Params(BaseModel):
        listen_ip: str = "0.0.0.0"
        listen_port: int = 9000
        timeout: float = 0.1

    def __init__(self, config):
        super().__init__(config)
        self.logger = logging.getLogger('osc_in')
        self.logger.setLevel(logging.DEBUG)
        
        self.params = self.Params(**config.get('params', {}))
        self.server = None
        self._running = threading.Event()
        self._thread = None
        self.dispatcher = dispatcher.Dispatcher()
        self.logger.info(f"Initializing OSC listener on {self.params.listen_ip}:{self.params.listen_port}")

        # Setup default handler
        self.dispatcher.set_default_handler(self._handle_osc_message)

    def should_process(self):
        return False

    def start(self):
        """Start the OSC server thread"""
        if self._running.is_set():
            return
            
        try:
            self.server = osc_server.ThreadingOSCUDPServer(
                (self.params.listen_ip, self.params.listen_port),
                self.dispatcher
            )
            self.server.timeout = self.params.timeout
            
            self._running.set()
            self._thread = Thread(
                target=self._serve_forever,
                name=f"OSCIn-{self.params.listen_port}",
                daemon=True
            )
            self._thread.start()
            self.logger.info(f"Started OSC listener on {self.params.listen_ip}:{self.params.listen_port}")
        except Exception as e:
            self.logger.error(f"Start failed: {str(e)}", exc_info=True)
            raise

    def _serve_forever(self):
        """Main server loop"""
        while self._running.is_set():
            try:
                self.server.handle_request()
            except Exception as e:
                if self._running.is_set():
                    self.logger.error(f"Server error: {str(e)}")

    def _handle_osc_message(self, address, *args):
        """Handle incoming OSC messages"""
        try:
            if not self._running.is_set():
                return
                
            self.logger.debug(f"Received OSC: {address} {args}")
            
            # Create data packet
            packet = self.create_packet(
                content={
                    "address": address,
                    "arguments": args
                },
                format=DataFormat.OSC,
                data_type=DataType.EVENT,
                category=DataCategory.CONTROL
            )
            
            # Publish to data bus
            self.data_bus.publish(self.outputs[0], packet)
            
        except Exception as e:
            self.logger.error(f"Message handling failed: {str(e)}", exc_info=True)

    def stop(self):
        """Stop the server"""
        if not self._running.is_set():
            return
            
        self.logger.debug("Stopping OSC listener")
        self._running.clear()
        
        # Shutdown server
        if self.server:
            try:
                self.server.shutdown()
            except:
                pass
        
        # Wait for thread to finish
        if self._thread and self._thread.is_alive():
            self._thread.join(timeout=2.0)
        
        self.server = None
        self.logger.info("OSC listener stopped")

    def add_address_handler(self, address: str, callback: callable):
        """Add custom handler for specific OSC address"""
        self.dispatcher.map(address, callback)

    def cleanup(self):
        self.stop()

NODE_CLASSES = [OSCInNode]