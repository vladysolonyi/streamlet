import time
from pydantic import BaseModel
from typing import Any
from framework.core.decorators import node_telemetry
from framework.nodes.base_node import BaseNode
from framework.data.data_types import *
from framework.data.data_packet import DataPacket


class ConstantNode(BaseNode):
    node_type = "constant"
    accepted_data_types = set()          # No inputs
    accepted_formats = set()
    accepted_categories = set()
    IS_GENERATOR = True                  # Generates its own data
    IS_ASYNC_CAPABLE = False
    MIN_INPUTS = 0
    MAX_INPUTS = 0

    class Params(BaseModel):
        value: Any       

    def __init__(self, config):
        super().__init__(config)
        # One-time emission flag
        self._emitted = False

    def should_process(self):
        # Emit only once
        return not self._emitted

    @node_telemetry("process")
    def process(self):
        # Create and publish the constant packet
        pkt = self.create_packet(
            content=self.params.value,
            data_type=DataType.DERIVED,
            format=DataFormat.NUMERICAL,
            category=DataCategory.GENERIC
        )
        self.data_bus.publish(self.outputs[0], pkt)
        self._emitted = True
        # Record timestamp
        self.last_processed = time.time()

# Register node classes for the pipeline
NODE_CLASSES = [ConstantNode]