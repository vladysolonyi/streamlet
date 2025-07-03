from typing import Any, Iterable
from pydantic import BaseModel
from framework.nodes.base_node import BaseNode
from framework.data.data_packet import DataPacket
from framework.data.data_types import DataType, DataFormat, DataCategory, LifecycleState


class Splitter(BaseNode):
    node_type = "splitter"
    accepted_data_types = {DataType.STREAM, DataType.EVENT}
    accepted_formats = {DataFormat.NUMERICAL, DataFormat.TEXTUAL, DataFormat.BINARY}
    accepted_categories = {DataCategory.GENERIC}
    IS_GENERATOR = False

    class Params(BaseModel):
        flatten_strings: bool = False  # if True, split string into characters

    def __init__(self, config):
        super().__init__(config)
        self.params = self.Params(**config.get("params", {}))

    def on_data(self, packet: DataPacket, input_channel: str):
        content = packet.content

        # Determine what to iterate
        if isinstance(content, str) and not self.params.flatten_strings:
            items = [content]  # treat whole string as one item
        elif isinstance(content, str) and self.params.flatten_strings:
            items = list(content)
        elif isinstance(content, (list, tuple, set)):
            items = content
        else:
            self.logger.warning("Unsupported content type for splitting: %s", type(content))
            return

        for item in items:
            new_packet = self.create_packet(
                content=item,
                data_type=DataType.DERIVED,
                format=self._infer_format(item),
                metadata=packet.metadata,
                lifecycle_state=LifecycleState.PROCESSED
            )
            self.data_bus.publish(self.outputs[0], new_packet)

    def _infer_format(self, value: Any):
        if isinstance(value, (int, float)):
            return DataFormat.NUMERICAL
        elif isinstance(value, str):
            return DataFormat.TEXTUAL
        elif isinstance(value, bytes):
            return DataFormat.BINARY
        return DataFormat.TEXTUAL  # fallback

NODE_CLASSES = [Splitter]
