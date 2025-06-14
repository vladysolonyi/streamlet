# src/framework/core/telemetry.py
import janus
import asyncio
import logging
from fastapi import WebSocket
from fastapi.websockets import WebSocketDisconnect

# Set up logger
telemetry_logger = logging.getLogger("telemetry")
telemetry_logger.setLevel(logging.DEBUG)

class Telemetry:
    def __init__(self):
        self.active_connections = set()
        self.async_lock = asyncio.Lock()
        self.queue = janus.Queue()
        self.is_running = False
        telemetry_logger.debug("Telemetry system initialized")

    async def add_connection(self, websocket: WebSocket):
        async with self.async_lock:
            self.active_connections.add(websocket)
            client = f"{websocket.client.host}:{websocket.client.port}"
            telemetry_logger.debug(f"➕ Added connection: {client}. Total: {len(self.active_connections)}")

    async def remove_connection(self, websocket: WebSocket):
        async with self.async_lock:
            if websocket in self.active_connections:
                self.active_connections.discard(websocket)
                client = f"{websocket.client.host}:{websocket.client.port}"
                telemetry_logger.debug(f"➖ Removed connection: {client}. Total: {len(self.active_connections)}")

    def broadcast_sync(self, message: dict):
        """Called from sync nodes to queue messages"""
        try:
            self.queue.sync_q.put(message)
            telemetry_logger.debug(f"📦 Queued telemetry: {message} | Queue size: {self.queue.sync_q.qsize()}")
        except Exception as e:
            telemetry_logger.error(f"❌ Queue error: {str(e)}")

    async def _async_broadcaster(self):
        """Process messages from the queue"""
        self.is_running = True
        telemetry_logger.info("🚀 Starting telemetry broadcaster")
        
        try:
            while self.is_running:
                try:
                    message = await asyncio.wait_for(
                        self.queue.async_q.get(), 
                        timeout=1.0
                    )
                    
                    telemetry_logger.debug(f"📡 Processing message: {message}")
                    
                    async with self.async_lock:
                        dead_connections = []
                        conn_count = len(self.active_connections)
                        telemetry_logger.debug(f"Broadcasting to {conn_count} connections")
                        
                        for conn in self.active_connections:
                            try:
                                await conn.send_json(message)
                                telemetry_logger.debug(f"  ✅ Sent to {conn.client}")
                            except (WebSocketDisconnect, RuntimeError) as e:
                                dead_connections.append(conn)
                                telemetry_logger.debug(f"  ❌ Dead connection: {conn.client} - {str(e)}")
                            except Exception as e:
                                telemetry_logger.error(f"  ⚠️ Send error to {conn.client}: {str(e)}")
                                
                        for conn in dead_connections:
                            self.active_connections.discard(conn)
                            
                    self.queue.async_q.task_done()
                    
                except asyncio.TimeoutError:
                    # Normal timeout - log periodically
                    telemetry_logger.debug("⏳ Queue timeout (no messages)")
                    continue
                except Exception as e:
                    telemetry_logger.error(f"Broadcaster error: {str(e)}")
                    await asyncio.sleep(0.1)
                    
        except asyncio.CancelledError:
            telemetry_logger.info("🔌 Broadcaster task cancelled")
        finally:
            self.is_running = False
            telemetry_logger.info("🛑 Telemetry broadcaster stopped")

    def stop(self):
        """Gracefully stop the broadcaster"""
        if self.is_running:
            telemetry_logger.info("🛑 Stopping telemetry broadcaster")
            self.is_running = False

telemetry = Telemetry()