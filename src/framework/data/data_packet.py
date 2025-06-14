# framework/data/data_packet.py
from pydantic import BaseModel, ConfigDict, Field
from datetime import datetime
from typing import Optional, Any, List
from .data_types import *
import msgpack

class DataPacket(BaseModel):
    model_config = ConfigDict(arbitrary_types_allowed=True)
    data_type: DataType
    format: DataFormat
    category: DataCategory
    lifecycle_state: LifecycleState = LifecycleState.RAW
    sensitivity: SensitivityLevel = SensitivityLevel.PUBLIC
    source: DataSource
    content: Any
    timestamp: datetime = datetime.now()
    sequence_id: Optional[int] = None
    processing_chain: List[str] = Field(
        default_factory=list,
        description="Chain of node IDs that processed this data"
    )

    def model_dump_msgpack(self) -> bytes:
        return msgpack.packb(
            self.model_dump(mode="json"),  # Handles enums/datetime
            default=self._msgpack_default,
        )

    @classmethod
    def model_validate_msgpack(cls, data: bytes) -> "DataPacket":
        return cls.model_validate(
            msgpack.unpackb(data, ext_hook=cls._msgpack_ext_hook)
        )

    @staticmethod
    def _msgpack_default(obj: Any) -> Any:
        """Handles non-serializable types"""
        if isinstance(obj, datetime):
            return {"__datetime__": obj.isoformat()}
        if isinstance(obj, Enum):
            return {"__enum__": str(obj)}
        raise TypeError(f"Unserializable type {type(obj)}")

    @classmethod
    def _msgpack_ext_hook(cls, code: int, data: bytes) -> Any:
        """Reconstruct custom types"""
        if code == 0:
            return datetime.fromisoformat(data.decode())
        if code == 1:
            enum_type, value = data.decode().split(":")
            return globals()[enum_type](value)
        return msgpack.ExtType(code, data)