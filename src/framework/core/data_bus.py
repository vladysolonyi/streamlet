from collections import defaultdict
import msgpack
from typing import Any, Callable, Dict

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
        """Push data to channel with serialization"""
        packed = self.serializer.packb(data)
        for callback in self.subscribers[channel]:
            callback(self.serializer.unpackb(packed))

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