import requests
import logging
from pydantic import BaseModel
from framework.core.decorators import node_telemetry
from framework.nodes.base_node import BaseNode
from framework.data import DataType, DataFormat, DataCategory

class ApiRequestNode(BaseNode):
    node_type = "api_request"
    accepted_data_types = {DataType.EVENT}    # Only trigger on EVENT packets
    accepted_formats = set(DataFormat)                   # Accept any format
    accepted_categories = set(DataCategory)    # Accept all categories
    IS_GENERATOR = False
    IS_ASYNC_CAPABLE = False
    MIN_INPUTS = 1
    MAX_INPUTS = 1

    class Params(BaseModel):
        url: str                               # API endpoint
        method: str = "GET"                  # HTTP method
        headers: dict = {}                     # Optional HTTP headers
        params: dict = {}                      # Query parameters
        data: dict = {}                        # Body data for POST/PUT
        timeout: float = 5.0                   # Request timeout in seconds
        response_format: str = "json"        # "json" or "text"

    def __init__(self, config):
        super().__init__(config)
        self.logger = logging.getLogger(self.node_type)
        self.params = self.Params(**config.get('params', {}))

    @node_telemetry("on_data")
    def on_data(self, packet, input_channel: str):
        # 1. Validate and buffer if needed
        if not self.validate_input(packet):
            return

        # 2. Perform API request
        try:
            resp = requests.request(
                method=self.params.method,
                url=self.params.url,
                headers=self.params.headers,
                params=self.params.params,
                json=self.params.data,
                timeout=self.params.timeout
            )
            resp.raise_for_status()
        except Exception as e:
            self.logger.error(f"API request failed: {e}")
            return

        # 3. Parse response
        if self.params.response_format == "json":
            content = resp.json()
        else:
            content = resp.text

        # 4. Create and publish new packet
        new_pkt = self.modify_packet(
            packet,
            new_content=content,
            data_type=DataType.DERIVED,
            format=DataFormat.TEXTUAL,
            category=DataCategory.GENERIC
        )
        for out_ch in self.outputs:
            self.data_bus.publish(out_ch, new_pkt)

# Register node classes for the pipeline
NODE_CLASSES = [ApiRequestNode]
