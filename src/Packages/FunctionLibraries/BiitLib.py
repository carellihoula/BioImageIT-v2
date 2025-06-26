from pathlib import Path
from importlib import import_module
import re
import sys
from src import getRootPath

# try:
#     PROJECT_ROOT_PATH = Path(__file__).resolve().parents[3]
# except IndexError:
#     PROJECT_ROOT_PATH = Path(__file__).resolve().parent
#     print(f"WARNING: Unable to go up 3 levels from {Path(__file__).resolve().parent}. PROJECT_ROOT_PATH is set to {PROJECT_ROOT_PATH}")
#     print("Make sure Biit.py is in src/Packages/FunctionLibraries/ for PROJECT_ROOT_PATH to be correct.")

class BiitLib:
    classes = {}

TOOLS_BASE_PATH = getRootPath() / "src" / "Tools"


def sourcesFolderHasVersion(sourcesPath:Path):
    pattern = r"^bioimageit-v\d+\.\d+\.\d+-[a-f0-9]+$"
    return bool(re.match(pattern, sourcesPath.name))

def getImportPath(toolPath: Path, base_path: Path) -> str:
    return '.'.join(toolPath.resolve().relative_to(base_path).with_suffix('').parts)

def getTools(tools_directory_path: Path) -> list[Path]:
    if not tools_directory_path.is_dir():
        return []
    return sorted([p for p in tools_directory_path.rglob('*.py') if p.is_file() and p.name != "__init__.py"])

def get_tool_info(tool_path: Path, module: object, base_path: Path) -> dict | None:
    if not hasattr(module, 'Tool'):
        return None

    tool_class = module.Tool
    tool_info = {
        'name': getattr(tool_class, 'name', "Undefined Name"),
        'description': getattr(tool_class, 'description', ""),
        'categories': getattr(tool_class, 'categories', []),
        'environment': getattr(tool_class, 'environment', 'bioimageit'),
        'dependencies': getattr(tool_class, 'dependencies', {}),
        'inputs': getattr(tool_class, 'inputs', []),
        'outputs': getattr(tool_class, 'outputs', []),
        'test': getattr(tool_class, 'test', []),
        'path': str(tool_path.relative_to(base_path)),
        'module_path': getImportPath(tool_path, base_path)
    }
    return tool_info

def add_to_syspath(path: Path):
    s = str(path.resolve())
    if s not in sys.path:
        sys.path.insert(0, s)


def load_tools_info(tools_directory_path_str: str | Path, tools_dictory_workflow_path: str | Path) -> list:
    tools_dir_path = Path(tools_directory_path_str)
    tools_workflow_path = Path(tools_dictory_workflow_path) / "Tools"
   
    add_to_syspath(tools_dir_path)
    add_to_syspath(tools_workflow_path.parent)

    tools_information = []
    # Concatenate tools from both directories
    all_tool_paths = list(getTools(tools_dir_path)) + list(getTools(tools_workflow_path))
    
    for tool_file_path in all_tool_paths:
        module_import_str = ""
        try:
            if str(tool_file_path).startswith(str(tools_dir_path)):
                base_path = tools_dir_path
            else: 
                base_path = tools_workflow_path.parent
            module_import_str = getImportPath(tool_file_path, base_path)
            module = import_module(module_import_str)
            tool_info = get_tool_info(tool_file_path, module, base_path)
            if tool_info is not None:
                tools_information.append(tool_info)
        except Exception as e:
            print(f"Error loading tool from {module_import_str}: {e}")
            
    return tools_information

toolsPath = TOOLS_BASE_PATH

def createNode(modulePath: Path, moduleImportPath: str, module):
    if not hasattr(module, 'Tool'):
        return None

    tool = module.Tool
    tool.moduleImportPath = moduleImportPath

   
    if not hasattr(tool, 'environment'):
        tool.environment = 'bioimageit'
    if not hasattr(tool, 'dependencies'):
        tool.dependencies = {}

    for attr in ['name', 'description']:
        if not hasattr(tool, attr):
            raise Exception(f"Tool {moduleImportPath} missing required attribute: {attr}")

    BiitLib.classes[modulePath.name] = tool
    return tool

def loadTool(path: Path, base_path: Path = None):
    import_path = getImportPath(path, base_path)
    module = import_module(import_path)
    return createNode(path, import_path, module)


# def make_serializable(value):
#     if isinstance(value, (str, int, float, bool, type(None))):
#         return value
#     elif isinstance(value, (list, tuple)):
#         return [make_serializable(item) for item in value]
#     elif isinstance(value, dict):
#         return {k: make_serializable(v) for k, v in value.items()}
#     else:
#         return str(value)