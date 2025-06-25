# framework/nodes/loaders/udp_in.py

import socket
import logging
import threading
import time
from framework.nodes.base_node import BaseNode
from pydantic import BaseModel
from framework.data.data_packet import DataPacket
from framework.data.data_types import *

class UDPIn(BaseNode):
    """Node for receiving data via UDP and emitting DataPackets"""
    node_type = "udp_in"
    MIN_INPUTS = 0
    MAX_INPUTS = 0
    IS_ACTIVE = True
    accepted_data_types = {DataType.STREAM, DataType.DERIVED, DataType.STATIC}
    accepted_formats = {DataFormat.NUMERICAL, DataFormat.TEXTUAL, DataFormat.BINARY}
    accepted_categories = set(DataCategory)

    class Params(BaseModel):
        listen_ip: str = "0.0.0.0"
        listen_port: int = 7000
        timeout: float = 0.1
        buffer_size: int = 1024

    def __init__(self, config):
        super().__init__(config)
        self.logger = logging.getLogger('udp_in')
        self.logger.setLevel(logging.DEBUG)
        
        self.params = self.Params(**config.get('params', {}))
        self.sock = None
        self._running = threading.Event()
        self._thread = None
        self.logger.info(f"Initializing UDP listener on {self.params.listen_ip}:{self.params.listen_port}")

    def should_process(self):
        return False

    def start(self):
        """Start the listener thread"""
        if self._running.is_set():
            return
            
        try:
            # Create socket with reuse options
            self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            
            # Enable address and port reuse
            self.sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            if hasattr(socket, 'SO_REUSEPORT'):
                self.sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEPORT, 1)
            
            # Set timeout and bind
            self.sock.settimeout(self.params.timeout)
            self.sock.bind((self.params.listen_ip, self.params.listen_port))
            
            self._running.set()
            self._thread = threading.Thread(
                target=self._receive_loop,
                name=f"UDPIn-{self.params.listen_port}",
                daemon=True
            )
            self._thread.start()
            self.logger.info(f"Started UDP listener on {self.params.listen_ip}:{self.params.listen_port}")
        except OSError as e:
            if e.errno == 48:  # Address already in use
                self.logger.warning("Address in use - retrying in 1 second")
                time.sleep(1)
                self.start()  # Retry once
            else:
                self.logger.error(f"Start failed: {str(e)}", exc_info=True)
                raise
        except Exception as e:
            self.logger.error(f"Start failed: {str(e)}", exc_info=True)
            raise

    def _receive_loop(self):
        """Main receive loop"""
        while self._running.is_set():
            try:
                data, addr = self.sock.recvfrom(self.params.buffer_size)
                self.logger.debug(f"Received {len(data)} bytes from {addr}")
                
                packet = self.create_packet(
                    content=data,
                    metadata={"remote_addr": addr}
                )
                
                self.data_bus.publish(self.outputs[0], packet)
                
            except socket.timeout:
                continue
            except OSError as e:
                if e.errno == 9:  # Bad file descriptor (socket closed)
                    break
                elif self._running.is_set():
                    self.logger.error(f"Socket error: {str(e)}")
            except Exception as e:
                if self._running.is_set():
                    self.logger.error(f"Receive error: {str(e)}")
                break

        self.logger.info("Receive thread exiting")

    def stop(self):
        """Stop the thread and close socket"""
        if not self._running.is_set():
            return
            
        self.logger.debug("Stopping UDP listener")
        self._running.clear()
        
        # Close socket to break out of recvfrom
        if self.sock:
            try:
                # Set timeout to break recvfrom faster
                self.sock.settimeout(0.1)
                
                # Send dummy packet to unblock recvfrom
                try:
                    self.sock.sendto(b'', ('127.0.0.1', self.params.listen_port))
                except:
                    pass
                
                # Close socket
                self.sock.close()
            except Exception as e:
                self.logger.warning(f"Error closing socket: {str(e)}")
            finally:
                self.sock = None
        
        # Wait for thread to finish
        if self._thread and self._thread.is_alive():
            self._thread.join(timeout=2.0)
            if self._thread.is_alive():
                self.logger.warning("Thread did not exit cleanly")
                # Try to force terminate if still alive
                try:
                    import ctypes
                    ctypes.pythonapi.PyThreadState_SetAsyncExc(ctypes.c_long(self._thread.ident), ctypes.py_object(SystemExit))
                except:
                    pass
        
        self.logger.info("UDP listener stopped")

    def cleanup(self):
        """Alias for stop to match pipeline interface"""
        self.stop()

NODE_CLASSES = [UDPIn]