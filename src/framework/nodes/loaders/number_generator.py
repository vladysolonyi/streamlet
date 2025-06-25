import time
from framework.nodes import BaseNode
from pydantic import BaseModel
from framework.data.data_types import *
from typing import Union

class NumberGenerator(BaseNode):
    node_type = "number_generator"
    IS_ACTIVE = True
    MIN_INPUTS = 0
    IS_ASYNC_CAPABLE = False

    class Params(BaseModel):
        start_value: float = 0.0
        step_per_frame: float = 1.0
        max_value: Union[float, None] = None  # Use None instead of inf
        wrap_around: bool = False

    def __init__(self, config):
        super().__init__(config)
        self.params = self.Params(**config.get('params', {}))
        self.current = self.params.start_value
        self.sequence_id = 0

    def process(self):
        if not (hasattr(self, 'pipeline')) or not self.pipeline.in_frame:
            return
            
        self.current += self.params.step_per_frame
        
        # Handle max_value logic with None check
        if self.params.max_value is not None and self.current > self.params.max_value:
            if self.params.wrap_around:
                self.current = self.params.start_value
            else:
                self.current = self.params.max_value
        
        packet = self.create_packet(
            data_type=DataType.STREAM,
            format=DataFormat.NUMERICAL,
            category=DataCategory.GENERIC,
            content=self.current,
            sequence_id=self.sequence_id,
            lifecycle_state=LifecycleState.RAW
        )
        
        self.data_bus.publish(self.outputs[0], packet)
        self.last_output = packet
        self.sequence_id += 1

NODE_CLASSES = [NumberGenerator]