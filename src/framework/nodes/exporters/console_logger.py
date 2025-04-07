# src/framework/nodes/exporters/console_logger.py
from framework.nodes.base_node import BaseNode

class ConsoleLogger(BaseNode):
    """Logs data to console for debugging"""
    node_type = "console_logger"
    
    def on_data(self, data):
        """Handle incoming data"""
        print(f"[LOG] {self.inputs[0]}: {data}")
        self.last_received = data  # For test verification

NODE_CLASSES = [ConsoleLogger]