# src/framework/nodes/exporters/console_logger.py
from framework.nodes.base_node import BaseNode
from pydantic import BaseModel

class ConsoleLogger(BaseNode):
    """Logs data to console for debugging"""
    node_type = "console_logger"
    class Params(BaseModel):  # Nested Params model
        prefix: str = "[LOG]"

    def __init__(self, config):
        super().__init__(config)
        self.params = self.Params(**config.get('params', {}))
        self.pefix = self.params.prefix
    
    def on_data(self, data):
        """Handle incoming data"""
        print(f"{self.pefix} {self.inputs[0]}: {data}")
        self.last_received = data  # For test verification

NODE_CLASSES = [ConsoleLogger]