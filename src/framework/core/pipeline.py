import logging
from pathlib import Path
from typing import Dict, List
from .data_bus import DataBus
from .registry import NodeRegistry

class Pipeline:
    def __init__(self, config_path: str):
        self.nodes = []
        self.data_bus = DataBus()
        self.config = self._load_config(config_path)
        self.logger = logging.getLogger('pipeline')

    def _load_config(self, config_path: str) -> Dict:
        """Load pipeline configuration from YAML/JSON"""
        config_file = Path(config_path)
        if not config_file.exists():
            raise FileNotFoundError(f"Pipeline config {config_path} not found")
        
        # Add support for both YAML and JSON
        if config_file.suffix == '.yaml':
            import yaml
            return yaml.safe_load(config_file.read_text())
        elif config_file.suffix == '.json':
            import json
            return json.loads(config_file.read_text())
        else:
            raise ValueError("Unsupported config format")

    def build(self):
        """Instantiate and connect nodes"""
        self.logger.info("Building pipeline with %d nodes", len(self.config['nodes']))
        
        for node_config in self.config['nodes']:
            # Create node with only type and params
            node = NodeRegistry.create(
                node_type=node_config['type'],
                config=node_config  # Pass full node config
            )
            
            # Set connection parameters AFTER creation
            node.inputs = node_config.get('inputs', [])
            node.outputs = node_config.get('outputs', [])
            node.data_bus = self.data_bus
            self.nodes.append(node)
            
            # Connect to data bus
            for channel in node.inputs:
                self.data_bus.subscribe(node, channel)
            for channel in node.outputs:
                self.data_bus.register_channel(channel)

        self.logger.debug("Pipeline construction completed")

    def run(self):
        """Execute the processing pipeline"""
        self.logger.info("Starting pipeline execution")
        try:
            while True:  # Main processing loop
                # Only process active nodes that generate data
                for node in self.nodes:
                    if node.should_process():
                        node.process()
        except KeyboardInterrupt:
            self.logger.info("Pipeline execution interrupted")
        finally:
            self.shutdown()

    def shutdown(self):
        """Cleanup resources"""
        self.logger.info("Shutting down pipeline")
        for node in self.nodes:
            node.cleanup()
        self.data_bus.flush()