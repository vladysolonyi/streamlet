from framework.nodes import BaseNode

class NumberGenerator(BaseNode):
    node_type = "number_generator"
    IS_ACTIVE = True  # Actively generates data
    
    def __init__(self, config):
        super().__init__(config)
        self.current = config['params']['start']
        self.step = config['params']['step']
        
    def should_process(self):
        """Generate new numbers continuously"""
        return True
        
    def process(self):
        """Active data generation"""
        self.data_bus.publish(self.outputs[0], self.current)
        self.current += self.step

NODE_CLASSES = [NumberGenerator]