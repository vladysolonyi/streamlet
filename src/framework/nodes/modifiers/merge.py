from typing import Dict, List
from pydantic import BaseModel
from framework.nodes.base_node import BaseNode
from framework.data.data_packet import DataPacket
from framework.data.data_types import DataType, DataFormat, DataCategory, LifecycleState
import time


class Merge(BaseNode):
    node_type = "merge"
    tags = ["Untested"]
    accepted_data_types = {DataType.STREAM, DataType.EVENT, DataType.DERIVED}
    accepted_formats = {DataFormat.NUMERICAL, DataFormat.TEXTUAL, DataFormat.BINARY}
    accepted_categories = {DataCategory.GENERIC}
    IS_GENERATOR = False

    class Params(BaseModel):
        timeout: float = 2.0  # seconds to wait before giving up on incomplete merge
        output_as: str = "list"  # "list" or "dict"

    def __init__(self, config):
        super().__init__(config)
        self.params = self.Params(**config.get("params", {}))
        self.buffers: Dict[str, DataPacket] = {}
        self.timestamps: Dict[str, float] = {}

    def on_data(self, packet: DataPacket, input_channel: str):
        self.buffers[input_channel] = packet
        self.timestamps[input_channel] = time.time()

        # Remove expired packets
        now = time.time()
        expired = [ch for ch, ts in self.timestamps.items() if now - ts > self.params.timeout]
        for ch in expired:
            self.logger.debug(f"Expired input from {ch}")
            self.buffers.pop(ch, None)
            self.timestamps.pop(ch, None)

        # Wait until we have one from each input
        if all(input_ch in self.buffers for input_ch in self.inputs):
            contents = {
                ch: self.buffers[ch].content for ch in self.inputs
            }

            if self.params.output_as == "list":
                merged_content = [contents[ch] for ch in self.inputs]
            else:
                merged_content = contents  # keep channel names

            merged_packet = self.create_packet(
                content=merged_content,
                data_type=DataType.DERIVED,
                format=self._infer_format(merged_content),
                metadata={},  # optionally merge metadata
                lifecycle_state=LifecycleState.PROCESSED
            )

            self.data_bus.publish(self.outputs[0], merged_packet)

            # Clear all
            self.buffers.clear()
            self.timestamps.clear()

    def _infer_format(self, content):
        if isinstance(content, bytes):
            return DataFormat.BINARY
        elif isinstance(content, (str, list, dict)):
            return DataFormat.TEXTUAL
        elif isinstance(content, (int, float)):
            return DataFormat.NUMERICAL
        return DataFormat.TEXTUAL

NODE_CLASSES = [Merge]
