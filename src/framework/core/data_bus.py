from collections import defaultdict
import msgpack
from typing import Any, Callable, Dict
from framework.data.data_packet import DataPacket

class DataBus:
    def __init__(self):
        self.channels = defaultdict(list)
        self.subscribers = defaultdict(list)
        self.serializer = msgpack

    def register_channel(self, channel: str):
        """Create a new data channel"""
        if channel not in self.channels:
            self.channels[channel] = []

    def subscribe(self, node: Any, channel: str):
        """Add node subscription to channel"""
        self.subscribers[channel].append(node.on_data)

    def publish(self, channel: str, data: Any):
        """Handle serialization transparently"""
        # Serialize
        if isinstance(data, DataPacket):
            packed = self.serializer.packb(data.model_dump(mode='json'))
        else:
            packed = self.serializer.packb(data)

        # Deserialize for subscribers
        unpacked = self.serializer.unpackb(packed)
        is_packet = isinstance(unpacked, dict) and 'data_type' in unpacked

        for callback in self.subscribers[channel]:
            if is_packet:
                callback(DataPacket.model_validate(unpacked))
            else:
                callback(unpacked)

    def flush(self):
        for ch in self.channels:
            self.channels[ch].clear()
        self.subscribers.clear()

    def get_channel_stats(self) -> Dict[str, Dict[str, int]]:
        return {
            channel: {
                'subscribers': len(self.subscribers.get(channel, [])),
                'messages': len(self.channels.get(channel, []))
            }
            for channel in set(self.channels.keys()).union(self.subscribers.keys())
        }