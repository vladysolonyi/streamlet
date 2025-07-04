from collections import defaultdict
from concurrent.futures import ThreadPoolExecutor
from typing import Any, Callable, Dict
import msgpack
import logging
from framework.data.data_packet import DataPacket

class DataBus:
    def __init__(self, max_workers: int = 10):
        self.subscribers = defaultdict(list)
        self.channels = defaultdict(list)
        self.serializer = msgpack
        self.executor = ThreadPoolExecutor(max_workers=max_workers)
        self.logger = logging.getLogger('databus')
        self.enabled = False  # DataBus starts disabled
        
    def set_enabled(self, enabled: bool):
        """Enable or disable data processing"""
        self.enabled = enabled
        self.logger.info(f"DataBus {'enabled' if enabled else 'disabled'}")
        
    def register_channel(self, channel: str):
        """Create a new data channel"""
        if channel not in self.channels:
            self.channels[channel] = []
        
    def subscribe(self, node: Any, channel: str):
        """Add node subscription to channel"""
        self.subscribers[channel].append(node.on_data)

    def publish(self, channel: str, data: Any):
        """Handle delivery without blocking publisher"""
        # Only process data if DataBus is enabled
        if not self.enabled:
            return
            
        if not self.subscribers[channel]:
            self.logger.debug(f"No subscribers for channel {channel}")
            return
            
        # Process in separate thread to avoid blocking
        self.executor.submit(self._deliver, channel, data)

    def _deliver(self, channel: str, data: Any):
        """Actual delivery logic in worker thread"""
        try:
            # Serialization logic remains
            if isinstance(data, DataPacket):
                packed = self.serializer.packb(data.model_dump(mode='json'))
            else:
                packed = self.serializer.packb(data)

            unpacked = self.serializer.unpackb(packed)
            is_packet = isinstance(unpacked, dict) and 'data_type' in unpacked

            for callback in self.subscribers[channel]:
                try:
                    if is_packet:
                        callback(DataPacket.model_validate(unpacked), channel)
                    else:
                        callback(unpacked, channel)
                except Exception as e:
                    self.logger.error(f"Callback error: {str(e)}", exc_info=True)
        except Exception as e:
            self.logger.error(f"Delivery failed: {str(e)}", exc_info=True)

    def flush(self):
        """Clear all data from channels"""
        self.subscribers.clear()
        self.channels.clear()

    def shutdown(self):
        """Clean up thread pool"""
        self.logger.info("Shutting down DataBus")
        self.enabled = False
        self.executor.shutdown(wait=True)

    def get_channel_stats(self) -> Dict[str, Dict[str, int]]:
        return {
            channel: {'subscribers': len(callbacks)}
            for channel, callbacks in self.subscribers.items()
        }