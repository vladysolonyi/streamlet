from framework.nodes import BaseNode
from pydantic import BaseModel
from framework.data.data_packet import DataPacket
from framework.data.data_types import *

class MathNode(BaseNode):
    node_type = "math_multiply"
    accepted_data_types = {DataType.STREAM, DataType.DERIVED}
    accepted_formats = {DataFormat.NUMERICAL}
    accepted_categories = {DataCategory.ENVIRONMENTAL, DataCategory.GEOSPATIAL}

    class Params(BaseModel):
        multiplier: int = 1

    def __init__(self, config):
        super().__init__(config)
        self.params = self.Params(**config.get('params', {}))
        self.multiplier = self.params.multiplier
        
    def on_data(self, packet: DataPacket):
        """Process validated DataPackets"""
        if not self.validate_input(packet):
            self.logger.warning(f"Rejected incompatible packet: {packet}")
            return

        try:
            result = packet.content * self.multiplier
            
            # Create new packet with processing metadata
            new_packet = self.modify_packet(packet, result)
            self.data_bus.publish(self.outputs[0], new_packet)
        except TypeError as e:
            self.logger.error(f"Invalid data type for math operation: {str(e)}")
        except Exception as e:
            self.logger.error(f"Processing failed: {str(e)}")

NODE_CLASSES = [MathNode]