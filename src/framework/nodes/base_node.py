from abc import ABCMeta
from typing import Type, Set, Any, Optional
from pydantic import BaseModel
from framework.data import *
from framework.core.telemetry import telemetry
import uuid
import logging
import time
import functools


class NodeMeta(ABCMeta):
    def __new__(cls, name, bases, namespace, **kwargs):
        for method_name in ['process', 'on_data']:
            if method_name in namespace:
                original_method = namespace[method_name]
                
                # Enhanced wrapper with start/end telemetry
                def wrapped(self, *args, 
                           __original_method=original_method,
                           __method_name=method_name,
                           **kwargs):
                    # Emit processing start telemetry
                    self.emit_telemetry(
                        metric="processing_start",
                        value=time.time()
                    )
                    
                    start = time.perf_counter()
                    try:
                        result = __original_method(self, *args, **kwargs)
                    except Exception as e:
                        # Emit error telemetry
                        self.emit_telemetry(
                            metric="processing_error",
                            value=str(e)
                        )
                        raise
                    finally:
                        # Always emit end telemetry
                        duration = time.perf_counter() - start
                        self.emit_telemetry(
                            metric="processing_end",
                            value=time.time()
                        )
                        # Keep execution time telemetry
                        self.emit_telemetry(
                            metric="execution_time",
                            value=duration
                        )
                    
                    return result
                
                namespace[method_name] = wrapped

        # Create class and register
        new_class = super().__new__(cls, name, bases, namespace, **kwargs)
        if hasattr(new_class, 'node_type'):
            from framework.core.registry import NodeRegistry
            NodeRegistry.register(new_class.node_type, new_class)
        return new_class

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
        self.name = config['name']
        self.data_bus = None
        self.inputs = config.get('inputs', [])
        self.outputs = config.get('outputs', [])
        self.logger = logging.getLogger(self.node_type)
        self.telemetry = telemetry
        self.last_processed = time.time()  # Track processing time
        self.rejected_count = 0  # Track rejected packets
        self.processed_count = 0  # Track processed packets

    # In BaseNode class
    def emit_telemetry(self, metric: str, value: Any):
        """Non-blocking telemetry emission"""
        try:
            self.telemetry.broadcast_sync({
                "node_id": self.name,
                "metric": metric,
                "value": value,
                "timestamp": time.time()
            })
        except Exception as e:
            self.logger.error(f"Telemetry error: {str(e)}")

    @classmethod
    def get_param_schema(cls):
        return cls.Params.schema() if cls.Params else {"type": "object"}

    def should_process(self):
        """Override for active nodes that need periodic execution"""
        return self.IS_ACTIVE

    def initialize(self):
        """Hardware/SDR initialization (override in loaders)"""
        pass

    def validate_input(self, packet: DataPacket) -> bool:
        """Check if node can process this data type with telemetry"""
        is_valid = (
            packet.data_type in self.accepted_data_types and
            packet.format in self.accepted_formats and
            packet.category in self.accepted_categories
        )
        
        if not is_valid:
            self.log_rejection(packet)
            self.rejected_count += 1
            self.emit_telemetry(
                metric="data_rejected",
                value={
                    "reason": "incompatible_data",
                    "data_type": str(packet.data_type),
                    "format": str(packet.format),
                    "category": str(packet.category),
                    "current_rejected": self.rejected_count
                }
            )
        
        return is_valid

    def log_rejection(self, packet: DataPacket):
        """Log detailed rejection reasons"""
        rejection_reasons = []
        
        if packet.data_type not in self.accepted_data_types:
            rejection_reasons.append(
                f"data_type {packet.data_type} not in {self.accepted_data_types}"
            )
            
        if packet.format not in self.accepted_formats:
            rejection_reasons.append(
                f"format {packet.format} not in {self.accepted_formats}"
            )
            
        if packet.category not in self.accepted_categories:
            rejection_reasons.append(
                f"category {packet.category} not in {self.accepted_categories}"
            )
            
        self.logger.warning(
            f"Rejected packet: {', '.join(rejection_reasons)}"
        )
        
    def process(self):
        """Main processing method (override in processors)"""
        raise NotImplementedError
        
    def cleanup(self):
        """Resource cleanup (critical for SDR devices)"""
        pass

    def create_packet(
        self,
        content: Any,
        data_type: Optional[DataType] = None,
        format: Optional[DataFormat] = None,
        category: Optional[DataCategory] = None,
        **overrides
    ) -> DataPacket:
        """Create packet with optional manual overrides"""
        return DataPacket(
            data_type=data_type or self._default_data_type(),
            format=format or self._default_format(),
            category=category or self._default_category(),
            source=DataSource.INTERNAL,
            content=content,
            **overrides
        )

    def modify_packet(
        self,
        original: DataPacket,
        new_content: Any,
        data_type: DataType = DataType.DERIVED,  # Default but overrideable
        format: Optional[DataFormat] = None,
        category: Optional[DataCategory] = None,
        **kwargs
    ) -> DataPacket:
        """Create derivative packet with configurable metadata"""
        return original.copy(update={
            "content": new_content,
            "data_type": data_type,
            "format": format or original.format,
            "category": category or original.category,
            "processing_chain": original.processing_chain + [self.node_id],
            **kwargs
        })

    def _default_data_type(self) -> DataType:
        """Infer from IS_ACTIVE flag"""
        return DataType.STREAM if self.IS_ACTIVE else DataType.STATIC

    def _default_format(self) -> DataFormat:
        if not self.accepted_formats:
            raise ValueError(f"{self.node_type} requires at least one accepted format")
        return next(iter(self.accepted_formats))

    def _default_category(self) -> DataCategory:
        if not self.accepted_categories:
            raise ValueError(f"{self.node_type} requires at least one accepted category")
        return next(iter(self.accepted_categories))