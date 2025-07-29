import os
import json
from pathlib import Path
import shutil
import tempfile
import pandas
from pydantic import BaseModel
import zipfile
from PIL import Image
import websockets

from src.ThumbnailManagement.ThumbnailGenerator import ThumbnailGenerator

BASE_WORKFLOWS_STORAGE = Path.home() / "BioImageIT_Workflows"
# file that will store the paths of managed workflows
REGISTRY_FILE_NAME = ".workflow_registry.json"
REGISTRY_FILE_PATH = BASE_WORKFLOWS_STORAGE / REGISTRY_FILE_NAME

DEFAULT_WORKFLOW_CONTENT = {
    "nodes": [], "edges": [], "viewport": {"x": 0, "y": 0, "zoom": 1}
}

class RenameRequest(BaseModel):
    old_full_path: str
    new_name: str

class DuplicateRequest(BaseModel):
    source_path: str 
    target_parent_path: str
    target_name: str

class CreateWorkflowRequest(BaseModel):
    name: str      
    path: str  

class WorkflowManager:
    def __init__(self, ws_url="ws://localhost:8000/ws"):
        BASE_WORKFLOWS_STORAGE.mkdir(parents=True, exist_ok=True)
        self._workflow_paths_registry = self._load_registry() 
        self.ws_url = ws_url
        self.selected_node = None
    
    def set_selected_node(self, node: dict):
        print(f"[WorkflowManager] selected Node : {node}") #["data"]["tool"]["name"]
        self.selected_node = node

    def get_selected_node(self):
        return self.selected_node
    
    def _load_registry(self) -> set[str]:
        if REGISTRY_FILE_PATH.exists():
            try:
                with REGISTRY_FILE_PATH.open("r") as f:
                    paths = json.load(f)
                    # Ensure these are strings and normalize them to resolved absolute paths
                    return set(str(Path(p).resolve()) for p in paths if isinstance(p, str))
            except (json.JSONDecodeError, TypeError) as e:
                print(f"Warning: The workflow registry file {REGISTRY_FILE_PATH} is corrupted or badly formatted. It will be reset. Error: {e}")
                return set()
        return set() # Returns an empty set if the file doesn't exist

    def _save_registry(self):
        try:
            with REGISTRY_FILE_PATH.open("w") as f:
                json.dump(list(self._workflow_paths_registry), f, indent=2)
        except IOError as e:
            print(f"Critical error: Unable to write to workflow registry file {REGISTRY_FILE_PATH}. Error: {e}")


    def getWorkflows(self) -> list[str]:
        """
        Returns a list of absolute paths of registered and valid workflows.
        Cleans the registry of invalid paths.
        """
        current_registry = list(self._workflow_paths_registry) # Work on a copy for modification
        valid_paths_to_return = []
        registry_updated = False

        for path_str in current_registry:
            workflow_path = Path(path_str)
            # A valid workflow exists, is a directory, and contains graph.json (for example)
            if workflow_path.exists() and workflow_path.is_dir() and (workflow_path / "graph.json").exists():
                valid_paths_to_return.append(str(workflow_path))
            else:
                # This path is no longer valid, remove it from the main registry
                if path_str in self._workflow_paths_registry:
                    self._workflow_paths_registry.remove(path_str)
                print(f"Information: Invalid or deleted workflow path removed from registry: {path_str}")
                registry_updated = True
        
        if registry_updated:
            self._save_registry() 

        return sorted(valid_paths_to_return)


    def createWorkflow(self, name: str, parent_directory_path_str: str):
        """
        Creates a new workflow (folder) in the specified parent_directory_path_str.
        """
        try:
            parent_path = Path(parent_directory_path_str).resolve()
            if not parent_path.is_dir():
                return {"error": f"The specified parent path '{parent_directory_path_str}' is not a valid file or does not exist."}, 400
            # if not str(parent_path).startswith(str(Path.home())):
            #     return {"error": "The specified creation path is not allowed."}, 403

            # Full path to new workflow
            workflow_path = parent_path / name

            if workflow_path.exists():
                return {"error": f"A workflow named '{name}' already exists in '{parent_path}'."}, 409

            # Creating the workflow folder structure
            workflow_path.mkdir(parents=True)
            (workflow_path / "Thumbnails").mkdir(parents=True, exist_ok=True)
            (workflow_path / "Thumbnails" / ".keep").touch()
            (workflow_path / "Tools").mkdir(parents=True, exist_ok=True)
            # (workflow_path / "Tools" / ".keep").touch()
            (workflow_path / ".gitignore").write_text("Metadata/*/*data_frame.csv\nData/\nThumbnails/\n.DS_Store\n")
            with open(workflow_path / "graph.json", "w") as f:
                json.dump(DEFAULT_WORKFLOW_CONTENT, f, indent=2)
            
            # Add to registry
            self._workflow_paths_registry.add(str(workflow_path.resolve()))
            self._save_registry()
            
            return {"message": "Workflow successfully created.", "path": str(workflow_path)}, 201 # Created

        except ValueError as ve: 
            return {"error": f"The parent path provided is invalid: {ve}"}, 400
        except Exception as e:
            print(f"Server error during workflow creation: {e}")
            return {"error": f"An internal error occurred during workflow creation."}, 500



    def deleteWorkflow(self, workflow_full_path_str: str):
        workflow_path = Path(workflow_full_path_str).resolve()

        if not workflow_path.exists():
            return {"error": "Workflow not found"}, 404
        try:
            shutil.rmtree(workflow_path)
            # Remove from registry (convert to str for comparison with set elements)
            path_to_remove_str = str(workflow_path)
            if path_to_remove_str in self._workflow_paths_registry:
                self._workflow_paths_registry.remove(path_to_remove_str)
                self._save_registry()
            return {"message": "Workflow deleted", "name": workflow_full_path_str}, 200
        except Exception as e:
            return {"error": f"Failed to delete workflow: {str(e)}"}, 500

    def duplicateWorkflow(self, source_full_path_str: str, target_parent_path_str: str, target_name: str):
        source_path = Path(source_full_path_str).resolve()
        target_parent_path = Path(target_parent_path_str).resolve()
        target_path = target_parent_path / target_name

        # Validations
        # if not str(source_path).startswith(str(Path.home())) or \
        #    not str(target_parent_path).startswith(str(Path.home())): # Security check
        #      return {"error": "Duplication path not authorized."}, 403
        if not source_path.is_dir():
            return {"error": "Source workflow not found."}, 404
        if not target_parent_path.is_dir():
            return {"error": "Invalid target parent path for duplication."}, 400
        if target_path.exists():
            return {"error": "A workflow with the same name already exists at the destination."}, 409

        try:
            shutil.copytree(source_path, target_path)
            # Add the new duplicated workflow to the registry
            self._workflow_paths_registry.add(str(target_path.resolve()))
            self._save_registry()
            return {"message": "Workflow duplicated", "path": str(target_path)}, 201
        except Exception as e:
            return {"error": f"Duplication failed: {e}"}, 500

    def renameWorkflow(self, old_full_path_str: str, new_name: str):
        old_path = Path(old_full_path_str).resolve()
        # The new path will be in the same parent as the old one, with the new name
        new_path = old_path.parent / new_name

        # Validations (security, existence)
        # if not str(old_path).startswith(str(Path.home())): # Security check
        #      return {"error": "Rename path not authorized."}, 403
        if not old_path.is_dir():
            return {"error": f"Source workflow '{old_full_path_str}' not found."}, 404
        if new_path.exists():
            return {"error": f"A workflow named '{new_name}' already exists at this location."}, 409
        
        try:
            old_path.rename(new_path)
            # Update the registry
            if str(old_path) in self._workflow_paths_registry:
                self._workflow_paths_registry.remove(str(old_path))
                self._workflow_paths_registry.add(str(new_path))
                self._save_registry()
            return {"message": "Workflow renamed", "old_path": str(old_path), "new_path": str(new_path)}, 200
        except Exception as e:
            return {"error": f"Rename failed: {e}"}, 500
        
    def exportWorkflow(self, workflow_full_path_str: str) -> Path | dict:
        """
        Exports the specified workflow directory as a zip file.
        Args: workflow_full_path_str: The absolute path to the workflow directory.
        Returns:
            A Path object to the temporary zip file if successful,
            or a dictionary with an "error" key if an error occurred.
        """
        try:
            workflow_dir = Path(workflow_full_path_str).resolve()
            if not workflow_dir.is_dir(): # is_dir() also implies exists()
                return {"error": f"Workflow directory not found at: {workflow_full_path_str}"}

            # Create a temporary file for the zip archive.
            # delete=False is important because we return the path and delete it in the route handler.
            with tempfile.NamedTemporaryFile(delete=False, suffix=".zip", prefix=f"{workflow_dir.name}_") as tmp_zip_file:
                temp_zip_file_path = Path(tmp_zip_file.name)

            # Create the zip archive
            with zipfile.ZipFile(temp_zip_file_path, "w", zipfile.ZIP_DEFLATED) as zipf:
                for file_path in workflow_dir.rglob("*"):
                    if file_path.is_file(): 
                        # so the contents of workflow_dir are at the root of the zip.
                        arcname = file_path.relative_to(workflow_dir)
                        zipf.write(file_path, arcname)
            
            print(f"Workflow exported to temporary file: {temp_zip_file_path}")
            return temp_zip_file_path 
        except FileNotFoundError:
            return {"error": f"Workflow directory not found at: {workflow_full_path_str}"}
        except Exception as e:
            # Log the full error for server-side debugging
            print(f"Error during workflow export for '{workflow_full_path_str}': {e}")
            return {"error": f"An unexpected error occurred during export: {str(e)}"}
        
    def openWorkflowFromGraph(self, graph_json_path_str: str) -> dict:
        """
        Opens a workflow from a graph.json file path.
        Validates the parent folder as a workflow, registers it if new,
        and returns the graph data.
        This function combines validation, registration and reading logic.
        """
        registration_status = "unknown"
        try:
            graph_json_path = Path(graph_json_path_str).resolve(strict=True) # strict=True for FileNotFoundError
            
            if not graph_json_path.is_file() or graph_json_path.name != "graph.json":
                return {"error": f"The path '{graph_json_path_str}' does not point to a valid graph.json file."}

            workflow_path = graph_json_path.parent # The workflow folder is the parent of graph.json
            workflow_path_str = str(workflow_path) # Resolved absolute path

            if workflow_path_str not in self._workflow_paths_registry: # if not included in registry paths, add it
                self._workflow_paths_registry.add(workflow_path_str)
                self._save_registry()
                registration_status = "registered"
                print(f"DEBUG: Workflow '{workflow_path_str}' registered.")
            else:
                registration_status = "already_exists"
                print(f"DEBUG: Workflow '{workflow_path_str}' already in registry.")
           
            # graph reading logic
            try:
                with graph_json_path.open("r") as f:
                    graph_data = json.load(f)
            except json.JSONDecodeError:
                return {"error": f"JSON decoding error for graph.json in: {workflow_path_str}"}

            return {
                "success": True,
                "path": workflow_path_str,
                "graph_data": graph_data,
                "registration_status": registration_status
            }
        except FileNotFoundError:
            return {"error": f"Specified graph.json file not found: {graph_json_path_str}"}
        except Exception as e: # Catches other errors (e.g., Path() on invalid path)
            print(f"Error in openWorkflowFromGraph for {graph_json_path_str}: {e}")
            return {"error": f"Internal server error while opening workflow: {str(e)}"}

    def getToolsByWorkflow(self, workflow_full_path_str: str) -> list[str]:
        """
        Returns a list of tool names (absolute paths) in the specified workflow.
        """
        workflow_path = Path(workflow_full_path_str).resolve()
        tools_dir = workflow_path / "Tools"

        if not tools_dir.exists() or not tools_dir.is_dir():
            return []
        
        tool_paths = []
        for tool_path in tools_dir.rglob("*.py"):
            if tool_path.is_file():
                # Get relative path from workflow root
                relative_path = tool_path.relative_to(workflow_path)
                module_path = str(relative_path).replace("\\", "/")  # assure les slashs Unix
                absolute_path = str(tool_path.resolve())
                tool_paths.append({
                    "module_path": module_path,
                    "absolute_path": absolute_path
                })
        # List all tool directories (subdirectories) in the Tools directory
        # tool_paths = [str(tool_path.resolve()) for tool_path in tools_dir.rglob("*.py") if tool_path.is_file()]
        # return tool_paths
        return tool_paths
    

    def createSymbolicLink(self, workflow_full_path_str: str):
        """Create a symbolic link to the current workflow's Thumbnails folder only once."""
        try:
            # Get the current workflow path and its name.
            workflow_path = Path(workflow_full_path_str).resolve()
            workflow_name = Path(workflow_path).name

            # Build the server directory for this workflow.
            server_static_path = Path('server/static/images') / workflow_name
            server_static_path.mkdir(parents=True, exist_ok=True)

            # Resolve the absolute path of the Thumbnails folder in the workflow.
            thumbnails_path = (Path(workflow_path) / 'Thumbnails').resolve()
            if thumbnails_path.exists():
                # Define the target symbolic link path (using absolute paths to avoid recursion).
                target_link = (server_static_path / 'Thumbnails')
                
                # Check if the target_link already exists.
                if target_link.exists():
                    # If it's a symlink and it already points to the correct target, do nothing.
                    if target_link.is_symlink() and target_link.resolve() == thumbnails_path:
                        print(f"Symbolic link already exists: {target_link}")
                        return
                    else:
                        # Otherwise, remove the existing file/link.
                        target_link.unlink()
                
                # Create the symbolic link using the absolute path of the target.
                target_link.symlink_to(thumbnails_path, target_is_directory=True)
                print(f"Created symbolic link: {target_link} -> {thumbnails_path}")
                print(f"Accessible via: http://localhost:8000/images/{workflow_name}/Thumbnails/")
            else:
                print("The Thumbnails folder does not exist in the workflow.")
        except Exception as e:
            print(f"Error creating symbolic link: {e}")
    
    def convertAbsolutePathToUrl(self, abs_path, workflow_path:str):
        """
        Convert an absolute path to a URL format.
        Cut the absolute path to the workflow name and add the URL prefix (http://localhost:8000/images/).
        Example:
        Input: "/home/user/workflow_name/Thumbnails/node_name/image.png"
        Output: "http://localhost:8000/images/workflow_name/Thumbnails/node_name/image.png"
        """
        if abs_path is None:
            return None
        abs_path_str = str(abs_path)
        # Retrieve  the workflow name from the pyFlow instance
        workflow_name = Path(workflow_path).name
        # Check if the workflow name is in the absolute path
        if workflow_name in abs_path_str:
            # Get the relative path after the workflow name
            relative_path = abs_path_str.split(workflow_name, 1)[1].lstrip("/\\")
            # Construct the URL
            return f"http://localhost:8000/images/{workflow_name}/{relative_path}"
        return abs_path_str

    
    async def sendDataWebSocket(self, topic:str, data):
        """Convert all paths to thumbnail paths, add URL columns, and send data over WebSocket."""
        try:
            async with websockets.connect(self.ws_url) as websocket:
            
                if isinstance(data, pandas.DataFrame):
                    df = data.copy()
                    if not self.selected_node:
                        print("No selected node to send with WebSocket data.")
                        return

                    node_name = self.selected_node["data"]["tool"]["name"]

                    for column in df.columns:
                        df[column+'_thumbnail'] = df[column].map(lambda x: self.convertAbsolutePathToUrl(ThumbnailGenerator.get().getThumbnailPath(x)))
                    
                    # Permission request: the server will send a notification as soon as there is at least one subscriber.
                    await websocket.send(json.dumps({
                        "action": "wait_for_permission",
                        "topic": topic,
                    }))
                    # wait for the response
                    permission_response = await websocket.recv()
                    permission_data = json.loads(permission_response)

                    if permission_data.get("permission", False):
                        # Prepare the data to be sent
                        message_payload = {
                            "node": node_name,
                            "results": df.to_dict(orient="records")
                        }
                        message = {
                            "topic": "table_data",
                            "action": "publish",
                            "message": message_payload
                        }
                        await websocket.send(json.dumps(message, default=str))
                    else:
                        print("Permission not granted to publish on this topic.")
        except Exception as e:
            print(f"Client WebSocket status: {e}")
    

workflowManager = WorkflowManager() 