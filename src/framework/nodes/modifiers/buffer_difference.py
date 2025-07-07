import logging
from typing import Optional
from pydantic import BaseModel
from framework.nodes.base_node import BaseNode
from framework.data.data_packet import DataPacket
from framework.data.data_types import DataType, DataFormat, DataCategory, LifecycleState
from framework.core.decorators import node_telemetry

class BufferDifferenceNode(BaseNode):
    node_type = "buffer_difference"
    tags = ["math"]
    accepted_data_types = {DataType.STREAM, DataType.EVENT, DataType.DERIVED}
    accepted_formats = {DataFormat.NUMERICAL}
    accepted_categories = {DataCategory.GENERIC}
    IS_GENERATOR = False
    MIN_INPUTS = 1
    MAX_INPUTS = 1

    class Params(BaseModel):
        # No parameters needed currently, but keeping for future extensions
        pass

    def __init__(self, config):
        super().__init__(config)
        self.logger = logging.getLogger(self.node_type)
        self._last_value: Optional[float] = None

    @node_telemetry("on_data")
    def on_data(self, packet: DataPacket, input_channel: str):
        # Validate input
        if not self.validate_input(packet):
            return

        # Extract numeric value
        try:
            current = float(packet.content)
        except (ValueError, TypeError):
            self.logger.warning(f"Non-numeric content ignored: {packet.content}")
            return

        # If we have a previous value, compute difference
        if self._last_value is not None:
            diff = current - self._last_value
            out_pkt = self.create_packet(
                content=diff,
                data_type=DataType.DERIVED,
                format=DataFormat.NUMERICAL,
                category=DataCategory.GENERIC,
                lifecycle_state=LifecycleState.PROCESSED
            )
            self.data_bus.publish(self.outputs[0], out_pkt)
            self.logger.debug(f"Emitted difference: {diff} (current={current}, last={self._last_value})")
        else:
            self.logger.debug(f"No previous value, storing current={current}")

        # Update last value
        self._last_value = current

NODE_CLASSES = [BufferDifferenceNode]
