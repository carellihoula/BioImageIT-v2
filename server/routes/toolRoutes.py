import os
from src.Packages.FunctionLibraries.BiitLib import load_tools_info, toolsPath
from quart import Blueprint, jsonify, request

from pathlib import Path

tool_bp = Blueprint('tools', __name__, url_prefix='/api/tools')




@tool_bp.get("/")
async def getTools():
    tools_info = load_tools_info(toolsPath)
    return  jsonify(tools_info), 200