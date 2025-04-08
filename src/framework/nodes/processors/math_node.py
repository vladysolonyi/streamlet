from framework.nodes import BaseNode
from pydantic import BaseModel

# framework/nodes/processors/math_node.py
class MathNode(BaseNode):
    node_type = "math_multiply"

    class Params(BaseModel):  # Nested Params model
        multiplier: int = 1
    
    def __init__(self, config):
        super().__init__(config)
        self.params = self.Params(**config.get('params', {}))
        self.multiplier = self.params.multiplier
        
    def on_data(self, data):
        """Called automatically when data arrives"""
        result = data * self.multiplier
        for output in self.outputs:
            self.data_bus.publish(output, result)

NODE_CLASSES = [MathNode]