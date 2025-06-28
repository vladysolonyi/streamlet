import os
import json
import csv
from typing import List, Dict, Any, Optional
from datetime import datetime
from pydantic import BaseModel
from framework.nodes.base_node import BaseNode
from framework.data.data_packet import DataPacket
from framework.data.data_types import *

class StorageNode(BaseNode):
    node_type = "storage"
    accepted_data_types = set(DataType)
    accepted_formats = {DataFormat.NUMERICAL, DataFormat.TEXTUAL, DataFormat.BINARY}
    accepted_categories = set(DataCategory)
    IS_GENERATOR = False

    class Params(BaseModel):
        storage_path: str = "./data_storage"
        file_prefix: str = "data"
        flush_on_each: bool = True
        file_format: str = "jsonl"  # "jsonl" or "csv"
        filter_by_type: Optional[str] = None
        include_metadata: bool = True

    def __init__(self, config):
        super().__init__(config)
        self.params = self.Params(**config.get("params", {}))
        os.makedirs(self.params.storage_path, exist_ok=True)
        self.buffer: List[DataPacket] = []

    def on_data(self, packet: DataPacket, input_channel: str):
        # Optional filtering
        if self.params.filter_by_type and packet.data_type.name.lower() != self.params.filter_by_type.lower():
            return

        self.buffer.append(packet)
        if self.params.flush_on_each:
            self.flush()

    def flush(self):
        if not self.buffer:
            return

        timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
        filename = f"{self.params.file_prefix}_{timestamp}.{self.params.file_format}"
        filepath = os.path.join(self.params.storage_path, filename)

        if self.params.file_format == "jsonl":
            with open(filepath, "w", encoding="utf-8") as f:
                for pkt in self.buffer:
                    entry = {
                        "content": pkt.content,
                        "timestamp": pkt.timestamp.isoformat(),
                        "source": pkt.source,
                    }
                    if self.params.include_metadata and pkt.metadata:
                        entry["metadata"] = pkt.metadata
                    f.write(json.dumps(entry) + "\n")

        elif self.params.file_format == "csv":
            # Assumes packets contain dicts or structured content
            headers = set()
            for pkt in self.buffer:
                if isinstance(pkt.content, dict):
                    headers.update(pkt.content.keys())
            headers = list(headers)

            with open(filepath, "w", newline="", encoding="utf-8") as f:
                writer = csv.DictWriter(f, fieldnames=headers)
                writer.writeheader()
                for pkt in self.buffer:
                    if isinstance(pkt.content, dict):
                        writer.writerow(pkt.content)

        self.buffer.clear()

NODE_CLASSES = [StorageNode]
