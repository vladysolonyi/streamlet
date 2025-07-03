from typing import List, Dict, Any
import logging
from pydantic import BaseModel
from framework.nodes.base_node import BaseNode
from framework.data.data_packet import DataPacket
from framework.data.data_types import DataType, DataFormat, DataCategory, LifecycleState
from transformers import pipeline

class KeywordExtractor(BaseNode):
    node_type = "keyword_extractor"
    accepted_data_types = {DataType.STREAM, DataType.EVENT}
    accepted_formats = {DataFormat.TEXTUAL}
    accepted_categories = {DataCategory.GENERIC}
    IS_GENERATOR = False
    IS_ASYNC_CAPABLE = False
    MIN_INPUTS = 1
    MAX_INPUTS = 1

    class Params(BaseModel):
        model_name: str = "dbmdz/bert-large-cased-finetuned-conll03-english"
        grouped_entities: bool = True

    def __init__(self, config):
        super().__init__(config)
        self.params = self.Params(**config.get('params', {}))
        self.logger = logging.getLogger(self.node_type)
        try:
            self.ner = pipeline(
                task="ner",
                model=self.params.model_name,
                grouped_entities=self.params.grouped_entities
            )
        except Exception as e:
            self.logger.error(f"Failed to load NER model {self.params.model_name}: {e}")
            raise

    def on_data(self, packet: DataPacket, input_channel: str):
        if not self.validate_input(packet):
            return

        text = packet.content
        if not isinstance(text, str):
            self.logger.warning("KeywordExtractor received non-text content: %s", type(text))
            return

        try:
            entities = self.ner(text)
        except Exception as e:
            self.logger.error(f"NER error: {e}")
            return

        # Extract unique entity words/text
        keywords: List[str] = []
        for ent in entities:
            # ent has 'word' or 'entity_group'
            word = ent.get('word') or ent.get('entity_group') or str(ent)
            if word not in keywords:
                keywords.append(word)

        output_content: Dict[str, Any] = {
            "input": text,
            "keywords": keywords
        }

        out_pkt = self.create_packet(
            content=output_content,
            data_type=DataType.DERIVED,
            format=DataFormat.JSON,
            category=DataCategory.GENERIC,
            lifecycle_state=LifecycleState.PROCESSED
        )
        self.data_bus.publish(self.outputs[0], out_pkt)

NODE_CLASSES = [KeywordExtractor]
