from framework.nodes import BaseNode
from pydantic import BaseModel

class NumberGenerator(BaseNode):
    node_type = "number_generator"
    IS_ACTIVE = True  # Actively generates data

    class Params(BaseModel):  # Nested Params model
        current: int = 0
        step: int = 1

    def __init__(self, config):
        super().__init__(config)
        # Validate params using Pydantic model
        self.params = self.Params(**config.get('params', {}))
        
        # Access validated parameters
        self.current = self.params.current
        self.step = self.params.step
    def should_process(self):
        """Generate new numbers continuously"""
        return True
        
    def process(self):
        """Active data generation"""
        self.data_bus.publish(self.outputs[0], self.current)
        self.current += self.step

NODE_CLASSES = [NumberGenerator]