# framework/nodes/processors/delay_node.py
import time
import logging
import threading
import queue  # Import the queue module
from pydantic import BaseModel
from framework.nodes.base_node import BaseNode
from framework.data.data_packet import DataPacket
from framework.data.data_types import *

class DelayNode(BaseNode):
    node_type = "delay"
    # Accept all data types including STATIC
    accepted_data_types = set(DataType)  # Accepts all data types
    accepted_formats = set(DataFormat)  # Accepts all formats
    accepted_categories = set(DataCategory)  # Accepts all categories

    class Params(BaseModel):
        delay_ms: int = 1000  # Default delay of 1 second
        max_queue_size: int = 1000  # Maximum packets to buffer
        drop_on_overflow: bool = False  # Whether to drop packets when queue is full

    def __init__(self, config):
        super().__init__(config)
        self.params = self.Params(**config.get('params', {}))
        
        # Thread-safe queue for buffering packets
        self.queue = queue.Queue(maxsize=self.params.max_queue_size)
        
        # Worker thread for delayed processing
        self.worker_thread = threading.Thread(target=self._process_queue)
        self.worker_thread.daemon = True
        self.running = True
        self.worker_thread.start()
        
        self.logger = logging.getLogger('delay_node')
        self.logger.info(f"Delay node initialized with {self.params.delay_ms}ms delay")

    def on_data(self, packet: DataPacket):
        """Receive packets and add to delay queue"""
        if not self.validate_input(packet):
            self.logger.warning(f"Rejected incompatible packet: {packet}")
            return

        try:
            # Add packet to queue with timestamp
            self.queue.put((time.monotonic(), packet), block=not self.params.drop_on_overflow)
            self.emit_telemetry("queue_size", self.queue.qsize())
        except queue.Full:
            self.logger.warning("Queue full - packet dropped")
            self.emit_telemetry("dropped_packets", 1)

    def _process_queue(self):
        """Worker thread that processes the queue with delays"""
        while self.running:
            try:
                # Get next packet with timeout
                enqueue_time, packet = self.queue.get(timeout=0.1)
                
                # Calculate remaining delay
                elapsed = (time.monotonic() - enqueue_time) * 1000
                remaining_delay = max(0, self.params.delay_ms - elapsed)
                
                # Sleep for remaining delay
                if remaining_delay > 0:
                    time.sleep(remaining_delay / 1000)
                
                # Forward the packet
                self.data_bus.publish(self.outputs[0], packet)
                self.emit_telemetry("processed_packets", 1)
                
            except queue.Empty:
                # Normal when queue is empty
                continue
            except Exception as e:
                self.logger.error(f"Queue processing error: {str(e)}")

    def cleanup(self):
        """Graceful shutdown"""
        self.running = False
        if self.worker_thread.is_alive():
            self.worker_thread.join(timeout=2.0)
        
        # Clear queue on shutdown
        while not self.queue.empty():
            try:
                self.queue.get_nowait()
            except queue.Empty:
                break
                
        self.logger.info("Delay node shutdown complete")

# Register the node
NODE_CLASSES = [DelayNode]