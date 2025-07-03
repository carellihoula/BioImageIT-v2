import threading
import time
import requests
# from src.ToolManagement.EnvironmentManager import environmentManager

from wetlands.environment_manager import EnvironmentManager
from wetlands.external_environment import ExternalEnvironment
from pathlib import Path
from src import getRootPath

# Initialize the environment manager
# environmentManager = EnvironmentManager("micromamba/", False)

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
        self.environment = None
        self.process = None
        self.environmentManager = EnvironmentManager("micromamba/", False)

    def wait_for_http_ready(self, url="http://127.0.0.1:3000", timeout=120):
        """Wait for the HTTP server to be ready by checking the URL."""
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
        if self.wait_for_http_ready():
            self.status = "ready"
        else:
            self.status = "starting"

        return self.status

    def init_and_launch_code_server(self):
        """Install and launch code-server in a separate thread (only once)."""
        with self._launch_lock:
            if self.environment_ready or self.status == "ready":
                return  
            threading.Thread(target=self.setup_code_server, daemon=True).start()

    def setup_code_server(self):
        """Handle the installation and launching of code-server."""
        try:
            self.status = "starting"
            dependencies = {
                'python': '3.10',
                'conda': ['code-server'],
                'pip': []
            }

            env_name = "codeserver12"
            # Check if environment already exists
            if not self.environmentManager.environmentExists(env_name):
                print("Creating new code-server environment...")

            extension_path = getRootPath() / 'launchfileauto-latest.vsix'
            print(f"Extension path: {extension_path}")
            # self.environment = ExternalEnvironment(env_name, self.environmentManager)
            self.environment = self.environmentManager.create(
                environment=env_name,
                dependencies=dependencies,
                additionalInstallCommands=[f"code-server --install-extension {extension_path}"]
            )
            
            commands = [
                # f"code-server --install-extension {extension_path}",
                # launch code-server
                "code-server --auth none --bind-addr 127.0.0.1:3000"
            ]


            # self.environment.launch()
           
            if not self.environment.launched():
                self.process = self.environment.launch()

            self.environment.executeCommands(commands)

            # if self.wait_for_http_ready():
            #     self.environment_ready = True
            #     self.status = "ready"
            # else:
            #     self.status = "error: timeout waiting for port"
            # # self.environment_ready = True
            # # self.status = "ready"
            # print(f"Code server setup complete with status: {self.status}")

        except Exception as e:
            self.status = f"error: {str(e)}"
            print(f"Error setting up code-server: {e}")


    def stop_code_server(self):
        """Stop the code-server and clean up resources."""
        try:
            if not self.process and not self.environment:
                # print("No process and no environment.")
                return
            if self.environment:
                self.environment._exit()
            # self.environment._exit()  
            self.environment_ready = False
            self.status = "stopped"
            print("Code server stopped successfully.")
            
        except Exception as e:
            print(f"Error stopping code-server: {e}")
            
    # def is_running(self):
    #     """Check if code-server is still running."""
    #     if not self.process:
    #         return False
    #     return self.process.poll() is None