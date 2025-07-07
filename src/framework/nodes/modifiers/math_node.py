# nodes/processors/math_multiply.py
from framework.nodes.base_node import BaseNode
from pydantic import BaseModel
from framework.data.data_packet import DataPacket
from framework.data.data_types import *

class MathMultiplyNode(BaseNode):
    node_type = "math_multiply"
    tags = ["math"]
    accepted_data_types = {DataType.STREAM, DataType.DERIVED, DataType.STATIC}
    accepted_formats = {DataFormat.NUMERICAL}
    accepted_categories = set(DataCategory)
    
    # Input configuration (defaults to single input)
    # MIN_INPUTS = 1 (default)
    # MAX_INPUTS = 1 (default)

    class Params(BaseModel):
        multiplier: int = 1

    def process(self):
        """Process single input"""
        if not self.input_buffers[self.inputs[0]]:
            return
            
        packet = self.input_buffers[self.inputs[0]][0]
        
        try:
            result = packet.content * self.params.multiplier
            
            # Create new packet with processing metadata
            new_packet = self.modify_packet(packet, result)
            
            # Publish to all outputs
            for output_channel in self.outputs:
                self.data_bus.publish(output_channel, new_packet)
                
        except Exception as e:
            self.logger.error(f"Multiplication failed: {str(e)}")

# Register the node
NODE_CLASSES = [MathMultiplyNode]