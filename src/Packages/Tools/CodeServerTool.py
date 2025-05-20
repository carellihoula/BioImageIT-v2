import threading
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

    def init_and_launch_code_server(self):
        """Install and launch code-server in a separate thread (only once)."""
        with self._launch_lock:
            if not self.environment_ready:
                threading.Thread(target=self.setup_code_server, daemon=True).start()

    def setup_code_server(self):
        """Handle the installation and launching of code-server."""
        dependencies = {
            'python': '3.10',
            'conda': ['code-server'],
            'pip': []
        }

        if not environmentManager.environmentExists("codeserver-env"):
            environmentManager.create(
                environment="codeserver-env",
                dependencies=dependencies,
            )

        CodeServerTool.environment = environmentManager.launch(
            environment="codeserver-env",
            customCommand=(
                f'code-server --install-extension launchfileauto-latest.vsix && '
                f'code-server --auth none --bind-addr 127.0.0.1:3000'
            ),
            condaEnvironment=True
        )

        self.environment_ready = True
