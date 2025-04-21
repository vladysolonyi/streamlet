from framework.nodes import BaseNode
from pydantic import BaseModel
from framework.data.data_types import *

class NumberGenerator(BaseNode):
    node_type = "number_generator"
    IS_ACTIVE = True  # Actively generates data
    accepted_data_types = {DataType.STREAM}
    accepted_formats = {DataFormat.NUMERICAL}
    accepted_categories = {DataCategory.ENVIRONMENTAL}

    class Params(BaseModel):
        current: int = 0
        step: int = 1

    def __init__(self, config):
        super().__init__(config)
        self.params = self.Params(**config.get('params', {}))
        self.current = self.params.current
        self.step = self.params.step
        self.sequence_id = 0  # Track packet sequence

    def should_process(self):
        return True
        
    def process(self):
        """Generate and publish DataPackets with metadata"""
        packet = self.create_packet(
            content=self.current,
            sequence_id=self.sequence_id,
            lifecycle_state=LifecycleState.RAW
        )
        
        self.data_bus.publish(self.outputs[0], packet)
        self.current += self.params.step
        self.sequence_id += 1

NODE_CLASSES = [NumberGenerator]