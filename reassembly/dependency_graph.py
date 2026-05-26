"""
Dependency graph built from the converted module list.

Provides:
  • Topological build order  (dependencies compiled before dependents)
  • Cycle detection          (circular imports surfaced as warnings)
  • Microservice grouping    (layer-based clustering)
  • Serialisation            (to_dict → saved as output/assembled/dependency_graph.json)
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Set


# ── Node ──────────────────────────────────────────────────────────────────────

@dataclass
class DepNode:
    name:         str
    layer:        str
    package:      str
    dependencies: List[str] = field(default_factory=list)
    dependents:   List[str] = field(default_factory=list)   # reverse edges


# ── Layer → microservice group mapping ───────────────────────────────────────

_LAYER_GROUP: Dict[str, str] = {
    "model":          "domain",
    "dto":            "domain",
    "repository":     "data",
    "service":        "service",
    "controller":     "api",
    "exception":      "shared",
    "config":         "shared",
    "utility":        "shared",
    "infrastructure": "shared",
}


# ── Graph ─────────────────────────────────────────────────────────────────────

class DependencyGraph:
    def __init__(self, modules: List[Dict]) -> None:
        self.nodes: Dict[str, DepNode] = {}
        self._build(modules)

    # ── Construction ──────────────────────────────────────────────────────────

    def _build(self, modules: List[Dict]) -> None:
        for m in modules:
            name = m.get("name", "")
            if not name:
                continue
            self.nodes[name] = DepNode(
                name=name,
                layer=m.get("microservice_type", m.get("layer", "unknown")),
                package=m.get("package", "com.bank.legacy"),
                dependencies=[
                    d for d in m.get("dependencies", [])
                    if d and d != name          # exclude self-refs
                ],
            )

        # Build reverse edges
        for name, node in self.nodes.items():
            for dep in node.dependencies:
                if dep in self.nodes:
                    self.nodes[dep].dependents.append(name)

    # ── Topological sort ──────────────────────────────────────────────────────

    def topological_sort(self) -> List[str]:
        """Return module names in build order (deepest dependency first)."""
        visited:  Set[str] = set()
        ordering: List[str] = []

        def _dfs(name: str, path: Set[str]) -> None:
            if name in path or name not in self.nodes:
                return
            if name in visited:
                return
            path = path | {name}
            for dep in self.nodes[name].dependencies:
                _dfs(dep, path)
            visited.add(name)
            ordering.append(name)

        for name in self.nodes:
            _dfs(name, set())

        return ordering

    # ── Cycle detection ───────────────────────────────────────────────────────

    def detect_cycles(self) -> List[List[str]]:
        """Return a list of cyclic paths (each cycle as an ordered list of names)."""
        cycles:   List[List[str]] = []
        visited:  Set[str]        = set()

        def _dfs(name: str, path: List[str], path_set: Set[str]) -> None:
            if name in path_set:
                start = path.index(name)
                cycles.append(path[start:] + [name])
                return
            if name in visited or name not in self.nodes:
                return
            path.append(name)
            path_set.add(name)
            for dep in self.nodes[name].dependencies:
                _dfs(dep, path[:], path_set.copy())
            path.pop()
            path_set.discard(name)
            visited.add(name)

        for name in self.nodes:
            if name not in visited:
                _dfs(name, [], set())

        # Deduplicate cycles (same set of nodes, different entry point)
        seen_sets: List[frozenset] = []
        unique: List[List[str]] = []
        for c in cycles:
            fs = frozenset(c)
            if fs not in seen_sets:
                seen_sets.append(fs)
                unique.append(c)
        return unique

    # ── Microservice grouping ─────────────────────────────────────────────────

    def microservice_groups(self) -> Dict[str, List[str]]:
        """Cluster modules into logical microservice layers."""
        groups: Dict[str, List[str]] = {}
        for name, node in self.nodes.items():
            group = _LAYER_GROUP.get(node.layer, "shared")
            groups.setdefault(group, []).append(name)
        return {k: sorted(v) for k, v in sorted(groups.items())}

    # ── Stats ─────────────────────────────────────────────────────────────────

    def most_depended_on(self, top_n: int = 5) -> List[Dict]:
        """Return the top-N modules that others depend on most."""
        ranked = sorted(
            self.nodes.values(),
            key=lambda n: len(n.dependents),
            reverse=True,
        )
        return [
            {"name": n.name, "layer": n.layer, "dependent_count": len(n.dependents)}
            for n in ranked[:top_n]
        ]

    # ── Serialisation ─────────────────────────────────────────────────────────

    def to_dict(self) -> Dict:
        cycles = self.detect_cycles()
        return {
            "total_modules":       len(self.nodes),
            "build_order":         self.topological_sort(),
            "microservice_groups": self.microservice_groups(),
            "circular_deps":       cycles,
            "has_cycles":          len(cycles) > 0,
            "most_depended_on":    self.most_depended_on(),
            "nodes": {
                name: {
                    "layer":        node.layer,
                    "package":      node.package,
                    "dependencies": node.dependencies,
                    "dependents":   node.dependents,
                }
                for name, node in self.nodes.items()
            },
        }
