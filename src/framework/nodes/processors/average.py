from typing import List, Optional
from pydantic import BaseModel
from framework.nodes.base_node import BaseNode
from framework.data.data_packet import DataPacket
from framework.data.data_types import DataType, DataFormat, DataCategory, LifecycleState


class Average(BaseNode):
    node_type = "average"
    accepted_data_types = {DataType.STREAM, DataType.EVENT}
    accepted_formats = {DataFormat.NUMERICAL}
    accepted_categories = {DataCategory.GENERIC}
    IS_GENERATOR = False  # passive node

    class Params(BaseModel):
        window_size: int = 10  # how many values to keep in memory

    def __init__(self, config):
        super().__init__(config)
        self.params = self.Params(**config.get("params", {}))
        self.values: List[float] = []

    def on_data(self, packet: DataPacket, input_channel: str):
        try:
            value = float(packet.content)
        except (ValueError, TypeError):
            self.logger.warning("Non-numeric input received: %s", packet.content)
            return

        self.values.append(value)
        if len(self.values) > self.params.window_size:
            self.values.pop(0)

        avg = sum(self.values) / len(self.values)

        out_packet = self.create_packet(
            content=avg,
            data_type=DataType.DERIVED,
            format=DataFormat.NUMERICAL,
            category=DataCategory.GENERIC,
            lifecycle_state=LifecycleState.PROCESSED
        )
        self.data_bus.publish(self.outputs[0], out_packet)


NODE_CLASSES = [Average]
