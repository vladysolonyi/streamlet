from abc import ABCMeta
from typing import Type, Set, Any, Optional, List
from pydantic import BaseModel
from framework.data import *
from framework.core.telemetry import telemetry
from framework.core.decorators import node_telemetry
import uuid
import logging
import time
import re

# Precompiled regex for parameter references
REF_REGEX = re.compile(r"@ref:([\w\.]+)")

# Wrapper for telemetry and node_type autoregistration
class NodeMeta(ABCMeta):
    def __new__(cls, name, bases, namespace, **kwargs):
        # Create the class
        new_class = super().__new__(cls, name, bases, namespace, **kwargs)

        # Register node type if it has one
        if hasattr(new_class, 'node_type'):
            from framework.core.registry import NodeRegistry
            NodeRegistry.register(new_class.node_type, new_class)

        return new_class

# =============== 
# Base Node Class
# ===============
class BaseNode(metaclass=NodeMeta):
    node_type: str  # Node Type
    tags: List[str] = []  # override in subclasses

    # Node Configuration
    accepted_data_types: Set[DataType] = set()  # Allowed data types
    accepted_formats: Set[DataFormat] = set()  # Allowed data formats
    accepted_categories: Set[DataCategory] = set()  # Allowed data categories

    Params: Type[BaseModel] = None

    IS_GENERATOR = False  # Node generates data itself / Waits for data to process
    IS_ASYNC_CAPABLE = False  # Node supports async processing
    MAX_BUFFER_SIZE = 100 # Packet overflow limit


    # Input Configuration
    MIN_INPUTS = 1  # Minimum number of input channels required
    MAX_INPUTS = 1  # Maximum number of input channels allowed
    
    def __init__(self, config):
        self.node_id = f"{self.node_type}_{uuid.uuid4().hex[:6]}"  # Unique node ID
        self.config = config
        self.name = config['name']  # Node name
        self.inputs = config.get('inputs', [])  # Input channels
        self.outputs = config.get('outputs', [])  # Output channels
        self.logger = logging.getLogger(self.node_type)  # Node logger
        self.data_bus = None
        self.telemetry = telemetry

        # Telemetry data
        self.last_processed = time.time()  # Timestamp of last processed packet
        self.rejected_count = 0  # Count of rejected packets
        self.processed_count = 0  # Count of processed packets
        
        # Assign other node's packet values to this node's parameters
        self.references = {}
        self.reference_subscriptions = {}
        self.last_output = None  # Track last output packet
        
        # Initialize references from config
        self._parse_references(config)
        
        # Validate input configuration
        if len(self.inputs) < self.MIN_INPUTS:
            raise ValueError(f"{self.node_type} requires at least {self.MIN_INPUTS} inputs")
        if self.MAX_INPUTS is not None and len(self.inputs) > self.MAX_INPUTS:
            raise ValueError(f"{self.node_type} allows at most {self.MAX_INPUTS} inputs")
            
        # Initialize input storage
        self.input_buffers = {channel: [] for channel in self.inputs}
        
        if self.Params:
            # Create params with proper types for references
            params_data = {}
            for k, v in config.get('params', {}).items():
                if isinstance(v, str) and REF_REGEX.match(v):
                    # Get the expected type from the Params model
                    field = self.Params.model_fields.get(k)
                    if field:
                        # Create type-appropriate placeholder
                        if field.annotation is str:
                            params_data[k] = ""
                        elif field.annotation is int:
                            params_data[k] = 0
                        elif field.annotation is float:
                            params_data[k] = 0.0
                        elif field.annotation is bool:
                            params_data[k] = False
                        else:
                            params_data[k] = None
                    else:
                        params_data[k] = None
                else:
                    params_data[k] = v
            self.params = self.Params(**params_data)
        else:
            self.params = None

    @node_telemetry("on_data")
    def on_data(self, packet: DataPacket, input_channel: str):
        """Handle incoming data with channel information"""
        is_reference = False
        
        # First check if this is a reference we care about
        for param_name, ref_path in self.references.items():
            ref_node_name = ref_path.split('.')[0]
            if input_channel == f"{ref_node_name}_out":
                self._update_reference(param_name, ref_path, packet)
                is_reference = True
        
        # If it's ONLY a reference (not a normal input), stop here
        if is_reference and input_channel not in self.inputs:
            return
            
        # Then handle normal input processing
        if input_channel not in self.input_buffers:
            self.logger.error(f"Unregistered input channel: {input_channel}")
            return
            
        if not self.validate_input(packet):
            self.log_rejection(packet)
            return
            
        # Create packet buffer storage for every input channel
        if len(self.input_buffers[input_channel]) < self.MAX_BUFFER_SIZE:
            self.input_buffers[input_channel].append(packet)
        else:
            self.logger.warning(f"Buffer overflow on {input_channel}, packet dropped")
            self.rejected_count += 1
        
        # Check if we have enough inputs to process
        ready_channels = [ch for ch, buf in self.input_buffers.items() if buf]
        if len(ready_channels) >= self.MIN_INPUTS:
            self.process()
    
    # ==========================
    # Node Referencing Functions
    # ==========================
    # Parse references from config
    def _parse_references(self, config):
        """Find and register parameter references in config"""
        if 'params' not in config:
            return
            
        for param_name, param_value in config['params'].items():
            if isinstance(param_value, str):
                match = REF_REGEX.match(param_value)
                if match:
                    ref_path = match.group(1)
                    self.references[param_name] = ref_path
                    self.logger.debug(f"Registered reference for {param_name}: {ref_path}")

    # Update parameter with reference value
    def _update_reference(self, param_name: str, ref_path: str, packet: DataPacket):
        """Update parameter value with automatic type conversion"""
        try:    
            # Extract value based on reference path
            raw_value = self._extract_value(packet, ref_path)
            if raw_value is None:
                self.logger.warning(f"Reference {ref_path} yielded None for '{param_name}'—"
                                    "did you forget to initialize upstream output?")
            
            # Get expected type from Pydantic model
            field = self.Params.model_fields.get(param_name)
            if not field:
                self.logger.error(f"Parameter {param_name} not found in model")
                return
                
            expected_type = field.annotation
            
            # Convert value to expected type
            value = self._convert_to_type(raw_value, expected_type)
            
            # Update parameter
            if self.params and hasattr(self.params, param_name):
                # Update Pydantic model
                params_dict = self.params.model_dump()
                params_dict[param_name] = value
                self.params = self.Params(**params_dict)
            else:
                # Update config directly
                self.config['params'][param_name] = value
                
            self.logger.debug(f"Updated reference: {param_name} = {value}")
        except Exception as e:
            self.logger.error(f"Reference update failed: {str(e)}")

    # Extract value from incoming packet of the specified reference
    def _extract_value(self, packet: DataPacket, ref_path: str) -> Any:
        """Extract value using dot-notation path"""
        parts = ref_path.split('.')
        ref_node_name = parts[0]
        path_parts = parts[1:] if len(parts) > 1 else []
        
        # If no path specified, return the entire content
        if not path_parts:
            return packet.content
        
        current = packet
        
        try:
            # Process each path segment
            for part in path_parts:
                # Handle special cases first
                if part == 'content':
                    current = current.content
                elif part == 'metadata':
                    current = current.metadata
                # Handle nested attributes
                elif hasattr(current, part):
                    current = getattr(current, part)
                # Handle nested dictionaries
                elif isinstance(current, dict) and part in current:
                    current = current[part]
                # Handle list indices
                elif isinstance(current, list) and part.isdigit():
                    index = int(part)
                    if index < len(current):
                        current = current[index]
                    else:
                        raise IndexError(f"Index {index} out of range")
                else:
                    raise ValueError(f"Invalid path segment: {part}")
                    
            return current
        except Exception as e:
            raise ValueError(
                f"Failed to extract '{ref_path}' from packet {packet!r}: {e}"
            ) from e

    # Try to convert incoming data from the reference node
    def _convert_to_type(self, value: Any, target_type: Type) -> Any:
        """Convert value to target type with smart handling"""
        # If already the correct type, return as-is
        if isinstance(value, target_type):
            return value
            
        # Special handling for common types
        try:
            if target_type is str:
                return str(value)
            elif target_type is int:
                return int(value)
            elif target_type is float:
                return float(value)
            elif target_type is bool:
                return bool(value)
            elif target_type is list:
                return [value] if not isinstance(value, list) else value
            elif target_type is dict:
                return value if isinstance(value, dict) else {"value": value}
            else:
                # Try direct conversion
                return target_type(value)
        except (TypeError, ValueError):
            # Try JSON conversion for complex types
            try:
                if hasattr(target_type, 'model_validate_json'):
                    return target_type.model_validate_json(value)
                elif hasattr(target_type, 'parse_raw'):
                    return target_type.parse_raw(value)
            except:
                self.logger.warning(f"Could not convert {type(value)} to {target_type}")
                return value

    # ====================
    # Validation Functions
    # ====================
    # Validate incoming packets by accepted data types, formats, and categories
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

    # Packet rejection logging
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

    def _default_format(self) -> DataFormat:
        if not self.accepted_formats:
            raise ValueError(f"{self.node_type} requires at least one accepted format")
        return next(iter(self.accepted_formats))

    def _default_category(self) -> DataCategory:
        if not self.accepted_categories:
            raise ValueError(f"{self.node_type} requires at least one accepted category")
        return next(iter(self.accepted_categories))

    # ====================
    # Processing Functions
    # ====================
    # Main processing method - override in child nodes - Use this to process data
    @node_telemetry("process")
    def process(self):
        """
        Main processing method - override in child nodes
        Access packets through self.input_buffers
        """
        # Pass packets through the node by default
        if self.inputs and self.input_buffers[self.inputs[0]]:
            packet = self.input_buffers[self.inputs[0]].pop(0)
            
            self.last_output = packet
            
            for output_channel in self.outputs:
                self.data_bus.publish(output_channel, packet)

    # Used in the pipeline to determine if the node is passive or active
    def should_process(self):
        return self.IS_GENERATOR

    # ========================
    # Node Parameter Functions
    # ========================
    @classmethod
    def get_param_schema(cls):
        return cls.Params.schema() if cls.Params else {"type": "object"}

    # Apply updated parameters
    def apply_params(self):
        """Apply updated parameters immediately"""
        # Default implementation - recreate params object
        if self.Params and hasattr(self, 'config'):
            self.params = self.Params(**self.config.get('params', {}))
        
        # Custom logic for specific nodes
        if hasattr(self, 'on_params_updated'):
            self.on_params_updated()

    # ===================
    # Telemetry Functions
    # ===================
    def emit_telemetry(self, metric: str, value: Any):
        """Non-blocking telemetry emission"""
        try:
            self.telemetry.broadcast_sync({
                "pipeline_id": self.pipeline.id,
                "node_id": self.name,
                "metric": metric,
                "value": value,
                "timestamp": time.time()
            })
        except Exception as e:
            self.logger.error(f"Telemetry error: {str(e)}")

    # =====================
    # Data Packet Functions
    # =====================
    # Create packet (for loader nodes)
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
            data_type=data_type or DataType.DERIVED,
            format=format or self._default_format(),
            category=category or self._default_category(),
            source=DataSource.INTERNAL,
            content=content,
            **overrides
        )

    # Modify incoming packet (for processor nodes)
    def modify_packet(
        self,
        original: DataPacket,
        new_content: Any,
        data_type: DataType = DataType.DERIVED, # Default but overrideable
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

