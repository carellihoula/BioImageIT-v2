import logging
import asyncio
from server.websocket_manager import ws_manager  # import the already created instance
from event_loop import main_loop

class SocketHandler(logging.Handler):
    """Handler that sends each log to the 'logs' topic of ws_manager."""
    def __init__(self, level: int = logging.NOTSET):
        super().__init__(level)

    def emit(self, record: logging.LogRecord):
        try:
            msg = self.format(record)
            asyncio.run_coroutine_threadsafe(
                ws_manager.publish("logs", msg),
                main_loop
            )
        except Exception:
            self.handleError(record)

def configure_logging(logfile_path: str = "app.log"):
    """Installs FileHandler + SocketHandler on the root logger."""
    fmt = "%(asctime)s | %(levelname)-5s | %(name)s | %(message)s"
    datefmt = "%Y-%m-%d %H:%M:%S"

    # FileHandler (writes to app.log)
    fh = logging.FileHandler(logfile_path, encoding="utf-8")
    fh.setLevel(logging.DEBUG)
    fh.setFormatter(logging.Formatter(fmt, datefmt))

    # SocketHandler (pushes logs to WS topic "logs")
    sh = SocketHandler(level=logging.DEBUG)
    sh.setFormatter(logging.Formatter(fmt, datefmt))

    root = logging.getLogger()
    root.setLevel(logging.DEBUG)
    root.addHandler(fh)
    root.addHandler(sh)
