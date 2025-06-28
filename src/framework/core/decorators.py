import time
import functools
import logging

def node_telemetry(method_name=None):
    def decorator(func):
        @functools.wraps(func)
        def wrapper(self, *args, **kwargs):
            self.emit_telemetry("processing_start", time.time())
            start = time.perf_counter()
            try:
                return func(self, *args, **kwargs)
            except Exception as e:
                self.emit_telemetry("processing_error", str(e))
                raise
            finally:
                duration = time.perf_counter() - start
                self.emit_telemetry("processing_end", time.time())
                self.emit_telemetry("execution_time", duration)
        return wrapper
    return decorator
