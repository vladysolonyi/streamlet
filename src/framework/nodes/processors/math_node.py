from framework.nodes import BaseNode

# framework/nodes/processors/math_node.py
class MathNode(BaseNode):
    node_type = "math_multiply"
    
    def __init__(self, config):
        super().__init__(config)
        self.multiplier = config.get('params', {}).get('multiplier', 2)
        
    def on_data(self, data):
        """Called automatically when data arrives"""
        result = data * self.multiplier
        for output in self.outputs:
            self.data_bus.publish(output, result)

NODE_CLASSES = [MathNode]