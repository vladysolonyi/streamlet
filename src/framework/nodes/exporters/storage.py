import logging
from typing import Any, Dict, List, Optional
from pydantic import BaseModel
from framework.nodes.base_node import BaseNode
from framework.data.data_packet import DataPacket
from framework.data.data_types import DataType, DataFormat, DataCategory
from framework.core.decorators import node_telemetry

class StorageNode(BaseNode):
    node_type = "storage"
    tags = ["beta"]
    accepted_data_types = set(DataType)
    accepted_formats = {DataFormat.NUMERICAL, DataFormat.TEXTUAL, DataFormat.BINARY}
    accepted_categories = set(DataCategory)
    IS_GENERATOR = False
    MIN_INPUTS = 1
    MAX_INPUTS = 1

    class Params(BaseModel):
        filter_by_type: Optional[str] = None    # only store packets of this DataType
        include_metadata: bool = True           # add packet.metadata to stored record

    def __init__(self, config):
        super().__init__(config)
        self.params = self.Params(**config.get("params", {}))
        self._storage: List[Dict[str, Any]] = []
        self.last_entry: Optional[Dict[str, Any]] = None
        self.logger = logging.getLogger(self.node_type)

    @node_telemetry("on_data")
    def on_data(self, packet: DataPacket, input_channel: str):
        # 1. Filter by data_type if requested
        if self.params.filter_by_type and packet.data_type.name.lower() != self.params.filter_by_type.lower():
            return

        # 2. Build a simple record
        record: Dict[str, Any] = {
            "content": packet.content,
            "timestamp": packet.timestamp.isoformat(),
            "source": packet.source,
        }
        if self.params.include_metadata and packet.metadata:
            record["metadata"] = packet.metadata

        # 3. Store and update last_entry
        self._storage.append(record)
        self.last_entry = record

        self.logger.debug(f"Stored record #{len(self._storage)}: {record}")

        # 4. Immediately pass the original packet through
        for out_ch in self.outputs:
            self.data_bus.publish(out_ch, packet)

    def get_all(self) -> List[Dict[str, Any]]:
        """Optionally expose the full session storage in code."""
        return list(self._storage)

NODE_CLASSES = [StorageNode]
