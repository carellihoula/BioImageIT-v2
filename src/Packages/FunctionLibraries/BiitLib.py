from pathlib import Path
from importlib import import_module
import re
import sys

try:
    PROJECT_ROOT_PATH = Path(__file__).resolve().parents[3]
except IndexError:
    PROJECT_ROOT_PATH = Path(__file__).resolve().parent
    print(f"WARNING: Unable to go up 3 levels from {Path(__file__).resolve().parent}. PROJECT_ROOT_PATH is set to {PROJECT_ROOT_PATH}")
    print("Make sure Biit.py is in src/Packages/FunctionLibraries/ for PROJECT_ROOT_PATH to be correct.")

TOOLS_BASE_PATH = PROJECT_ROOT_PATH / "src" / "Tools"

def sourcesFolderHasVersion(sourcesPath:Path):
    pattern = r"^bioimageit-v\d+\.\d+\.\d+-[a-f0-9]+$"
    return bool(re.match(pattern, sourcesPath.name))

def get_project_root_path() -> Path:
    return PROJECT_ROOT_PATH

sourcesPath = Path(__file__).parent.parent
rootPath = sourcesPath.parent if sourcesFolderHasVersion(sourcesPath) else sourcesPath

def getSourcesPath():
    return sourcesPath

def getImportPath(toolPath: Path):
    return '.'.join(toolPath.resolve().relative_to(get_project_root_path()).with_suffix('').parts)

def getTools(tools_directory_path: Path) -> list[Path]:
    if not tools_directory_path.is_dir():
        return []
    return sorted([p for p in tools_directory_path.rglob('*.py') if p.is_file() and p.name != "__init__.py"])

def get_tool_info(tool_path: Path, module: object) -> dict | None:
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
        'path': str(tool_path.relative_to(TOOLS_BASE_PATH)),
        'module_path': getImportPath(tool_path)
    }
    return tool_info

def load_tools_info(tools_directory_path_str: str | Path) -> list:
    tools_dir_path = Path(tools_directory_path_str)
    tools_information = []
    for tool_file_path in getTools(tools_dir_path):
        module_import_str = ""
        try:
            module_import_str = getImportPath(tool_file_path)
            module = import_module(module_import_str)
            tool_info = get_tool_info(tool_file_path, module)
            if tool_info is not None:
                tools_information.append(tool_info)
        except Exception as e:
            print(f"Error loading tool from {module_import_str}: {e}")
            
    return tools_information

toolsPath = TOOLS_BASE_PATH

            