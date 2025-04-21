from abc import ABCMeta
from typing import Type, Set, Any, Optional
from pydantic import BaseModel
from framework.data import *
import uuid
import logging

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
    accepted_data_types: Set[DataType] = set()
    accepted_formats: Set[DataFormat] = set()
    accepted_categories: Set[DataCategory] = set()
    Params: Type[BaseModel] = None  # Define per-node
    IS_ACTIVE = False  # Default to passive node
    
    def __init__(self, config):
        self.node_id = f"{self.node_type}_{uuid.uuid4().hex[:6]}" 
        self.config = config
        self.data_bus = None
        self.inputs = config.get('inputs', [])
        self.outputs = config.get('outputs', [])
        self.logger = logging.getLogger(self.node_type)

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

    def validate_input(self, packet: DataPacket) -> bool:
        """Check if node can process this data type"""
        return (packet.data_type in self.accepted_data_types and
                packet.format in self.accepted_formats and
                packet.category in self.accepted_categories)
        
    def process(self):
        """Main processing method (override in processors)"""
        raise NotImplementedError
        
    def cleanup(self):
        """Resource cleanup (critical for SDR devices)"""
        pass

    def create_packet(self, content: Any, **overrides) -> DataPacket:
        """Create DataPacket with node-specific defaults"""
        return DataPacket(
            data_type=self._default_data_type(),
            format=self._default_format(),
            category=self._default_category(),
            source=DataSource.INTERNAL,  # Default for generated data
            content=content,
            **overrides  # Allow per-node overrides
        )

    def modify_packet(
        self,
        original: DataPacket,
        new_content: Any,
        **kwargs
    ) -> DataPacket:
        """Create derivative packet with full processing history"""
        return original.copy(update={
            "content": new_content,
            "data_type": DataType.DERIVED,
            "processing_chain": original.processing_chain + [self.node_id],
            **kwargs
        })

    def _default_data_type(self) -> DataType:
        """Infer from IS_ACTIVE flag"""
        return DataType.STREAM if self.IS_ACTIVE else DataType.STATIC

    def _default_format(self) -> DataFormat:
        return next(iter(self.accepted_formats))  # First accepted format

    def _default_category(self) -> DataCategory:
        return next(iter(self.accepted_categories))
