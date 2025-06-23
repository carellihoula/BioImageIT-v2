import os
from pathlib import Path
from fastapi import APIRouter, HTTPException
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from src.Packages.FunctionLibraries.BiitLib import load_tools_info, loadTool, toolsPath
from src.Packages.FunctionLibraries.ToolGenerator import write_tool_file
from shutil import copy2

tool_router = APIRouter(prefix="/api/tools", tags=["tools"])

@tool_router.get("/")
async def getTools(toolsWorkflow: str):
    """
    endpoint to retrieve all tools
    """
    tools_info = load_tools_info(toolsPath, toolsWorkflow)
    # print(f'tools_info: {tools_info}')
    return JSONResponse(content=tools_info, status_code=200)

class ToolInput(BaseModel):
    filename: str
    current_workflow: str

@tool_router.post("/")
async def create_tool(tool: ToolInput):
    current_workflow_tools_path = Path(tool.current_workflow) / "Tools"

    if not current_workflow_tools_path.exists():
        raise HTTPException(status_code=404, detail="Workflow tools folder does not exist")
    
    tool_file_path = current_workflow_tools_path / tool.filename / f"{tool.filename}.py"

    if tool_file_path.exists():
        raise HTTPException(status_code=400, detail="Tool already exists")

    try:
        tool_file_path.parent.mkdir(parents=True, exist_ok=True)
        # Write Python tool file
        write_tool_file(tool_file_path, tool.filename)
        # Load the tool to register it
        loadTool(tool_file_path)

        return JSONResponse(content={"message": "Tool created and loaded successfully"}, status_code=201)

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to create tool: {e}")