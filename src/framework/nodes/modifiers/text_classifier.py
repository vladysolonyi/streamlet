from typing import Dict, Any
from pydantic import BaseModel
from framework.nodes.base_node import BaseNode
from framework.data.data_packet import DataPacket
from framework.data.data_types import DataType, DataFormat, DataCategory, LifecycleState
from transformers import pipeline
import logging

class TextClassifier(BaseNode):
    node_type = "text_classifier"
    tags = ["Untested"]
    accepted_data_types = {DataType.STREAM, DataType.EVENT}
    accepted_formats = {DataFormat.TEXTUAL}
    accepted_categories = {DataCategory.GENERIC}
    IS_GENERATOR = False
    IS_ASYNC_CAPABLE = False
    MIN_INPUTS = 1
    MAX_INPUTS = 1

    class Params(BaseModel):
        model_name: str = "distilbert-base-uncased-finetuned-sst-2-english"
        top_k: int = 1
        return_all_scores: bool = False

    def __init__(self, config):
        super().__init__(config)
        self.params = self.Params(**config.get('params', {}))
        self.logger = logging.getLogger(self.node_type)
        try:
            self.classifier = pipeline(
                task="sentiment-analysis",
                model=self.params.model_name,
                return_all_scores=self.params.return_all_scores
            )
        except Exception as e:
            self.logger.error(f"Failed to load model {self.params.model_name}: {e}")
            raise

    def on_data(self, packet: DataPacket, input_channel: str):
        # Validate input
        if not self.validate_input(packet):
            return

        text = packet.content
        try:
            # Perform classification
            result = self.classifier(text, top_k=self.params.top_k)
        except Exception as e:
            self.logger.error(f"Classification error: {e}")
            return

        # Prepare classification output
        output_content: Dict[str, Any] = {
            "input": text,
            "result": result
        }

        # Create and publish new packet with classification
        out_pkt = self.create_packet(
            content=output_content,
            data_type=DataType.DERIVED,
            format=DataFormat.JSON,
            category=DataCategory.GENERIC,
            lifecycle_state=LifecycleState.PROCESSED
        )
        self.data_bus.publish(self.outputs[0], out_pkt)

# Register node classes for the pipeline
NODE_CLASSES = [TextClassifier]
