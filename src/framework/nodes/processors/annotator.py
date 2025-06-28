from typing import Any, Dict
from pydantic import BaseModel
from framework.nodes.base_node import BaseNode
from framework.data.data_packet import DataPacket
from framework.data.data_types import DataType, DataFormat, DataCategory, LifecycleState


class Annotator(BaseNode):
    node_type = "annotator"
    accepted_data_types = {DataType.STREAM, DataType.EVENT, DataType.DERIVED}
    accepted_formats = {DataFormat.NUMERICAL, DataFormat.TEXTUAL, DataFormat.BINARY, DataFormat.JSON}
    accepted_categories = {DataCategory.GENERIC}
    IS_GENERATOR = False  # Passive processor
    MIN_INPUTS = 1
    MAX_INPUTS = 1

    class Params(BaseModel):
        annotations: Dict[str, Any]  # metadata fields to add/overwrite

    def __init__(self, config):
        super().__init__(config)
        self.params = self.Params(**config.get('params', {}))
        self.logger = logging.getLogger(self.node_type)

    def on_data(self, packet: DataPacket, input_channel: str):
        # 1. Validate compatibility
        if not self.validate_input(packet):
            return

        # 2. Merge existing metadata with annotations
        existing_meta = packet.metadata or {}
        merged_meta = {**existing_meta, **self.params.annotations}

        # 3. Create new packet with updated metadata
        new_pkt = self.modify_packet(
            packet,
            new_content=packet.content,
            data_type=packet.data_type,
            format=packet.format,
            category=packet.category,
            metadata=merged_meta,
            lifecycle_state=LifecycleState.PROCESSED
        )

        # 4. Publish annotated packet
        for out_ch in self.outputs:
            self.data_bus.publish(out_ch, new_pkt)


NODE_CLASSES = [Annotator]
