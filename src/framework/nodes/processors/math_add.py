# nodes/processors/math_add.py
from framework.nodes.base_node import BaseNode
from pydantic import BaseModel
from framework.data.data_packet import DataPacket
from framework.data.data_types import *
from framework.core.decorators import node_telemetry

class MathAddNode(BaseNode):
    node_type = "math_add"
    accepted_data_types = set(DataType)
    accepted_formats = {DataFormat.NUMERICAL}
    accepted_categories = set(DataCategory)
    
    # Input configuration
    MIN_INPUTS = 2  # Require exactly 2 inputs
    MAX_INPUTS = 2  # No more than 2 inputs
    
    class Params(BaseModel):
        strict_types: bool = True

    @node_telemetry("process")
    def process(self):
        """Process packets from both inputs"""
        # Get the first packet from each input
        packet1 = self.input_buffers[self.inputs[0]][0] if self.input_buffers[self.inputs[0]] else None
        packet2 = self.input_buffers[self.inputs[1]][0] if self.input_buffers[self.inputs[1]] else None
        
        if not packet1 or not packet2:
            return
            
        try:
            result = packet1.content + packet2.content
            
            # Create new packet using first input as template
            new_packet = self.modify_packet(
                original=packet1,
                new_content=result,
                data_type=DataType.DERIVED
            )
            
            # Send to all outputs
            for output_channel in self.outputs:
                self.data_bus.publish(output_channel, new_packet)
            
        except Exception as e:
            self.logger.error(f"Addition failed: {str(e)}")

# Register the node
NODE_CLASSES = [MathAddNode]