import time
import logging
from typing import List, Dict, Any
from pydantic import BaseModel
from framework.nodes.base_node import BaseNode
from framework.data.data_packet import DataPacket
from framework.data.data_types import *
from framework.core.decorators import node_telemetry

class AccumulatorNode(BaseNode):
    node_type = "accumulator"
    tags = ["data flow"]
    accepted_data_types = {DataType.STREAM, DataType.EVENT}
    accepted_formats = {DataFormat.NUMERICAL, DataFormat.TEXTUAL, DataFormat.BINARY}
    accepted_categories = set(DataCategory)
    IS_GENERATOR = False  # Passive node - only processes when data arrives
    
    class Params(BaseModel):
        flush_by: str = "size"  # "size" or "count"
        chunk_size: int = 1024  # in bytes (for "size" mode)
        packet_count: int = 10  # number of packets (for "count" mode)
        include_metadata: bool = True
        output_format: DataFormat = DataFormat.BINARY
        strict_typing: bool = False

    def __init__(self, config):
        super().__init__(config)
        self.params = self.Params(**config.get('params', {}))
        self.buffer: List[DataPacket] = []
        self.current_size = 0
        self.logger = logging.getLogger('accumulator')
        self.logger.setLevel(logging.DEBUG)
        
        # Validate flush mode
        if self.params.flush_by not in ["size", "count"]:
            self.logger.warning("Invalid flush_by value. Defaulting to 'size'")
            self.params.flush_by = "size"

    @node_telemetry("on_data")
    def on_data(self, packet: DataPacket, input_channel: str):
        """Validate and add incoming data to buffer"""
        try:
            if not self.validate_input(packet):
                self.logger.warning("Rejected incompatible packet from %s: %s", 
                                  input_channel, packet)
                return

            # Content type validation
            if self.params.strict_typing:
                if self.params.output_format == DataFormat.BINARY and not isinstance(packet.content, bytes):
                    raise ValueError(f"Expected bytes for BINARY format, got {type(packet.content)}")
                elif self.params.output_format == DataFormat.NUMERICAL and not isinstance(packet.content, (int, float)):
                    raise ValueError(f"Expected numerical value, got {type(packet.content)}")

            # Add packet to buffer
            self.buffer.append(packet)
            self.current_size += self._get_content_size(packet.content)
            
            self.logger.debug("Buffered packet from %s. Current: %d/%s", 
                            input_channel, 
                            self.current_size if self.params.flush_by == "size" else len(self.buffer),
                            self.params.chunk_size if self.params.flush_by == "size" else self.params.packet_count)

            # Check if we should flush
            should_flush = False
            if self.params.flush_by == "size":
                should_flush = self.current_size >= self.params.chunk_size
            elif self.params.flush_by == "count":
                should_flush = len(self.buffer) >= self.params.packet_count
                
            if should_flush:
                flush_reason = "size" if self.params.flush_by == "size" else "count"
                self.logger.info("%s threshold reached (%s), flushing", 
                               flush_reason.capitalize(),
                               self.current_size if flush_reason == "size" else len(self.buffer))
                self.flush()

        except Exception as e:
            self.logger.error("Buffer error from %s: %s", input_channel, str(e), exc_info=True)

    def flush(self):
        """Emit accumulated data"""
        if not self.buffer:
            self.logger.debug("Flush called with empty buffer")
            return

        try:
            self.logger.debug("Flushing %d packets (%d bytes)", 
                            len(self.buffer), self.current_size)
            
            # Create batch with validation
            batch_content, metadata = self._create_batch()
            if not batch_content:
                self.logger.warning("Empty batch content after processing")
                return

            # Create output packet
            batch_packet = self.create_packet(
                content=batch_content,
                data_type=DataType.DERIVED,
                format=self.params.output_format,
                metadata=metadata if self.params.include_metadata else None,
                lifecycle_state=LifecycleState.PROCESSED
            )
            
            # Publish the batch
            self.data_bus.publish(self.outputs[0], batch_packet)
            self.logger.info("Successfully flushed %d packets (%d bytes)", 
                           len(self.buffer), self.current_size)

        except Exception as e:
            self.logger.error("Flush failed - %s", str(e), exc_info=True)
            self._dump_buffer_for_analysis()
        finally:
            self._reset_buffer()

    def _create_batch(self):
        """Create batch content with type validation"""
        metadata = {
            "count": len(self.buffer),
            "valid_count": 0,
            "start_time": None,
            "end_time": None,
            "source_nodes": set()
        }

        content_blocks = []
        timestamps = []
        
        for packet in self.buffer:
            try:
                # Content validation
                if self.params.output_format == DataFormat.BINARY:
                    if not isinstance(packet.content, bytes):
                        raise ValueError(f"Non-binary content in BINARY mode: {type(packet.content)}")
                    content_blocks.append(packet.content)
                    
                elif self.params.output_format == DataFormat.TEXTUAL:
                    content_blocks.append(str(packet.content))
                    
                elif self.params.output_format == DataFormat.NUMERICAL:
                    if not isinstance(packet.content, (int, float)):
                        raise ValueError(f"Non-numerical value: {packet.content}")
                    content_blocks.append(packet.content)
                
                # Metadata collection
                metadata["valid_count"] += 1
                timestamps.append(packet.timestamp.timestamp())
                metadata["source_nodes"].add(packet.source)
                
            except Exception as e:
                self.logger.warning("Invalid packet in batch: %s", str(e))

        # Finalize metadata
        if timestamps:
            metadata["start_time"] = min(timestamps)
            metadata["end_time"] = max(timestamps)
        metadata["source_nodes"] = list(metadata["source_nodes"])
        
        # Format content based on output format
        if self.params.output_format == DataFormat.BINARY:
            content = b''.join(content_blocks)
        elif self.params.output_format == DataFormat.TEXTUAL:
            content = "\n".join(content_blocks)
        elif self.params.output_format == DataFormat.NUMERICAL:
            content = content_blocks  # List of numbers
        
        return content, metadata

    def _get_content_size(self, content) -> int:
        """Calculate size in bytes for quota tracking"""
        if isinstance(content, bytes):
            return len(content)
        elif isinstance(content, str):
            return len(content.encode())
        return 1  # Count non-binary items as 1 unit

    def _dump_buffer_for_analysis(self):
        """Preserve failed buffer for debugging"""
        dump = [{
            "content_type": type(p.content).__name__,
            "content_sample": str(p.content)[:100],
            "source": p.source,
            "timestamp": p.timestamp.isoformat()
        } for p in self.buffer]
        
        self.logger.debug("Buffer dump:\n%s", dump)

    def _reset_buffer(self):
        """Reset buffer state"""
        prev_count = len(self.buffer)
        self.buffer.clear()
        self.current_size = 0
        self.logger.debug("Buffer reset (cleared %d items)", prev_count)

NODE_CLASSES = [AccumulatorNode]