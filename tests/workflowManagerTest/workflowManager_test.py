import pytest
from unittest.mock import MagicMock
from pathlib import Path
from src.WorkflowModule.WorkflowManager import WorkflowManager

class TestWorkflowManager:
    def test_create_workflow(self, manager, temp_dir):
        resp, status = manager.createWorkflow("MyWorkflow", temp_dir)
        assert status == 201
        assert "MyWorkflow" in resp["path"]
        assert (Path(resp["path"]) / "graph.json").exists()

    def test_delete_workflow(self, manager, temp_dir):
        _, status = manager.createWorkflow("ToDelete", temp_dir)
        path = Path(temp_dir) / "ToDelete"
        assert path.exists()

        resp, code = manager.deleteWorkflow(str(path))
        assert code == 200
        assert resp["message"] == "Workflow deleted"
        assert not path.exists()

    def test_duplicate_workflow(self, manager, temp_dir):
        manager.createWorkflow("SourceWF", temp_dir)
        source = Path(temp_dir) / "SourceWF"
        target_name = "CopyWF"

        resp, code = manager.duplicateWorkflow(str(source), temp_dir, target_name)
        assert code == 201
        assert (Path(temp_dir) / target_name).exists()

    def test_rename_workflow(self, manager, temp_dir):
        manager.createWorkflow("OldName", temp_dir)
        old_path = Path(temp_dir) / "OldName"
        new_name = "NewName"

        resp, code = manager.renameWorkflow(str(old_path), new_name)
        new_path = old_path.parent / new_name
        assert code == 200
        assert new_path.exists()
        assert not old_path.exists()

    def test_open_from_graph(self, manager, temp_dir):
        _, status = manager.createWorkflow("TestWF", temp_dir)
        graph_path = Path(temp_dir) / "TestWF" / "graph.json"
        result = manager.openWorkflowFromGraph(str(graph_path))

        assert result["success"]
        assert result["path"] == str(graph_path.parent.resolve())
        assert result["graph_data"] == {
            "nodes": [], "edges": [], "viewport": {"x": 0, "y": 0, "zoom": 1}
        }

    def test_export_workflow(self, manager, temp_dir):
        resp, status = manager.createWorkflow("ExportWF", temp_dir)
        wf_path = resp["path"]

        zip_path = manager.exportWorkflow(wf_path)
        assert isinstance(zip_path, Path)
        assert zip_path.suffix == ".zip"
        assert zip_path.exists()

        zip_path.unlink()  # Cleanup

    def test_get_tools(self, manager, temp_dir):
        resp, status = manager.createWorkflow("ToolWF", temp_dir)
        tools_path = Path(resp["path"]) / "Tools"
        tools_path.mkdir(parents=True, exist_ok=True)
        (tools_path / "my_tool.py").write_text("print('tool')")

        tools = manager.getToolsByWorkflow(resp["path"])
        assert len(tools) == 1
        assert tools[0]["module_path"] == "Tools/my_tool.py"

    def test_get_workflows(self, manager, temp_dir):

        # Mock _save_registry to avoid side effects
        manager._save_registry = MagicMock()

        # Create valid workflow
        valid_workflow = Path(temp_dir) / "ValidWorkflow"
        valid_workflow.mkdir()
        (valid_workflow / "graph.json").write_text("{}")

        # Create invalid workflow (no graph.json)
        invalid_workflow = Path(temp_dir) / "InvalidWorkflow"
        invalid_workflow.mkdir()

        # Create non-existing path
        non_existing_path = Path(temp_dir) / "DoesNotExist"

        # Set the registry with mixed paths
        manager._workflow_paths_registry = [
            str(valid_workflow),
            str(invalid_workflow),
            str(non_existing_path)
        ]

        # Run
        result = manager.getWorkflows()

        # Validate
        assert result == [str(valid_workflow)]
        assert str(valid_workflow) in manager._workflow_paths_registry
        assert str(invalid_workflow) not in manager._workflow_paths_registry
        assert str(non_existing_path) not in manager._workflow_paths_registry

        # Ensure _save_registry was called since registry changed
        manager._save_registry.assert_called_once()
