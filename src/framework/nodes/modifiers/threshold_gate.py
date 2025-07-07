from typing import Literal
from pydantic import BaseModel
from framework.nodes.base_node import BaseNode
from framework.data.data_packet import DataPacket
from framework.data.data_types import DataType, DataFormat, DataCategory

class ThresholdGate(BaseNode):
    node_type = "threshold_gate"
    tags = ["Untested"]
    IS_GENERATOR = False  # Passive processor

    accepted_data_types = {DataType.STREAM, DataType.EVENT}
    accepted_formats = {DataFormat.NUMERICAL}
    accepted_categories = {DataCategory.GENERIC}

    class Params(BaseModel):
        threshold: float = 0.0
        mode: Literal["gt", "lt", "ge", "le", "eq", "ne"] = "gt"

    def __init__(self, config):
        super().__init__(config)
        self.params = self.Params(**config.get("params", {}))

    def on_data(self, packet: DataPacket, input_channel: str):
        try:
            value = packet.content
            if not isinstance(value, (int, float)):
                self.logger.warning(f"Non-numerical content ignored: {value}")
                return

            if self._passes_threshold(value):
                self.publish(packet)
        except Exception as e:
            self.logger.error(f"ThresholdGate error: {e}", exc_info=True)

    def _passes_threshold(self, value: float) -> bool:
        t = self.params.threshold
        mode = self.params.mode
        return {
            "gt": value > t,
            "lt": value < t,
            "ge": value >= t,
            "le": value <= t,
            "eq": value == t,
            "ne": value != t
        }.get(mode, False)

NODE_CLASSES = [ThresholdGate]
