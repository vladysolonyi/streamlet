import logging
from pathlib import Path
from .data_bus import DataBus
from .registry import NodeRegistry
from pydantic import ValidationError
from typing import Union, Dict, Any
import json
import threading
import time

class Pipeline:
    def __init__(self, config_source: Union[str, Dict]):
        self._running = threading.Event()
        self._thread = None
        self.nodes = []
        self.data_bus = DataBus()
        self.config = self._load_config(config_source)
        self.logger = logging.getLogger('pipeline')

    def _load_config(self, source: Union[str, Dict]) -> Dict:
        """Load config from file path or dict"""
        if isinstance(source, str):
            config_file = Path(source)
            if not config_file.exists():
                raise FileNotFoundError(f"Config file {source} not found")
            
            if config_file.suffix == '.json':
                with open(config_file) as f:
                    return json.load(f)
            else:
                raise ValueError("Only JSON config files supported")
                
        elif isinstance(source, Dict):
            return source
            
        else:
            raise TypeError("Config must be file path (str) or dict")

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

    def update_node_params(self, node_id: str, new_params: dict):
        node = self.get_node(node_id)
        NodeClass = NodeRegistry.get_class(node.node_type)
        
        try:
            validated = NodeClass.Params(**new_params)
        except ValidationError as e:
            raise InvalidParameters(e.json())
            
        node.config["params"].update(validated.dict())
        node.apply_params()  # Node-specific implementation

    def run(self):
        """Non-blocking execution in background thread"""
        if self._running.is_set():
            return
            
        self._running.set()
        self._thread = threading.Thread(target=self._run_loop)
        self._thread.start()

    def _run_loop(self):
        """Main processing loop for background execution"""
        self.logger.info("Starting pipeline execution")
        try:
            while self._running.is_set():
                for node in self.nodes:
                    if node.should_process():
                        node.process()
                time.sleep(0.001)  # Prevent CPU hogging
        except Exception as e:
            self.logger.error(f"Pipeline failed: {str(e)}")
        finally:
            self.shutdown()

    def shutdown(self):
        """Graceful pipeline termination"""
        if self._running.is_set():
            self.logger.info("Stopping pipeline...")
            self._running.clear()
            self._thread.join(timeout=5)