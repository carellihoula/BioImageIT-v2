import os
import sys
from pathlib import Path
# import json

def get_root_path():
    return Path(__file__).parent.parent

APP_NAME = "BioImageIT"

def get_app_data():
    if sys.platform == "win32":
        data_path = Path(os.getenv("APPDATA", Path.home())) / APP_NAME

    elif sys.platform == "darwin":  # macOS
        data_path = Path.home() / "Library" / "Application Support" / APP_NAME

    else:  # Assume Linux/Unix
        data_path = Path.home() / ".config" / APP_NAME

    # Ensure the directory exists
    data_path.parent.mkdir(parents=True, exist_ok=True)

    return data_path


def reactflow_to_dag_nodes(graph_json):
    nodes = graph_json["nodes"]
    edges = graph_json["edges"]

    # Build the input map for each node
    node_inputs = {node["id"]: [] for node in nodes}
    for edge in edges:
        target = edge["target"]
        source = edge["source"]
        node_inputs[target].append(source)

    dag_nodes = {}
    for node in nodes:
        node_id = node["id"]
        tool = node["data"]["tool"]
        
        tool_key = tool["path"].split('/')[-1].replace('.py', '')
        parameters = {}
        for inp in tool.get("inputs", []):
            if "value" in inp:
                parameters[inp["name"]] = inp["value"]
            else:
                parameters[inp["name"]] = inp.get("default", None)
        dag_nodes[node_id] = {
            "task": tool_key,
            "inputs": node_inputs[node_id],
            "parameters": parameters
        }
    return dag_nodes


class DictToObject(object):
    def __init__(self, d):
        for key, value in d.items():
            if isinstance(value, dict):
                setattr(self, key, DictToObject(value))
            else:
                setattr(self, key, value)