import time
from framework.core.decorators import node_telemetry
from framework.data import DataType, DataFormat, DataCategory
from pydantic import BaseModel
from framework.nodes.base_node import BaseNode
from framework.data.data_packet import DataPacket

class TimerNode(BaseNode):
    node_type = "timer"
    tags = ["utils"]
    accepted_data_types = set()          # No inputs
    accepted_formats = set()
    accepted_categories = set()
    IS_GENERATOR = True
    MIN_INPUTS = 0

    class Params(BaseModel):
        interval: float  = 1.0            # seconds between events
        use_textual: bool = False         # True => textual timestamp

    def _update_reference(self, param_name: str, ref_path: str, packet: DataPacket):
        super()._update_reference(param_name, ref_path, packet)
        if param_name == "interval":
            new_interval = float(self.params.interval)
            self.logger.info(f"Interval ref updated to {new_interval}s – resetting timer")
            self.last_processed = time.time()


    def should_process(self):
        # Trigger at set intervals
        return time.time() - self.last_processed >= self.params.interval

    @node_telemetry("process")
    def process(self):
        # Determine content
        now = time.time()
        if self.params.use_textual:
            content = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(now))
            fmt = DataFormat.TEXTUAL
        else:
            content = now
            fmt = DataFormat.NUMERICAL

        # Create and publish an EVENT packet
        pkt = self.create_packet(
            content=content,
            data_type=DataType.EVENT,
            format=fmt,
            category=DataCategory.GENERIC
        )
        self.data_bus.publish(self.outputs[0], pkt)
        self.last_processed = now

NODE_CLASSES = [TimerNode]