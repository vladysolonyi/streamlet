import time
from pydantic import BaseModel
from framework.nodes.base_node import BaseNode
from framework.data.data_packet import DataPacket
from framework.data.data_types import DataType, DataFormat, DataCategory, LifecycleState


class RateLimiter(BaseNode):
    node_type = "rate_limiter"
    tags = ["Untested"]
    accepted_data_types = {DataType.STREAM, DataType.EVENT}
    accepted_formats = {DataFormat.NUMERICAL, DataFormat.TEXTUAL, DataFormat.BINARY}
    accepted_categories = {DataCategory.GENERIC}
    IS_GENERATOR = False

    class Params(BaseModel):
        interval: float = 1.0  # minimum time between forwarded packets (in seconds)

    def __init__(self, config):
        super().__init__(config)
        self.params = self.Params(**config.get("params", {}))
        self.last_emit_time = 0.0

    def on_data(self, packet: DataPacket, input_channel: str):
        current_time = time.time()
        if current_time - self.last_emit_time >= self.params.interval:
            self.last_emit_time = current_time
            self.data_bus.publish(self.outputs[0], packet)
        else:
            self.logger.debug("RateLimiter skipped packet: too soon")

NODE_CLASSES = [RateLimiter]
