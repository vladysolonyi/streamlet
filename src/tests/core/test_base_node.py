from framework.nodes import BaseNode
import pytest

class ConcreteNode(BaseNode):
    node_type = "concrete"
    
    def process(self, data):
        return data * 2
    
    def get_spatial_data(self):
        return {"value": 42}

def test_base_node_implementation():
    node = ConcreteNode({})
    assert node.process(2) == 4
    assert node.get_spatial_data()["value"] == 42

