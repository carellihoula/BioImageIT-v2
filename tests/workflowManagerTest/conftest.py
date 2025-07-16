import pytest
import tempfile
import shutil
from pathlib import Path
from src.WorkflowModule.WorkflowManager import WorkflowManager, REGISTRY_FILE_PATH

@pytest.fixture
def temp_dir():
    tmp = tempfile.mkdtemp()
    yield tmp
    shutil.rmtree(tmp)

@pytest.fixture
def manager(temp_dir, monkeypatch):
    """
    Redirect storage folder |
    monkeypatch lets you temporarily modify or replace objects, variables, functions, attributes 
        or even entire modules during test execution.
    """
   
    monkeypatch.setattr("src.WorkflowModule.WorkflowManager.BASE_WORKFLOWS_STORAGE", Path(temp_dir))
    monkeypatch.setattr("src.WorkflowModule.WorkflowManager.REGISTRY_FILE_PATH", Path(temp_dir) / ".workflow_registry.json")
    return WorkflowManager()
