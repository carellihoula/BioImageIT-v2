import threading
import time

import requests
from src.ToolManagement.EnvironmentManager import environmentManager

class CodeServerTool:
    _instance = None
    _lock = threading.Lock()  # To ensure multithreaded security

    def __new__(cls):
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super(CodeServerTool, cls).__new__(cls)
                    cls._instance._init_instance()
        return cls._instance

    def _init_instance(self):
        self.environment_ready = False
        self._launch_lock = threading.Lock()
        self.status = "idle"

    def wait_for_http_ready(self, url="http://127.0.0.1:3000", timeout=120):
        start = time.time()
        while time.time() - start < timeout:
            try:
                response = requests.get(url, timeout=2)
                if response.status_code == 200:
                    return True
            except Exception:
                time.sleep(0.5)
        return False

    def get_status(self):
        return self.status

    def init_and_launch_code_server(self):
        """Install and launch code-server in a separate thread (only once)."""
        # if self.status != "idle":
        #     return
        with self._launch_lock:
            if self.environment_ready or self.status == "starting":
                return  
            self.status = "starting"
            threading.Thread(target=self.setup_code_server, daemon=True).start()

    def setup_code_server(self):
        
       
        """Handle the installation and launching of code-server."""
        dependencies = {
            'python': '3.10',
            'conda': ['code-server'],
            'pip': []
        }
        
        

        if not environmentManager.exists("codeserver-env2"):
                # self.status = "starting"
                environmentManager.create(
                   "codeserver-env2",
                    dependencies,
                )

        CodeServerTool.environment = environmentManager.launch(
                "codeserver-env2",
               
                    f'code-server --install-extension launchfileauto-latest.vsix && '
                    f'code-server --auth none --bind-addr 127.0.0.1:3000'
                
                #condaEnvironment=True
            )
        if self.wait_for_http_ready():
            self.environment_ready = True
            self.status = "ready"
        else:
            self.status = "error: timeout waiting for port"
        # self.environment_ready = True
        # self.status = "ready"

        # except Exception as e:
        #     self.status = f"error: {str(e)}"