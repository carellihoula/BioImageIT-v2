import os
from pathlib import Path
from fastapi import APIRouter
from fastapi.responses import JSONResponse
from src.Packages.FunctionLibraries.BiitLib import load_tools_info, toolsPath

tool_router = APIRouter(prefix="/api/tools", tags=["tools"])

@tool_router.get("/")
async def getTools():
    """
    endpoint to retrieve all tools
    """
    tools_info = load_tools_info(toolsPath)
    return JSONResponse(content=tools_info, status_code=200)
