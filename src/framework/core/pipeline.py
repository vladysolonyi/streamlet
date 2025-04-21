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
        self.node_map = {}  # Maps node names to instances

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
        """Instantiate and connect nodes using declarative names"""
        self.logger.info("Building pipeline with %d nodes", len(self.config['nodes']))
        
        # First pass: create all nodes
        for node_config in self.config['nodes']:
            if 'name' not in node_config:
                raise ValueError("All nodes must have a 'name' field")
                
            node_name = node_config['name']
            if node_name in self.node_map:
                raise ValueError(f"Duplicate node name: {node_name}")
            
            node = NodeRegistry.create(
                node_type=node_config['type'],
                config=node_config
            )
            node.data_bus = self.data_bus
            self.nodes.append(node)
            self.node_map[node_name] = node

        # Second pass: connect nodes by name
        for node in self.nodes:
            node_name = node.config['name']
            
            # Auto-create output channel
            output_channel = f"{node_name}_out"
            node.outputs = [output_channel]
            self.data_bus.register_channel(output_channel)
            
            # Resolve inputs to upstream outputs
            node.inputs = []
            for input_ref in node.config.get('inputs', []):
                if input_ref not in self.node_map:
                    raise ValueError(f"Unknown input reference '{input_ref}' "
                                   f"for node '{node_name}'")
                
                upstream_channel = f"{input_ref}_out"
                self.data_bus.subscribe(node, upstream_channel)
                node.inputs.append(upstream_channel)

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
        """Safe thread termination with ownership check"""
        if self._running.is_set():
            self._running.clear()
            if self._thread is not None and self._thread is not threading.current_thread():
                self._thread.join(timeout=5)
            self._thread = None