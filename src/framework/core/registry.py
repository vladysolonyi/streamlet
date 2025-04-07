from typing import Type, Dict, Any

class NodeRegistry:
    """Central registry for signal processing nodes"""
    _nodes: Dict[str, Type] = {}

    @classmethod
    def register(cls, node_type: str, node_class: Type):
        """Register a node type"""
        if node_type in cls._nodes:
            raise ValueError(f"Node type {node_type} already registered")
        cls._nodes[node_type] = node_class

    @classmethod
    def create(cls, node_type: str, config: Dict[str, Any]) -> Any:
        """Create a node instance"""
        if node_type not in cls._nodes:
            raise ValueError(f"Unknown node type: {node_type}")
        return cls._nodes[node_type](config)

    @classmethod
    def list_available(cls) -> list:
        """List registered node types"""
        return list(cls._nodes.keys())