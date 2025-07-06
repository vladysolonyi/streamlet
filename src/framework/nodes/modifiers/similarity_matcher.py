import logging
from typing import Dict, List, Any
from pydantic import BaseModel
import numpy as np
from framework.nodes.base_node import BaseNode
from framework.data.data_packet import DataPacket
from framework.data.data_types import DataType, DataFormat, DataCategory, LifecycleState


def _cosine_similarity(a: np.ndarray, b: np.ndarray) -> float:
    if np.linalg.norm(a) == 0 or np.linalg.norm(b) == 0:
        return 0.0
    return float(np.dot(a, b) / (np.linalg.norm(a) * np.linalg.norm(b)))


def _euclidean_distance(a: np.ndarray, b: np.ndarray) -> float:
    return float(np.linalg.norm(a - b))


class SimilarityMatcher(BaseNode):
    node_type = "similarity_matcher"
    accepted_data_types = {DataType.STREAM, DataType.EVENT}
    accepted_formats = {DataFormat.NUMERICAL, DataFormat.TEXTUAL, DataFormat.BINARY}
    accepted_categories = {DataCategory.GENERIC}
    IS_GENERATOR = False
    IS_ASYNC_CAPABLE = False
    MIN_INPUTS = 1
    MAX_INPUTS = 1

    class Params(BaseModel):
        references: Dict[str, List[float]]  # mapping id -> vector
        metric: str = "cosine"            # "cosine" or "euclidean"

    def __init__(self, config):
        super().__init__(config)
        self.params = self.Params(**config.get('params', {}))
        self.logger = logging.getLogger(self.node_type)
        # Preprocess reference vectors
        self._refs = {
            key: np.array(vec, dtype=float)
            for key, vec in self.params.references.items()
        }

    def on_data(self, packet: DataPacket, input_channel: str):
        if not self.validate_input(packet):
            return

        content = packet.content
        try:
            vec = np.array(content, dtype=float)
        except Exception as e:
            self.logger.error(f"Invalid embedding content: {e}")
            return

        best_id = None
        best_score = None
        for ref_id, ref_vec in self._refs.items():
            if self.params.metric == "cosine":
                score = _cosine_similarity(vec, ref_vec)
            else:
                # For euclidean, lower is better; invert to similarity
                dist = _euclidean_distance(vec, ref_vec)
                score = float(1 / (1 + dist))

            if best_score is None or score > best_score:
                best_score = score
                best_id = ref_id

        output = {
            "input": content,
            "matched_id": best_id,
            "score": best_score
        }

        out_pkt = self.create_packet(
            content=output,
            data_type=DataType.DERIVED,
            format=DataFormat.JSON,
            category=DataCategory.GENERIC,
            lifecycle_state=LifecycleState.PROCESSED
        )
        self.data_bus.publish(self.outputs[0], out_pkt)


NODE_CLASSES = [SimilarityMatcher]
