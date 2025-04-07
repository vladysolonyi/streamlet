# framework/nodes/__init__.py
import importlib
import pkgutil
import logging
from framework.core.registry import NodeRegistry
from framework.nodes.base_node import BaseNode

logger = logging.getLogger(__name__)

def _autoload_nodes():
    """Smart node discovery with duplicate protection"""
    loaded_types = set()
    
    for _, module_name, _ in pkgutil.walk_packages(
        __path__,
        prefix=__name__ + "."
    ):
        if "__" in module_name or "base_node" in module_name:
            continue
            
        try:
            module = importlib.import_module(module_name)
            if not hasattr(module, 'NODE_CLASSES'):
                continue
                
            for cls in module.NODE_CLASSES:
                if (issubclass(cls, BaseNode) and 
                    cls != BaseNode and
                    cls.node_type not in loaded_types):
                    
                    NodeRegistry.register(cls.node_type, cls)
                    loaded_types.add(cls.node_type)
                    logger.debug(f"Registered node: {cls.node_type}")
                else:
                    logger.warning(f"Skipping duplicate: {cls.node_type}")
                    
        except Exception as e:
            logger.error(f"Failed to load {module_name}: {str(e)}")

_autoload_nodes()