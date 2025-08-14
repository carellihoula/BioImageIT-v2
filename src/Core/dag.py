from pathlib import Path
import networkx as nx

from wetlands.environment_manager import EnvironmentManager
from src.Core.node import Node

class DAG:

    def __init__(self, environment_manager: EnvironmentManager, nodes: dict, tools: dict, workflowPath: Path) -> None:
        self._environment_manager = environment_manager
        self.G = self.create(nodes, tools, workflowPath)

    def create(self, nodes: dict, tools: dict, workflowPath: Path) -> nx.DiGraph:
        # Build graph with node metadata
        G = nx.DiGraph()
        for node_name, node_data in nodes.items():
            name = node_data["task"]
            node = Node(self._environment_manager, tools[name]["path"], tools[name]["module"].Tool(), tools[name]["module_import_path"], workflowPath, False)
            node_data['node'] = node
            G.add_node(node_name, **node_data)
            for input_node in node_data["inputs"]:
                G.add_edge(input_node, node_name)
        return G

    def set_successors_dirty(self, node: str):
        for successor_node in self.G.successors(node):
            self.G.nodes[successor_node]["node"].setDirty(True)

    def set_node_parameters(self, node: str, parameters: dict):
        data = self.G.nodes[node]
        data.set("parameters", parameters)
        self.set_successors_dirty(node)
        inputs = data["inputs"]
        input_dataframes = [self.dataframes[inp] for inp in inputs]
        self.dataframes[node] = data["node"].processDataFrame(input_dataframes, parameters=parameters)
    
    def process(self, type: str)-> dict:
        print("process", type)
        # Storage for results of each node
        self.dataframes = {}

        # Execute all nodes in topological order
        execution_order = list(nx.topological_sort(self.G))
        for node in execution_order:
            print("  process", node)
            data = self.G.nodes[node]

            inputs = data["inputs"]
            params = data.get("parameters", {})

            # Resolve inputs from results
            input_dataframes = [self.dataframes[inp] for inp in inputs]

            # Execute the task
            if type == "dataframe":
                self.dataframes[node] = data["node"].processDataFrame(input_dataframes, parameters=params)
            else:
                self.dataframes[node] = data["node"].processData(input_dataframes, parameters=params)


        return self.dataframes

    def exit_environments(self)-> None:

        execution_order = list(nx.topological_sort(self.G))
        for node in execution_order:
            environment = self.G.nodes[node]["node"].tool.environment
            if environment in self._environment_manager.environments:
                self._environment_manager.environments[environment].exit()
        return None