import random
import logging
from pydantic import BaseModel, Field
from framework.core.decorators import node_telemetry
from framework.nodes.base_node import BaseNode
from framework.data.data_packet import DataPacket
from framework.data.data_types import DataType, DataFormat, DataCategory

class RandomNumberNode(BaseNode):
    node_type = "random_number"
    tags = ["loader", "random"]
    # Trigger only on EVENT packets, but wait for multiple inputs
    accepted_data_types = {DataType.EVENT}
    accepted_formats = set(DataFormat)
    accepted_categories = set(DataCategory)
    IS_GENERATOR = False
    IS_ASYNC_CAPABLE = False
    MIN_INPUTS = 1
    MAX_INPUTS = 1

    class Params(BaseModel):
        min_value: float = Field(0.0, description="Inclusive lower bound")
        max_value: float = Field(1.0, description="Inclusive upper bound")

    def __init__(self, config):
        super().__init__(config)
        self.params = self.Params(**config.get("params", {}))
        self.logger = logging.getLogger(self.node_type)
        self.last_output = 1
        # Track which inputs have triggered
        self._triggers = set()

    @node_telemetry("on_data")
    def on_data(self, packet: DataPacket, input_channel: str):
        # Only respond to EVENT packets on registered inputs
        if packet.data_type != DataType.EVENT or input_channel not in self.inputs:
            return

        # Mark this channel as having triggered
        self._triggers.add(input_channel)
        self.logger.debug(f"Trigger received from {input_channel}: {self._triggers}")

        # If we've received triggers from at least MIN_INPUTS channels, fire
        if len(self._triggers) >= self.MIN_INPUTS:
            try:
                value = random.uniform(self.params.min_value, self.params.max_value)
            except Exception as e:
                self.logger.error(f"Random generation error: {e}")
                self._triggers.clear()
                return

            out_pkt = self.create_packet(
                content=int(value),
                data_type=DataType.DERIVED,
                format=DataFormat.NUMERICAL,
                category=DataCategory.GENERIC
            )
            self.data_bus.publish(self.outputs[0], out_pkt)
            self.logger.info(f"Emitted random value {value} after triggers {self._triggers}")
            self.last_output = out_pkt.content
            # Reset for next round
            self._triggers.clear()

# Register node classes for the pipeline
NODE_CLASSES = [RandomNumberNode]
