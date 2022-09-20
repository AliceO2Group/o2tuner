"""
Useful classes to define and walk through directed acyclic graphs
"""

import sys
from o2tuner.log import Log

LOG = Log()


class GraphDAG:  # pylint: disable=too-few-public-methods
    """
    Class storing the configuration of a directed acyclic graph
    """
    def __init__(self, n_nodes, edges):
        """
        Init

        Args:
            n_nodes: int
                simply the number of nodes. Internally, the nodes will be range(n_nodes)
            edges: iter of 2-tuples
                iterable of edges with tuples (origin, target)
        """
        # Number of nodes
        self.n_nodes = n_nodes
        # edges
        self.edges = edges

        # Map nodes pointing towards a nodes
        self.from_nodes = [[] for _ in range(n_nodes)]
        # Map nodes to where this node points to
        self.to_nodes = [[] for _ in range(n_nodes)]
        # graph as 2D
        self.graph = [[False] * n_nodes for _ in range(n_nodes)]
        # Store the degree of incoming edges for each node (persistent)
        self.in_degree = [0] * self.n_nodes
        # Store the degree of outgoing edges for each node (persistent)
        self.out_degree = [0] * self.n_nodes
        # the index in the topology

        # Fill graph and in-degree
        for origin, target in self.edges:
            if self.graph[origin][target]:
                # We saw this edge already
                continue
            # Mark this edge as seen
            self.graph[origin][target] = True

            if origin > n_nodes or target > n_nodes or origin < 0 or target < 0:
                LOG.error(f"Found edge ({origin}, {target}) but nodes must be >= 0 and < {n_nodes}")
                sys.exit(1)
            self.from_nodes[target].append(origin)
            self.to_nodes[origin].append(target)
            self.in_degree[target] += 1
            self.out_degree[origin] += 1

        # Store at least one possible topology
        self.topology = []
        self.make_topology()

    def make_topology(self):
        """
        basically Kahn's algorithm to find a topology and to check for loops
        (which would then obviously not be a DAG)
        Returns True if sane and False if there is a cyclic path or an unknown node
        """
        # source nodes, no incoming edge
        in_degree = self.in_degree.copy()
        queue = [i for i, v in enumerate(in_degree) if not v]
        if not queue:
            LOG.error("There is no source node in the topology")
            return False

        counter = 0
        while queue:
            current = queue.pop(0)
            if current >= self.n_nodes or current < 0:
                LOG.error(f"Found an edge which node {current} but nodes are only valid from 0 to {self.n_nodes - 1}.")
                return False
            self.topology.append(current)
            for target in self.to_nodes[current]:
                in_degree[target] -= 1
                if not in_degree[target]:
                    queue.append(target)
            counter += 1
        if counter != self.n_nodes:
            LOG.error("There is at least one cyclic dependency.")
            return False
        return True


class GraphDAGWalker:
    """
    Find our way(s) through a DAG
    """
    def __init__(self, graph):
        """
        Init
        """
        self.graph = graph
        self.n_nodes = self.graph.n_nodes
        # Transient in degree which is updated whenever an origin node is done
        self.in_degree_transient = self.graph.in_degree.copy()
        # Flag done nodes
        self.done = []
        # As well as as a mask
        self.done_mask = [False] * self.n_nodes
        # mask those that must be done
        self.must_be_done = []
        self.must_be_done_mask = [False] * self.n_nodes
        # A transient topology
        self.topology_transient = None

    def get_can_be_done(self):
        """
        Simply get all nodes that are currently possible
        """
        return [i for i, idg in enumerate(self.in_degree_transient) if not idg and not self.done_mask[i]]

    def can_be_done(self, node):
        """
        Ask whether this node can be done
        """
        return not self.in_degree_transient[node]

    def set_done(self, node):
        """
        Report back here when a node is done
        """
        self.done.append(node)
        self.done_mask[node] = True

    def set_to_do(self, node):
        """
        Specify nodes to be done
        """
        self.must_be_done.append(node)
        self.must_be_done_mask[node] = True

    def find_shortest_path_to(self, targets, visited, done_mask, topology):
        """
        Recursively find shortest path to a target node
        """

        queue = targets.copy()
        while queue:
            next_target = queue.pop()
            if visited[next_target]:
                continue
            visited[next_target] = True
            topology.append(next_target)
            for origin in self.graph.from_nodes[next_target]:
                if not done_mask[origin]:
                    queue.append(origin)
        topology.reverse()

    def compute_topology(self):
        """
        Compute an efficient topology
        """
        # Nodes that should be done superseed the fact that they are potentially done already
        done_mask = self.done_mask.copy()
        done = []
        self.in_degree_transient = self.graph.in_degree.copy()
        # Sort according to topology
        must_be_done = [node for node in self.graph.topology if self.must_be_done_mask[node]]

        for node in self.done:
            if self.must_be_done_mask[node]:
                done_mask[node] = False
                continue
            done.append(node)

        for node in done:
            for target in self.graph.to_nodes[node]:
                self.in_degree_transient[target] -= 1

        self.topology_transient = []
        if not self.must_be_done:
            # If nothing specified to be done, just return the topology minus the tasks that were masked as done
            self.topology_transient = [n for n in self.graph.topology if not done_mask[n]]
            return self.topology_transient

        visited = [False] * self.n_nodes
        self.find_shortest_path_to(must_be_done, visited, done_mask, self.topology_transient)

        return self.topology_transient


def create_graph_walker(n_nodes, edges):
    """
    Directly create an object to walk through a GraphDAG
    """
    return GraphDAGWalker(GraphDAG(n_nodes, edges))
