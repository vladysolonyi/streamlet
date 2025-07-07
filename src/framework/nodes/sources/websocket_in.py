import asyncio
import threading
import logging
import websockets
from pydantic import BaseModel
from framework.nodes.base_node import BaseNode
from framework.data.data_packet import DataPacket
from framework.data.data_types import DataType, DataFormat, DataCategory

class WebSocketIn(BaseNode):
    node_type = "websocket_in"
    tags = ["network"]
    IS_GENERATOR = True  # Actively receives data

    accepted_data_types = {DataType.EVENT}
    accepted_formats = {DataFormat.TEXTUAL}
    accepted_categories = {DataCategory.GENERIC}

    class Params(BaseModel):
        url: str  # WebSocket server URL
        reconnect_delay: int = 5  # seconds to wait on disconnect
        auto_connect: bool = True

    def __init__(self, config):
        super().__init__(config)
        self.params = self.Params(**config.get("params", {}))
        self.logger = logging.getLogger("WebSocketIn")
        self._loop = None
        self._thread = None

        if self.params.auto_connect:
            self._start_loop()

    def _start_loop(self):
        self._thread = threading.Thread(target=self._run_loop, daemon=True)
        self._thread.start()

    def _run_loop(self):
        self._loop = asyncio.new_event_loop()
        asyncio.set_event_loop(self._loop)
        self._loop.run_until_complete(self._connect_loop())

    async def _connect_loop(self):
        while True:
            try:
                self.logger.info(f"Connecting to WebSocket: {self.params.url}")
                async with websockets.connect(self.params.url) as ws:
                    self.logger.info("WebSocket connection established")
                    async for message in ws:
                        packet = self.create_packet(
                            content=message,
                            data_type=DataType.EVENT,
                            format=DataFormat.TEXTUAL,
                            category=DataCategory.GENERIC
                        )
                        self.publish(packet)
            except Exception as e:
                self.logger.error(f"WebSocket error: {e}")
                await asyncio.sleep(self.params.reconnect_delay)

NODE_CLASSES = [WebSocketIn]
