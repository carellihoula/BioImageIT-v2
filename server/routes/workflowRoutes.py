import os
from quart import Blueprint, jsonify, request
from quart.helpers import send_file
from pydantic import ValidationError

from src.WorkflowModule.WorkflowManager import (
    WorkflowManager,
    CreateWorkflowRequest,
    RenameRequest ,
    DuplicateRequest
)
workflow_bp = Blueprint('workflows', __name__, url_prefix='/api/workflows')

workflow_manager = WorkflowManager()

@workflow_bp.get("/")
async def listWorkflowsRoute():
    workflow_paths = workflow_manager.getWorkflows()
    return jsonify(workflow_paths), 200

@workflow_bp.post("/create")
async def createWorkflowRoute():
    payload = await request.get_json()
    if not payload:
        return jsonify({"error": "Missing JSON body"}), 400

    try:
        req_data = CreateWorkflowRequest(**payload)
        workflow_name = req_data.name
        parent_dir = req_data.path
    except ValidationError as e:
        return jsonify({"error": "Invalid query data", "details": e.errors()}), 400
    
    if not workflow_name.strip() or not parent_dir.strip():
        return jsonify({"error": "'name' and 'path' can't be empty"}), 400

    result, status_code = workflow_manager.createWorkflow(workflow_name, parent_dir)
    return jsonify(result), status_code

@workflow_bp.delete("/delete")
async def deleteWorkflowRoute():
    payload = await request.get_json()
    if not payload or 'path' not in payload:
        return jsonify({"error": "complete workflow path missing from JSON body"}), 400
    
    workflow_to_delete_path = payload['path']
    if not isinstance(workflow_to_delete_path, str) or not workflow_to_delete_path.strip():
        return jsonify({"error": "'name' must be a non-empty string"}), 400

    result, status_code = workflow_manager.deleteWorkflow(workflow_to_delete_path)
    return jsonify(result), status_code

@workflow_bp.post("/duplicate")
async def duplicateWorkflowRoute():
    payload = await request.get_json()
    if not payload: return jsonify({"error": "Missing JSON body"}), 400
    try:
        req_model = DuplicateRequest(**payload) 
    except ValidationError as e:
        return jsonify({"error": "Invalid query data for duplication", "details": e.errors()}), 400

    # The manager method expects source_full_path_str, target_parent_path_str, target_name
    result, status_code = workflow_manager.duplicateWorkflow(
        req_model.source_path, 
        req_model.target_parent_path, 
        req_model.target_name     
    )
    return jsonify(result), status_code


@workflow_bp.post("/rename")
async def renameWorkflowRoute():
    payload = await request.get_json()
    if payload is None: return jsonify({"error": "Request must be JSON"}), 400
    try:
        req_model = RenameRequest(**payload)
    except ValidationError as e:
        return jsonify({"error": "Invalid request data", "details": e.errors()}), 400

    result, status_code = workflow_manager.renameWorkflow(req_model.old_full_path, req_model.new_name)
    return jsonify(result), status_code

@workflow_bp.get("/export")
async def exportWorkflow():
    path = request.args.get('path')
    print(path)
    result = workflow_manager.exportWorkflow(path)

    if isinstance(result, dict) and "error" in result:
        return result
    zip_file_path = result
    return await send_file(
            zip_file_path,
            mimetype="application/zip",
            as_attachment=True,
            attachment_filename="temp.zip"
        )