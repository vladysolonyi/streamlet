from abc import ABCMeta
from typing import Type, Optional
from pydantic import BaseModel

class NodeMeta(ABCMeta):
    """Metaclass for auto-registration of signal processing nodes"""
    def __init__(cls, name, bases, attrs):
        super().__init__(name, bases, attrs)
        if hasattr(cls, 'node_type'):
            # Import registry here to avoid circular imports
            from framework.core.registry import NodeRegistry
            NodeRegistry.register(cls.node_type, cls)

class BaseNode(metaclass=NodeMeta):
    node_type: str
    Params: Type[BaseModel] = None  # Define per-node
    IS_ACTIVE = False  # Default to passive node
    
    def __init__(self, config):
        self.config = config
        self.data_bus = None
        self.inputs = config.get('inputs', [])
        self.outputs = config.get('outputs', [])

    @classmethod
    def get_param_schema(cls):
        """Return JSON Schema for node parameters"""
        if cls.Params is None:
            return {"type": "object"}  # Allow any params
        return cls.Params.schema()

    def should_process(self):
        """Override for active nodes that need periodic execution"""
        return self.IS_ACTIVE

    def initialize(self):
        """Hardware/SDR initialization (override in loaders)"""
        pass
        
    def process(self):
        """Main processing method (override in processors)"""
        raise NotImplementedError
        
    def cleanup(self):
        """Resource cleanup (critical for SDR devices)"""
        pass
