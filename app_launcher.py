# BIOIMAGEIT/app_launcher.py
import webview
import threading
import uvicorn
import time
from api import Api
from server.main import app as quart_app



SERVER_HOST = "127.0.0.1"
SERVER_PORT = 8000
#APP_URL = f"http://{SERVER_HOST}:{SERVER_PORT}"
APP_URL = "http://localhost:5173"  # For testing on localhost

instance_api = Api()

def runQuartServer():
    print(f"Starting Quart server on {APP_URL}")
    try:
        uvicorn.run(
            quart_app,
            host=SERVER_HOST,
            port=SERVER_PORT,
            log_level="info"
        )
    except Exception as e:
        print(f"Error while starting or running Quart server: {e}")

if __name__ == '__main__':
    print("Launching BioImageIT application (minimal version)...")
    server_thread = threading.Thread(target=runQuartServer, daemon=True)
    server_thread.start()

    print(f"Waiting for server to start ({time.sleep(3) or 3} seconds)...")

    print(f"Launching Pywebview window pointing to {APP_URL}")
    try:
        webview.create_window(
            'BioImageIT Minimal',
            APP_URL,
            width=1900,
            height=900,
            resizable=True,
            js_api=instance_api
        )
        #gui='gtk'
        webview.start(debug=False, gui="qt")
    except Exception as e:
        print(f"Error while creating or starting Pywebview window: {e}")

    print("BioImageIT application (minimal version) terminated.")