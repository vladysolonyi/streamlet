import logging
from typing import List, Dict, Any
from pydantic import BaseModel
from framework.nodes.base_node import BaseNode
from framework.data.data_packet import DataPacket
from framework.data.data_types import DataType, DataFormat, DataCategory, LifecycleState
from transformers import pipeline

class IntentDetector(BaseNode):
    node_type = "intent_detector"
    accepted_data_types = {DataType.STREAM, DataType.EVENT}
    accepted_formats = {DataFormat.TEXTUAL}
    accepted_categories = {DataCategory.GENERIC}
    IS_GENERATOR = False
    IS_ASYNC_CAPABLE = False
    MIN_INPUTS = 1
    MAX_INPUTS = 1

    class Params(BaseModel):
        model_name: str = "facebook/bart-large-mnli"
        candidate_labels: List[str]              # list of intent labels
        multi_class: bool = False                # allow multiple intents
        hypothesis_template: str = "This text is about {}."

    def __init__(self, config):
        super().__init__(config)
        self.params = self.Params(**config.get('params', {}))
        self.logger = logging.getLogger(self.node_type)
        try:
            self.classifier = pipeline(
                task="zero-shot-classification",
                model=self.params.model_name
            )
        except Exception as e:
            self.logger.error(f"Failed to load zero-shot model {self.params.model_name}: {e}")
            raise

    def on_data(self, packet: DataPacket, input_channel: str):
        if not self.validate_input(packet):
            return

        text = packet.content
        try:
            result = self.classifier(
                sequences=text,
                candidate_labels=self.params.candidate_labels,
                hypothesis_template=self.params.hypothesis_template,
                multi_label=self.params.multi_class
            )
        except Exception as e:
            self.logger.error(f"Intent detection error: {e}")
            return

        output_content: Dict[str, Any] = {
            "input": text,
            "intent_scores": result
        }

        out_pkt = self.create_packet(
            content=output_content,
            data_type=DataType.DERIVED,
            format=DataFormat.JSON,
            category=DataCategory.GENERIC,
            lifecycle_state=LifecycleState.PROCESSED
        )
        self.data_bus.publish(self.outputs[0], out_pkt)

# Register node classes for the pipeline
NODE_CLASSES = [IntentDetector]
