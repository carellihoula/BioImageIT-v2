import os
from pathlib import Path
from fastapi import APIRouter, HTTPException
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from src.Packages.FunctionLibraries.BiitLib import load_tools_info, loadTool, toolsPath
from src.Packages.FunctionLibraries.ToolGenerator import write_tool_file

tool_router = APIRouter(prefix="/api/tools", tags=["tools"])

@tool_router.get("/")
async def getTools():
    """
    endpoint to retrieve all tools
    """
    tools_info = load_tools_info(toolsPath)
    # print(f'tools_info: {tools_info}')
    return JSONResponse(content=tools_info, status_code=200)

class ToolInput(BaseModel):
    name: str
    folder: str
    filename: str

@tool_router.post("/")
async def create_tool(tool: ToolInput):
    tool_folder_path = toolsPath / tool.folder
    tool_file_path = tool_folder_path / f"{tool.filename}.py"

    if not tool_folder_path.exists():
        tool_folder_path.mkdir(parents=True, exist_ok=True)

    if tool_file_path.exists():
        raise HTTPException(status_code=400, detail="Tool already exists")

    try:
        # Write Python tool file
        write_tool_file(tool_file_path, tool.name)

        # Load the tool to register it
        loadTool(tool_file_path)

        return JSONResponse(content={"message": "Tool created and loaded successfully"}, status_code=201)

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to create tool: {e}")