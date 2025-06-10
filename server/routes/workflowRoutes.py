from fastapi import APIRouter, Request, HTTPException, Query
from fastapi.responses import JSONResponse, FileResponse
from pydantic import ValidationError
from typing import Optional

from src.WorkflowModule.WorkflowManager import (
    WorkflowManager,
    CreateWorkflowRequest,
    RenameRequest,
    DuplicateRequest
)

workflow_router = APIRouter(prefix="/api/workflows", tags=["workflows"])

workflow_manager = WorkflowManager()


@workflow_router.get("/")
async def list_workflows():
    workflow_paths = workflow_manager.getWorkflows()
    return JSONResponse(content=workflow_paths)


@workflow_router.post("/create")
async def create_workflow(request: Request):
    payload = await request.json()
    if not payload:
        raise HTTPException(status_code=400, detail="Missing JSON body")

    try:
        req_data = CreateWorkflowRequest(**payload)
    except ValidationError as e:
        raise HTTPException(status_code=400, detail={"error": "Invalid query data", "details": e.errors()})

    if not req_data.name.strip() or not req_data.path.strip():
        raise HTTPException(status_code=400, detail="'name' and 'path' can't be empty")

    result, status_code = workflow_manager.createWorkflow(req_data.name, req_data.path)
    return JSONResponse(content=result, status_code=status_code)


@workflow_router.delete("/delete")
async def delete_workflow(request: Request):
    payload = await request.json()
    if not payload or 'path' not in payload:
        raise HTTPException(status_code=400, detail="complete workflow path missing from JSON body")

    workflow_to_delete_path = payload['path']
    if not isinstance(workflow_to_delete_path, str) or not workflow_to_delete_path.strip():
        raise HTTPException(status_code=400, detail="'path' must be a non-empty string")

    result, status_code = workflow_manager.deleteWorkflow(workflow_to_delete_path)
    return JSONResponse(content=result, status_code=status_code)


@workflow_router.post("/duplicate")
async def duplicate_workflow(request: Request):
    payload = await request.json()
    if not payload:
        raise HTTPException(status_code=400, detail="Missing JSON body")

    try:
        req_model = DuplicateRequest(**payload)
    except ValidationError as e:
        raise HTTPException(status_code=400, detail={"error": "Invalid query data for duplication", "details": e.errors()})

    result, status_code = workflow_manager.duplicateWorkflow(
        req_model.source_path,
        req_model.target_parent_path,
        req_model.target_name
    )
    return JSONResponse(content=result, status_code=status_code)


@workflow_router.post("/rename")
async def rename_workflow(request: Request):
    payload = await request.json()
    if payload is None:
        raise HTTPException(status_code=400, detail="Request must be JSON")

    try:
        req_model = RenameRequest(**payload)
    except ValidationError as e:
        raise HTTPException(status_code=400, detail={"error": "Invalid request data", "details": e.errors()})

    result, status_code = workflow_manager.renameWorkflow(req_model.old_full_path, req_model.new_name)
    return JSONResponse(content=result, status_code=status_code)


@workflow_router.get("/export")
async def export_workflow(path: Optional[str] = Query(None)):
    if not path:
        raise HTTPException(status_code=400, detail="Missing 'path' query parameter")

    result = workflow_manager.exportWorkflow(path)

    if isinstance(result, dict) and "error" in result:
        # Returns error in JSON
        return JSONResponse(content=result, status_code=400)

    zip_file_path = result

    return FileResponse(
        path=zip_file_path,
        media_type="application/zip",
        filename="temp.zip",
    )
