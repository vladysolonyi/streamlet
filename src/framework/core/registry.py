# framework/core/registry.py
from typing import Type, Dict, Any

class NodeRegistry:
    """Central registry for RF/EM processing nodes"""
    _nodes: Dict[str, Type] = {}
    _categories: Dict[str, str] = {}  # Track node categories

    @classmethod
    def register(cls, node_type: str, node_class: Type):
        """Register a new node type with category"""
        if node_type in cls._nodes:
            raise ValueError(f"Node type {node_type} already registered")
        
        # Extract category from class module path
        module_parts = node_class.__module__.split('.')
        category = module_parts[-2] if len(module_parts) >= 2 else 'other'
        cls._categories[node_type] = category
        
        cls._nodes[node_type] = node_class

    @classmethod
    def create(cls, node_type: str, config: Dict[str, Any]) -> Any:
        """Instantiate a node with its configuration"""
        if node_type not in cls._nodes:
            raise ValueError(f"Unknown node type: {node_type}")
        return cls._nodes[node_type](config)

    @classmethod
    def list_available(cls) -> list:
        """Get list of registered node types"""
        return list(cls._nodes.keys())

    @classmethod
    def get_category(cls, node_type: str) -> str:
        """Get category for a node type"""
        return cls._categories.get(node_type, 'uncategorized')
    
    @classmethod
    def get_params_schema(cls, node_type: str) -> dict:
        """Get parameter schema for node type"""
        return cls._nodes[node_type].get_param_schema()