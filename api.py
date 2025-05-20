# BIOIMAGEIT/api.py
import json
import os
import webview
import base64 
from pathlib import Path
from src.Packages.Tools.CodeServerTool import CodeServerTool
from src.WorkflowModule.WorkflowManager import WorkflowManager
   


class Api:
    """
    API class whose methods can be called from JavaScript.
    """
    def __init__(self):
        self.workflow_manager = WorkflowManager()
        self.codeserver = CodeServerTool()

    def launchCodeServer(self):
        self.codeserver.init_and_launch_code_server()
        return {'status': 'starting' if not self.codeserver.environment_ready else 'already_started'}

    def selectFolderDialog(self):
        """
        Opens a native dialog to select a folder.
        Returns the selected folder path or None if cancelled.
        """
        active_window = webview.active_window()
        if not active_window:
            print("API Error: No active pywebview window found to parent the dialog.")
            return None

        try:
            file_paths = active_window.create_file_dialog(
                webview.FOLDER_DIALOG,  # Specify folder selection
                allow_multiple=False   
            )

            if file_paths and len(file_paths) > 0:
                return file_paths[0]  # Return the first (and only) selected folder path
            else:
                # User cancelled the dialog or no folder was selected
                return None
        except Exception as e:
            print(f"API Error in select_folder_dialog: {e}")
            return None
        
        
    def saveFileDialog(self, filename: str, base64_data: str):
        """
        Opens a native "Save File" dialog and saves the provided base64 data.
        Returns a dictionary with "path" on success or "error" on failure.
        """
        active_window = webview.active_window()
        if not active_window:
            return {"error": "No active window to display save dialog."}

        try:
            save_path_tuple = active_window.create_file_dialog(
                webview.SAVE_DIALOG,
                directory=str(Path.home() / "Downloads"), # Suggestion de répertoire
                save_filename=filename
            )

            if save_path_tuple:
                save_path_str = save_path_tuple[0] if isinstance(save_path_tuple, tuple) else save_path_tuple
                if not save_path_str:
                    return {"error": "Save dialog cancelled by user."}

                save_path = Path(save_path_str)
                file_content = base64.b64decode(base64_data)
                with save_path.open("wb") as f:
                    f.write(file_content)
                return {"path": str(save_path)}
            else:
                return {"error": "Save dialog cancelled or no path chosen."}
        except Exception as e:
            return {"error": f"Error during save process: {str(e)}"}


    def exportWorkflowDirectSave(self, workflow_full_path_str: str):
        """
        Exports a workflow to a zip, then prompts the user to save it.
        This method is called from JavaScript.
        """
        if not workflow_full_path_str or not workflow_full_path_str.strip():
            return {"error": "Workflow path was not provided."}

        # Use WorkflowManager to create the temporary zip file
        # exportWorkflow returns a Path object to the temporary zip file or an error dict.
        temp_zip_file_path_or_error = self.workflow_manager.exportWorkflow(workflow_full_path_str)

        if isinstance(temp_zip_file_path_or_error, dict) and "error" in temp_zip_file_path_or_error:
            print(f"Python API: WorkflowManager.exportWorkflow error: {temp_zip_file_path_or_error['error']}")
            return temp_zip_file_path_or_error # Return error to frontend

        temp_zip_file_path = temp_zip_file_path_or_error # It's a Path object

        # Read the temporary zip file content in base64
        base64_content = None
        suggested_filename = Path(workflow_full_path_str).name + ".zip" # Default name for saving

        try:
            if not temp_zip_file_path.is_file(): # Additional check
                 return {"error": f"Temporary zip file not found at {temp_zip_file_path}"}

            with open(temp_zip_file_path, "rb") as f_zip:
                zip_bytes = f_zip.read()
            base64_content = base64.b64encode(zip_bytes).decode('utf-8')
            print(f"Python API: Zip file read and encoded in base64 (bytes size: {len(zip_bytes)})")
        except Exception as e:
            print(f"Python API: Error while reading or encoding temporary zip file: {e}")
            return {"error": f"Error while preparing file for save: {str(e)}"}
        finally:
            # Delete temporary zip file in all cases
            try:
                if temp_zip_file_path.exists(): # Check before deleting
                    os.remove(temp_zip_file_path)
                    # print(f"Python API: Temporary zip file {temp_zip_file_path} deleted.")
            except Exception as e_del:
                print(f"Python API: Warning - Failed to delete temporary zip file {temp_zip_file_path}: {e_del}")

        if base64_content is None: # If an error occurred before getting content
            return {"error": "Unable to get zip file content."}

        # 4. Call saveFileDialog for user to choose where to save
        print(f"Python API: Calling saveFileDialog with filename: {suggested_filename}")
        return self.saveFileDialog(suggested_filename, base64_content)


    def openWorkflowFromSelectedFolder(self):
        active_window = webview.active_window()
        if not active_window:
            return {"error": "No active window."}

        try:
            folder_path_tuple = active_window.create_file_dialog(webview.FOLDER_DIALOG)
            if not folder_path_tuple or not folder_path_tuple[0]:
                return {"error": "File selection cancelled."}
            selected_folder_path_str = folder_path_tuple[0]
            graph_json_path_str = str(Path(selected_folder_path_str) / "graph.json")

            return self.workflow_manager.openWorkflowFromGraph(graph_json_path_str)

        except Exception as e:
            return {"error": f"Erreur interne du serveur : {str(e)}"}
        
    def saveWorkflow(self, path: str, graph: dict):
        try:
            file_path = os.path.join(path, "graph.json")
            if not os.path.isdir(path):
                return { "success": False, "error": f"Directory does not exist: {path}" }
            with open(file_path, "w", encoding="utf-8") as f:
                json.dump(graph, f, ensure_ascii=False, indent=2)
            return { "success": True, "message": f"Graph saved to {file_path}" }
        except Exception as e:
            return { "success": False, "error": str(e) }
        
    def loadWorkflow(self, path: str):
        try:
            file_path = os.path.join(path, "graph.json")
            with open(file_path, "r", encoding="utf-8") as f:
                data = json.load(f)
            return { "success": True, "data": data }
        except Exception as e:
            return { "success": False, "error": str(e) }
