import logging
import time
from pydantic import BaseModel, Field
from typing import Any, Optional
from framework.core.decorators import node_telemetry
from framework.nodes.base_node import BaseNode
from framework.data.data_packet import DataPacket
from framework.data.data_types import DataType, DataFormat, DataCategory

class PassOnChangeNode(BaseNode):
    node_type = "pass_on_change"
    accepted_data_types = {DataType.STREAM, DataType.EVENT, DataType.DERIVED}
    accepted_formats = {DataFormat.NUMERICAL, DataFormat.TEXTUAL, DataFormat.JSON}
    accepted_categories = set(DataCategory)
    IS_GENERATOR = False
    IS_ASYNC_CAPABLE = False
    MIN_INPUTS = 1
    MAX_INPUTS = 1

    class Params(BaseModel):
        on_change_only: bool = Field(default=True, description="Emit only when value differs from last")
        key_path: Optional[str] = Field(default=None, description="Dot path into content dict to watch")

    def __init__(self, config):
        super().__init__(config)
        self.params = self.Params(**config.get('params', {}))
        self.logger = logging.getLogger(self.node_type)
        self._last_value: Optional[Any] = None

    @node_telemetry("on_data")
    def on_data(self, packet: DataPacket, input_channel: str):
        # Extract value to compare
        value = packet.content
        if self.params.key_path and isinstance(packet.content, dict):
            try:
                # Traverse nested dict via dot syntax
                parts = self.params.key_path.split('.')
                v = packet.content
                for p in parts:
                    v = v.get(p, None)
                value = v
            except Exception:
                self.logger.warning(f"Failed to extract key_path '{self.params.key_path}'")
                value = packet.content

        # Decide to emit
        changed = (self._last_value is None) or (value != self._last_value)
        self.logger.debug(f"ValueChange check: last={self._last_value}, new={value}, changed={changed}")
        if self.params.on_change_only and not changed:
            return

        # Update last and publish original packet
        self._last_value = value
        self.data_bus.publish(self.outputs[0], packet)
        self.last_processed = time.time()

NODE_CLASSES = [PassOnChangeNode]
