import logging
import asyncio
import websockets
import json
import threading

class SocketHandler(logging.Handler):
    def __init__(self, ws_url="ws://localhost:8000/ws"):
        super().__init__()
        self.ws_url = ws_url
        self.queue = asyncio.Queue()
        self.loop = asyncio.new_event_loop()
        self.thread = threading.Thread(target=self._start_loop, daemon=True)
        self.thread.start()
        self.formatter = logging.Formatter(fmt="%(asctime)s", datefmt="%Y-%m-%d %H:%M:%S") 

    def _start_loop(self):
        asyncio.set_event_loop(self.loop)
        self.loop.run_until_complete(self._connect_and_send())
    
    def formatTime(self, record):
        full_time =  self.formatter.formatTime(record)
        return full_time.split(",")[0]

    async def _connect_and_send(self):
        while True:
            try:
                async with websockets.connect(self.ws_url) as websocket:
                    await websocket.send(json.dumps({
                    "action": "wait_for_permission",
                    "topic": "logs"
                    }))

                    permission_response = await websocket.recv()
                    permission_data = json.loads(permission_response)

                    if permission_data.get("message") is True:
                        while True:
                            log_entry = await self.queue.get()
                            await websocket.send(json.dumps(log_entry))
                    else:
                        print("Permission denied for sending logs.")
                        await asyncio.sleep(1)
            except Exception as e:
                print(f"⚠️ WebSocket connection interrupted : {e}")
                await asyncio.sleep(3)

    def emit(self, record: logging.LogRecord):
        try:
            if record.levelno < logging.INFO:
                return
            # msg = self.format(record)
            log_entry = {
                "action": "publish",
                "topic": "logs",
                "message": {
                    "time": self.formatTime(record),         
                    "level": record.levelname,               
                    "logger": record.name,                   
                    "message": record.getMessage()  
                }
            }
            asyncio.run_coroutine_threadsafe(self.queue.put(log_entry), self.loop)
        except Exception:
            self.handleError(record)


def configure_logging(logfile_path="app.log"):
    """Configure logging with file and websocket handlers"""
    fmt = "%(asctime)s | %(levelname)-5s | %(name)s | %(message)s"
    datefmt = "%Y-%m-%d %H:%M:%S"

    fh = logging.FileHandler(logfile_path, encoding="utf-8")
    fh.setLevel(logging.DEBUG)
    fh.setFormatter(logging.Formatter(fmt, datefmt))

    sh = SocketHandler()
    sh.setLevel(logging.DEBUG)
    sh.setFormatter(logging.Formatter(fmt, datefmt))

    root = logging.getLogger()
    root.setLevel(logging.DEBUG)
    root.addHandler(fh)
    root.addHandler(sh)
