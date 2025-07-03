import atexit
import logging
import signal
import webview
import threading
import uvicorn
import time
import sys
from api import Api
from server.main import app as fastapi_app
from src.Packages.Tools.CodeServerTool import CodeServerTool
from server.websocket_manager import WebSocketManager
from logging_config import configure_logging




configure_logging("app.log")
logger = logging.getLogger(__name__)

SERVER_HOST = "127.0.0.1"
SERVER_PORT = 8000
#APP_URL = f"http://{SERVER_HOST}:{SERVER_PORT}"
APP_URL = "http://localhost:5173"  # For testing on localhost

instance_api = Api()
code_server = CodeServerTool()

def cleanup(signum=None, frame=None):
    try: 
        print("Stopping Code Server and cleaning up...")
        code_server.stop_code_server()
    except Exception as e:
        print(f"Error during cleanup: {e}")

def runFastAPIServer():
    print(f"Starting FastAPI server on {APP_URL}")
    try:
        uvicorn.run(
            fastapi_app,
            host=SERVER_HOST,
            port=SERVER_PORT,
            log_level="info"
        )
    except Exception as e:
        print(f"Error while starting or running FastAPI server: {e}")

if __name__ == '__main__':
    print("Launching BioImageIT application (minimal version)...")
    logger.info("Launching BioImageIT application (minimal version)...")

    # Register cleanup function for normal shutdown
    atexit.register(cleanup)
    # Register cleanup function for signal handling
    signal.signal(signal.SIGINT, cleanup)
    signal.signal(signal.SIGTERM, cleanup)

    server_thread = threading.Thread(target=runFastAPIServer, daemon=True)
    server_thread.start()
    print(f"Waiting for server to start ({time.sleep(3) or 3} seconds)...")

    print(f"Launching Pywebview window pointing to {APP_URL}")
    try:
        webview.create_window(
            'BioImageIT Minimal',
            APP_URL,
            width=1900,
            height=900,
            text_select=True,
            resizable=True,
            js_api=instance_api
        )
        #gui='gtk'
        webview.start(debug=True, gui="qt")
    except Exception as e:
        print(f"Error while creating or starting Pywebview window: {e}")
    finally:
        # Final cleanup in case atexit doesn't trigger
        cleanup()

    print("BioImageIT application (minimal version) terminated.")