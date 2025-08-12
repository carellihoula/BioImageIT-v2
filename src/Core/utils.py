import os
import sys
from pathlib import Path
# import json

def get_root_path():
    return Path(__file__).parents[2].resolve()

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
        name = tool["name"]
        isFileList = name == "List Files"
        
        tool_key = tool["path"].split('/')[-1].replace('.py', '')
        parameters = {}
        for inp in tool.get("inputs", []):
            param_name = inp["name"]
            # if "value" in inp:
            #     parameters[inp["name"]] = inp["value"]
            # else:
            #     parameters[inp["name"]] = inp.get("default", None)
            if inp.get("autoColumn", False) and not isFileList:
                # Find the source that feeds this parameter
                source_nodes = node_inputs.get(node_id, [])

                # Here we assume that the first source is the one that provides the column.
                if source_nodes:
                    source_node = source_nodes[0]
                    # By default, the column is “path” unless specified.
                    col_name = inp.get("columnName", "path")
                    parameters[param_name] = {
                        "type": "column",
                        "source_node": source_node,
                        "columnName": col_name,
                    }
                else:
                    # No source connected
                    parameters[param_name] = {
                        "type": "constant",
                        "value": inp.get("default", None),
                    }
            else:
                # Constant value
                if "value" in inp:
                    parameters[param_name] = inp["value"]
                else:
                    parameters[param_name] = inp.get("default", None)

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