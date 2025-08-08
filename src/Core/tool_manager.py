from importlib import import_module
from pathlib import Path
from src.Core import utils

class ToolManager:
    TOOLS_PATH = Path(__file__).parent / 'tools'

    def __init__(self) -> None:
        self.tools: dict = self.load_tools()

    def _get_tools(self, tools_path: Path = TOOLS_PATH):
        return sorted(list((tools_path).glob('*/*.py')))

    def _get_import_path(self, toolPath):
        return '.'.join(toolPath.resolve().relative_to(utils.get_root_path()).with_suffix('').parts)

    def load_tool(self, tool_path: Path):
        module_import_path = self._get_import_path(tool_path)
        module = import_module(module_import_path)

        if not hasattr(module.Tool, 'environment'):
            module.Tool.environment = 'bioimageit'
        if not hasattr(module.Tool, 'dependencies'):
            module.Tool.dependencies = dict()
        for attr in ['name', 'description']:
            if not hasattr(module.Tool, attr):
                raise Exception(f'Tool {module_import_path} has no attribute {attr}.')
        
        self.tools[tool_path.stem] = dict(path=tool_path, module=module, module_import_path=module_import_path)
    
    def load_tools(self, workflow_tools_path: Path | None = None)-> dict[str, dict]:
        self.tools = {}
        workflow_tools = self._get_tools(workflow_tools_path) if workflow_tools_path else []
        for tool_path in self._get_tools() + workflow_tools:
            self.load_tool(tool_path)
        return self.tools

    def get_tool_info(self, name: str, tool: dict) -> dict | None:
        root_path = utils.get_root_path()
        tool_class = tool["module"].Tool
        tool_info = {
            "name": name,
            "description": getattr(tool_class, "description", ""),
            "categories": getattr(tool_class, "categories", []),
            "environment": getattr(tool_class, "environment", "bioimageit"),
            "dependencies": getattr(tool_class, "dependencies", {}),
            "inputs": getattr(tool_class, "inputs", []),
            "outputs": getattr(tool_class, "outputs", []),
            "test": getattr(tool_class, "test", []),
            "path": str(tool["path"].relative_to(root_path)),
            "module_path": tool["module_import_path"]
        }
        return tool_info

    def get_tools(self, workflow_path_str: str):

        workflow_path = Path(workflow_path_str).resolve()
        if workflow_path.is_dir():
            self.load_tools(workflow_path / 'Tools')
        tools = [self.get_tool_info(name, tool) for name, tool in self.tools.items()]
        return tools

    
    def create_tool(self, workflow_path_str: str, raw_name: str):
        # Todo validate tool name
        tool_name = raw_name.replace(' ', '_')
        if tool_name in self.tools.keys():
            raise Exception(f'The tool {raw_name} already exists. Please choose a unique tool name.')
        
        workflow_path = Path(workflow_path_str).resolve()
        if not workflow_path.is_dir():
            raise Exception(f"Workflow path {workflow_path} not found.")
        
        workflow_tools_path = workflow_path / 'Tools'
        tool_path = workflow_tools_path / f'bif_{tool_name}' / f'{tool_name}.py'
        tool_path.parent.mkdir(exist_ok=True, parents=True)
        template_path = Path('core/') / 'tool_template.py'
        with open(tool_path, 'w') as destinationFile, open(template_path, 'r') as exampleFile:
            destinationFile.write(exampleFile.read())

        self.load_tool(tool_path)

        # Open script file in code editor
        # editCmd = ConfigManager().getPrefsValue("PREFS", "General/EditorCmd")
        # editCmd = editCmd.replace("@FILE", f'"{toolPath.resolve()}"') if "@FILE" in editCmd else f'{editCmd} {toolPath.resolve()}'
        # subprocess.Popen(editCmd, shell=True)

        # if str(workflow_tools_path) not in self.system_watcher.directories():
        #     self.system_watcher.addPath(str(workflow_tools_path.resolve()))
        # if str(tool_path) not in self.system_watcher.files():
        #     self.system_watcher.addPath(str(tool_path))
