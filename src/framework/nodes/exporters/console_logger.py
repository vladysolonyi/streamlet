# nodes/exporters/console_logger.py
from framework.nodes.base_node import BaseNode
from pydantic import BaseModel
from framework.data.data_types import *
from framework.core.decorators import node_telemetry

class ConsoleLogger(BaseNode):
    node_type = "console_logger"
    accepted_data_types = set(DataType)
    accepted_formats = set(DataFormat)
    accepted_categories = set(DataCategory)
    IS_ASYNC_CAPABLE = False
    IS_GENERATOR = False
    
    class Params(BaseModel):
        prefix: str = "[LOG]"

    @node_telemetry("process")
    def process(self):
        """Log the first packet from the first input"""
        input_channel = self.inputs[0]
        
        if self.input_buffers[input_channel]:
            while self.input_buffers[input_channel]:
                packet = self.input_buffers[input_channel][0]  # Peek first                
                print(f"{self.params.prefix} {packet}")
                self.input_buffers[input_channel].pop(0)
# Register the node
NODE_CLASSES = [ConsoleLogger]