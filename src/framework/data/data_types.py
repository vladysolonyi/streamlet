from enum import Enum

class DataType(Enum):
    EVENT = "event"          # Real-time triggers
    STATIC = "static"        # Immutable datasets
    STREAM = "stream"        # Continuous feeds
    DERIVED = "derived"      # Processed outputs
    TRANSACTIONAL = "transactional"  # User interactions

class DataFormat(Enum):
    NUMERICAL = "numerical"  # Scalars, vectors, tensors
    TEXTUAL = "textual"      # JSON/XML/plain text
    MEDIA = "media"          # Images/audio/video
    GEOSPATIAL = "geospatial" # GPS/GeoJSON
    BINARY = "binary"        # Serialized blobs

class DataCategory(Enum):
    GEOSPATIAL = "geospatial"
    MEDIA = "media"
    USER_ACTIVITY = "user_activity"
    ENVIRONMENTAL = "environmental"
    SOCIAL = "social"
    NETWORK = "network"
    GENERIC = "generic"

class LifecycleState(Enum):
    RAW = "raw"
    PROCESSED = "processed"
    ENRICHED = "enriched"
    ARCHIVED = "archived"

class SensitivityLevel(Enum):
    PUBLIC = "public"
    CONFIDENTIAL = "confidential"
    RESTRICTED = "restricted"

class DataSource(Enum):
    INTERNAL = "internal"
    EXTERNAL = "external"
    USER_GENERATED = "user_generated"