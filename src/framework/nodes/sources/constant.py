import time
from pydantic import BaseModel, Field
from typing import Any, Optional
from framework.core.decorators import node_telemetry
from framework.nodes.base_node import BaseNode
from framework.data.data_types import *
from framework.data.data_packet import DataPacket

class ConstantNode(BaseNode):
    node_type = "constant"
    accepted_data_types = set()
    accepted_formats = set()
    accepted_categories = set()
    IS_GENERATOR = True
    IS_ASYNC_CAPABLE = False
    MIN_INPUTS = 0
    MAX_INPUTS = 0

    class Params(BaseModel):
        value: Any
        send_on_update: bool = Field(default=False, description="Emit only when value updates")

    def __init__(self, config):
        super().__init__(config)
        # Track last emitted value
        self._last_value: Optional[Any] = None
        self._emitted = False

    def _update_reference(self, param_name: str, ref_path: str, packet: DataPacket):
        # Update base params
        super()._update_reference(param_name, ref_path, packet)
        # Reset emission if value changed and send_on_update is enabled
        new_value = self.params.value
        if self.params.send_on_update and new_value is not None and new_value != self._last_value:
            self.logger.info(f"Value updated from {self._last_value} to {new_value}, resetting emitter.")
            self._last_value = new_value
            self._emitted = False

    def should_process(self):
        # If not yet emitted, and (if send_on_update, value must be non-null)
        if not self._emitted:
            if self.params.send_on_update:
                return self.params.value is not None
            return True
        return False

    @node_telemetry("process")
    def process(self):
        # Only emit if value is set
        if self.params.value is None:
            self.logger.debug("Constant value is None, skipping emission.")
            return

        pkt = self.create_packet(
            content=self.params.value,
            data_type=DataType.DERIVED,
            format=(DataFormat.NUMERICAL if isinstance(self.params.value, (int, float)) else DataFormat.TEXTUAL),
            category=DataCategory.GENERIC
        )
        self.data_bus.publish(self.outputs[0], pkt)

        # Mark as emitted and store last value
        self._emitted = True
        self._last_value = self.params.value
        self.last_processed = time.time()

# Register node classes for the pipeline
NODE_CLASSES = [ConstantNode]
