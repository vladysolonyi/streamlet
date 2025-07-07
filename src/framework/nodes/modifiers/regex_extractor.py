import re
import logging
from typing import List, Union
from pydantic import BaseModel
from framework.nodes.base_node import BaseNode
from framework.data.data_packet import DataPacket
from framework.data.data_types import DataType, DataFormat, DataCategory, LifecycleState


class RegexExtractor(BaseNode):
    node_type = "regex_extractor"
    tags = ["Untested"]
    accepted_data_types = {DataType.STREAM, DataType.EVENT}
    accepted_formats = {DataFormat.TEXTUAL}
    accepted_categories = {DataCategory.GENERIC}
    IS_GENERATOR = False  # passive processor

    class Params(BaseModel):
        pattern: str                     # regex pattern
        group: int = 0                   # which capture group to extract
        all_matches: bool = True         # if True, return list of matches

    def __init__(self, config):
        super().__init__(config)
        self.params = self.Params(**config.get('params', {}))
        self.logger = logging.getLogger(self.node_type)
        try:
            self._regex = re.compile(self.params.pattern)
        except re.error as e:
            self.logger.error(f"Invalid regex pattern: {e}")
            raise

    def on_data(self, packet: DataPacket, input_channel: str):
        # 1. Validate packet
        if not self.validate_input(packet):
            return
        text = packet.content
        if not isinstance(text, str):
            self.logger.warning("RegexExtractor received non-text content: %s", type(text))
            return

        # 2. Find matches
        matches = self._regex.findall(text)
        extracted: Union[List[str], str]

        # If pattern has groups, findall returns list of tuples
        if self.params.group != 0:
            filtered = []
            for m in matches:
                try:
                    # m might be tuple if multiple groups
                    val = m[self.params.group] if isinstance(m, tuple) else None
                    if val is not None:
                        filtered.append(val)
                except Exception:
                    continue
            matches = filtered

        if self.params.all_matches:
            extracted = matches
        else:
            extracted = matches[0] if matches else ""

        # 3. Create output packet
        out_pkt = self.create_packet(
            content=extracted,
            data_type=DataType.DERIVED,
            format=DataFormat.TEXTUAL,
            category=DataCategory.GENERIC,
            lifecycle_state=LifecycleState.PROCESSED
        )
        self.data_bus.publish(self.outputs[0], out_pkt)


NODE_CLASSES = [RegexExtractor]
