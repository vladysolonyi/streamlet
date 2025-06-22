import logging
from pathlib import Path
from .data_bus import DataBus
from .registry import NodeRegistry
from pydantic import ValidationError
from typing import Union, Dict, Any
import json
import threading
import time
import copy

class Pipeline:
    def __init__(self, config_source: Union[str, Dict], pipeline_id: str):
        self.id = pipeline_id
        self._running = threading.Event()
        self._thread = None
        self.nodes = []
        self.data_bus = DataBus(max_workers=20)
        self.config = self._load_config(config_source)
        self.logger = logging.getLogger('pipeline')
        self.logger.setLevel(logging.DEBUG)
        self.node_map = {}
        self._config_lock = threading.RLock()
        self._build_lock = threading.Lock()

    def shutdown(self):
        """Safe thread termination with ownership check"""
        if self._running.is_set():
            self.logger.info(f"Shutting down pipeline {self.id}")
            self._running.clear()
            
            # Save thread reference before clearing
            pipeline_thread = self._thread
            
            # Clear thread reference early to avoid race conditions
            self._thread = None
            
            # Now work with the saved thread reference
            if pipeline_thread and pipeline_thread != threading.current_thread():
                try:
                    self.logger.info("Waiting for pipeline thread to finish...")
                    pipeline_thread.join(timeout=5)
                    if pipeline_thread.is_alive():
                        self.logger.warning("Pipeline thread did not terminate in time")
                except RuntimeError as e:
                    self.logger.error(f"Error joining thread: {str(e)}")
        
        self.logger.info("Cleaning up nodes...")
        # Clean up all nodes
        for node in self.nodes:
            try:
                # Stop async nodes properly
                if node.IS_ASYNC_CAPABLE and hasattr(node, 'stop'):
                    node.stop()
                    
                if hasattr(node, 'cleanup'):
                    node.cleanup()
            except Exception as e:
                self.logger.error(f"Error cleaning up {node.name}: {str(e)}")
        
        # Shutdown databus if it exists
        if hasattr(self, 'data_bus') and self.data_bus:
            self.data_bus.shutdown()
            self.logger.debug("DataBus shutdown complete")
        
        self.logger.info("Pipeline shutdown completed")

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
        with self._build_lock:
            # Clear existing nodes and node map
            self.nodes = []
            self.node_map = {}
            
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

            # Third pass: initialize input buffers
            for node in self.nodes:
                # Initialize input buffers with actual channel names
                node.input_buffers = {}
                for input_channel in node.inputs:
                    node.input_buffers[input_channel] = []

            # Fourth pass: setup reference subscriptions
            for node in self.nodes:
                self._setup_reference_subscriptions(node)

            self.logger.debug("Pipeline construction completed")

    def _setup_reference_subscriptions(self, node):
        """Subscribe to reference nodes for dynamic parameters"""
        if not hasattr(node, 'references') or not node.references:
            return
            
        for param_name, ref_path in node.references.items():
            ref_node_name = ref_path.split('.')[0]
            
            if ref_node_name not in self.node_map:
                raise ValueError(f"Referenced node '{ref_node_name}' not found "
                                 f"for parameter '{param_name}' in node '{node.name}'")
                
            ref_channel = f"{ref_node_name}_out"
            
            # Subscribe to the reference channel
            self.data_bus.subscribe(node, ref_channel)
            node.logger.debug(f"Subscribed to reference: {ref_node_name} for {param_name}")

    def update_config(self, new_config: dict):
        """Update pipeline configuration"""
        with self._config_lock:
            # Preserve node states if possible
            node_states = {}
            for node in self.nodes:
                if hasattr(node, 'save_state'):
                    node_states[node.name] = node.save_state()
            
            # Stop and clean up current pipeline
            self.shutdown()
            
            # Create a new DataBus instance
            self.data_bus = DataBus(max_workers=20)
            self.logger.debug("Created new DataBus instance")
            
            # Clear existing nodes and node map
            self.nodes = []
            self.node_map = {}
            
            # Update configuration
            self.config = new_config
            
            # Rebuild pipeline
            self.build()
            
            # Restore node states
            for node in self.nodes:
                if node.name in node_states:
                    node.restore_state(node_states[node.name])
                    
            # Restart if was running
            if self._running.is_set():
                self.run()
    
    def update_node_params(self, node_id: str, new_params: dict):
        """Update parameters for a specific node"""
        with self._config_lock:
            node = self.get_node(node_id)
            if not node:
                raise ValueError(f"Node {node_id} not found")
            
            # Update node parameters
            NodeClass = NodeRegistry.get_class(node.node_type)
            
            try:
                # Update in-memory parameters
                if hasattr(node, 'params'):
                    validated = NodeClass.Params(**new_params)
                    node.params = validated
                
                # Update config for persistence
                for node_config in self.config['nodes']:
                    if node_config['name'] == node_id:
                        node_config['params'] = new_params
                        break
                
                # Apply changes immediately
                if hasattr(node, 'apply_params'):
                    node.apply_params()
                
                return True
            except ValidationError as e:
                self.logger.error(f"Invalid parameters for {node_id}: {str(e)}")
                return False

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
                # Process active nodes only
                for node in self.nodes:
                    try:
                        if node.should_process() and not node.IS_ASYNC_CAPABLE:
                            node.process()
                    except Exception as e:
                        self.logger.error(f"Error processing node {node.name}: {str(e)}")
                
                # Short sleep to prevent CPU hogging
                time.sleep(0.001)
                
        except Exception as e:
            self.logger.error(f"Pipeline failed: {str(e)}", exc_info=True)
        finally:
            self.logger.info("Pipeline run loop exiting")