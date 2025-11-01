"""DAG builder and topological sort for generation order."""

import networkx as nx
from typing import List, Set, Dict
import logging

from datagen.core.schema import Dataset, Node

logger = logging.getLogger(__name__)


class DAGBuilder:
    """Build dependency graph and determine generation order."""

    def __init__(self, dataset: Dataset):
        self.dataset = dataset
        self.nodes_by_id: Dict[str, Node] = {n.id: n for n in dataset.nodes}
        self.graph = nx.DiGraph()

    def build(self) -> List[List[str]]:
        """
        Build DAG and return topological generations (levels).

        Returns:
            List of levels, where each level is a list of node ids that can
            be generated in parallel.

        Raises:
            ValueError: If circular dependencies detected
        """
        # If DAG explicitly provided in schema, validate and return it
        if self.dataset.dag:
            logger.info("Using explicit DAG from schema")
            self._validate_explicit_dag()
            return self.dataset.dag

        # Otherwise, infer from parents and references
        logger.info("Inferring DAG from dependencies")
        self._infer_dependencies()
        self._check_cycles()
        return self._topological_generations()

    def _validate_explicit_dag(self):
        """Validate that explicit DAG is valid (no cycles, all nodes present)."""
        # Already validated in schema that all node ids are present
        # Check for implicit ordering consistency
        seen = set()
        for level in self.dataset.dag:
            for node_id in level:
                if node_id in seen:
                    raise ValueError(f"Node {node_id} appears multiple times in DAG")
                seen.add(node_id)

                # Check that parents appear in earlier levels
                node = self.nodes_by_id[node_id]
                if node.parents:
                    for parent_id in node.parents:
                        if parent_id not in seen:
                            raise ValueError(
                                f"Node {node_id} references parent {parent_id} "
                                f"which appears later in DAG"
                            )

    def _infer_dependencies(self):
        """Infer dependencies from parents and column references."""
        # Add all nodes to graph
        for node_id in self.nodes_by_id:
            self.graph.add_node(node_id)

        # Add edges from dependencies
        for node in self.dataset.nodes:
            dependencies = self._find_dependencies(node)
            for dep in dependencies:
                # Edge from dependency to node (dep must come before node)
                self.graph.add_edge(dep, node.id)
                logger.debug(f"Dependency: {dep} -> {node.id}")

    def _find_dependencies(self, node: Node) -> Set[str]:
        """
        Find all nodes that this node depends on.

        Dependencies come from:
        1. Explicit parents
        2. lookup generator references (table.column)
        3. choices_ref references (table.column)
        """
        deps = set()

        # 1. Explicit parents
        if node.parents:
            deps.update(node.parents)

        # 2. Column-level references
        for col in node.columns:
            gen = col.generator

            # lookup generator
            if "lookup" in gen:
                from_ref = gen["lookup"].get("from", "")
                if "." in from_ref:
                    table_id = from_ref.split(".")[0]
                    if table_id != node.id:  # Don't create self-loop
                        deps.add(table_id)

            # choice with choices_ref
            if "choice" in gen:
                choices_ref = gen["choice"].get("choices_ref", "")
                if choices_ref and "." in choices_ref:
                    table_id = choices_ref.split(".")[0]
                    if table_id != node.id:
                        deps.add(table_id)

        return deps

    def _check_cycles(self):
        """Check for circular dependencies."""
        try:
            cycles = list(nx.simple_cycles(self.graph))
            if cycles:
                raise ValueError(f"Circular dependencies detected: {cycles}")
        except nx.NetworkXNoCycle:
            pass

    def _topological_generations(self) -> List[List[str]]:
        """
        Compute topological generations (levels) using NetworkX.

        Returns levels where each level contains nodes with no dependencies
        on later levels.
        """
        try:
            generations = list(nx.topological_generations(self.graph))
            logger.info(f"Generated {len(generations)} levels")
            for i, level in enumerate(generations):
                logger.debug(f"  Level {i}: {sorted(level)}")
            return [sorted(level) for level in generations]
        except nx.NetworkXError as e:
            raise ValueError(f"Cannot create topological sort: {e}")


def build_dag(dataset: Dataset) -> List[List[str]]:
    """
    Build DAG and return generation order.

    Args:
        dataset: Validated dataset schema

    Returns:
        List of generation levels (each level can be generated in parallel)

    Raises:
        ValueError: If cycles detected or invalid dependencies
    """
    builder = DAGBuilder(dataset)
    return builder.build()
