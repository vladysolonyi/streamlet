from abc import ABCMeta
from typing import Type, Set, Any, Optional, Dict, List
from pydantic import BaseModel
from framework.data import *
from framework.core.telemetry import telemetry
import uuid
import logging
import time
import re


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
    Params: Type[BaseModel] = None
    IS_ACTIVE = False
    IS_ASYNC_CAPABLE = False
    REF_PATTERN = r"@ref:([\w\.]+)"
    # Input configuration (set in child nodes)
    MIN_INPUTS = 1  # Minimum number of input channels required
    MAX_INPUTS = 1  # Maximum number of input channels allowed
    
    def __init__(self, config):
        self.node_id = f"{self.node_type}_{uuid.uuid4().hex[:6]}" 
        self.config = config
        self.name = config['name']
        self.data_bus = None
        self.inputs = config.get('inputs', [])
        self.outputs = config.get('outputs', [])
        self.logger = logging.getLogger(self.node_type)
        self.telemetry = telemetry
        self.last_processed = time.time()
        self.rejected_count = 0
        self.processed_count = 0
        
        # Node references for dynamic parameters
        self.references = {}
        self.reference_subscriptions = {}
        self.reference_cache = {}  # Cache for reference values
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
                if isinstance(v, str) and re.match(self.REF_PATTERN, v):
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

    # NEW METHODS FOR REFERENCE RESOLUTION
    def resolve_references(self, value: Any) -> Any:
        """Resolve references in a string value"""
        if not isinstance(value, str):
            return value
            
        # Find all references in the string
        matches = re.findall(self.REF_PATTERN, value)
        if not matches:
            return value
            
        # Replace each reference with its current value
        for ref_path in matches:
            try:
                # Get the referenced value
                ref_value = self._get_reference_value(ref_path)
                
                # Replace the reference pattern with the actual value
                value = value.replace(f"@ref:{ref_path}", str(ref_value))
            except Exception as e:
                self.logger.error(f"Reference resolution failed for {ref_path}: {str(e)}")
                
        return value

    def _get_reference_value(self, ref_path: str) -> Any:
        """Get the current value of a reference"""
        # Return cached value if available
        if ref_path in self.reference_cache:
            return self.reference_cache[ref_path]
            
        # Extract node name and path
        parts = ref_path.split('.')
        ref_node_name = parts[0]
        path_parts = parts[1:] if len(parts) > 1 else []
        
        # Find the referenced node
        if not hasattr(self, 'pipeline') or not self.pipeline:
            raise RuntimeError("Node not attached to a pipeline")
            
        ref_node = self.pipeline.node_map.get(ref_node_name)
        if not ref_node:
            raise ValueError(f"Referenced node '{ref_node_name}' not found")
            
        # Get the value from the node's last output
        if not hasattr(ref_node, 'last_output'):
            raise ValueError(f"Node '{ref_node_name}' has no output history")
            
        packet = ref_node.last_output
        if not packet:
            raise ValueError(f"Node '{ref_node_name}' has no output yet")
            
        # Extract value using dot-notation path
        current = packet
        for part in path_parts:
            if hasattr(current, part):
                current = getattr(current, part)
            elif isinstance(current, dict) and part in current:
                current = current[part]
            elif isinstance(current, list) and part.isdigit():
                index = int(part)
                current = current[index] if index < len(current) else None
            else:
                raise ValueError(f"Invalid path segment: {part}")
                
            if current is None:
                break
                
        # Cache the value
        self.reference_cache[ref_path] = current
        return current

    def clear_reference_cache(self):
        """Clear cached reference values"""
        self.reference_cache = {}
    # END OF NEW METHODS

    def apply_params(self):
        """Apply updated parameters immediately"""
        # Default implementation - recreate params object
        if self.Params and hasattr(self, 'config'):
            self.params = self.Params(**self.config.get('params', {}))
        
        # Clear reference cache when parameters are updated
        self.clear_reference_cache()
        
        # Custom logic for specific nodes
        if hasattr(self, 'on_params_updated'):
            self.on_params_updated()

    def _update_reference(self, param_name: str, ref_path: str, packet: DataPacket):
        """Update parameter value with automatic type conversion"""
        try:
            # Clear cache for this reference path
            if ref_path in self.reference_cache:
                del self.reference_cache[ref_path]
                
            # Extract value based on reference path
            raw_value = self._extract_value(packet, ref_path)
            
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

    def _parse_references(self, config):
        """Find and register parameter references in config"""
        if 'params' not in config:
            return
            
        for param_name, param_value in config['params'].items():
            if isinstance(param_value, str):
                match = re.match(self.REF_PATTERN, param_value)
                if match:
                    ref_path = match.group(1)
                    self.references[param_name] = ref_path
                    self.logger.debug(f"Registered reference for {param_name}: {ref_path}")

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
            
        # Store packet in buffer with size limit
        MAX_BUFFER_SIZE = 100
        if len(self.input_buffers[input_channel]) < MAX_BUFFER_SIZE:
            self.input_buffers[input_channel].append(packet)
        else:
            self.logger.warning(f"Buffer overflow on {input_channel}, packet dropped")
            self.rejected_count += 1
        
        # Check if we have enough inputs to process
        ready_channels = [ch for ch, buf in self.input_buffers.items() if buf]
        if len(ready_channels) >= self.MIN_INPUTS:
            self.process()


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
            self.logger.error(f"Value extraction failed: {str(e)}")
            raise

    # In BaseNode class
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

    @classmethod
    def get_param_schema(cls):
        return cls.Params.schema() if cls.Params else {"type": "object"}

    def should_process(self):
        """Override for active nodes that need periodic execution"""
        return self.IS_ACTIVE


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
        """
        Main processing method - override in child nodes
        Access packets through self.input_buffers
        """
        # Default implementation processes first input and removes packet
        if self.inputs and self.input_buffers[self.inputs[0]]:
            # Get and remove the first packet
            packet = self.input_buffers[self.inputs[0]].pop(0)
            
            # Store as last output for reference access
            self.last_output = packet
            
            for output_channel in self.outputs:
                self.data_bus.publish(output_channel, packet)

    def _init_references(self, config):
        """Parse and initialize node references from config"""
        if 'references' in config:
            for param_name, ref_config in config['references'].items():
                if 'node' in ref_config:
                    self.references[param_name] = ref_config
                    
    def register_reference(self, param_name: str, node_name: str, data_path: str = None):
        """Register a reference to another node's output"""
        self.references[param_name] = {
            'node': node_name,
            'data_path': data_path
        }
        
    def on_reference_update(self, param_name: str, value: Any):
        """Handle updated value from referenced node"""
        # Update parameter value
        if self.params and hasattr(self.params, param_name):
            # Create updated params object
            params_dict = self.params.dict()
            params_dict[param_name] = value
            self.params = self.params.__class__(**params_dict)
        else:
            # Update config directly for non-Params nodes
            self.config['params'][param_name] = value
            
        self.logger.debug(f"Updated parameter '{param_name}' to {value}")


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