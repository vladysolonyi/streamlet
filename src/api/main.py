# api/main.py
from fastapi import FastAPI, HTTPException, Security, WebSocket, WebSocketDisconnect
import asyncio
from contextlib import asynccontextmanager
from framework.core.telemetry import telemetry
from fastapi.security import APIKeyHeader
import time
from framework.core import Pipeline, NodeRegistry, PipelineManager
manager = PipelineManager()

from framework.data.data_types import (
    DataType,
    DataFormat, 
    DataCategory,
    LifecycleState,
    SensitivityLevel,
    DataSource
)
from uuid import UUID, uuid4
from pydantic import BaseModel
from fastapi.middleware.cors import CORSMiddleware
from typing import Union, AsyncGenerator
import yaml

@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    # Start telemetry broadcaster on startup
    broadcaster_task = asyncio.create_task(telemetry._async_broadcaster())
    
    yield
    
    # Cleanup on shutdown
    telemetry.stop()
    broadcaster_task.cancel()
    try:
        await broadcaster_task
    except asyncio.CancelledError:
        pass
    print("🛑 Telemetry broadcaster stopped")

app = FastAPI(lifespan=lifespan)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],  # Your frontend origin
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


api_keys = ["SECRET_KEY"]  # In production, use proper auth
security = APIKeyHeader(name="X-API-Key")

# In-memory pipeline store (replace with DB in production)
pipelines = {}

class PipelineConfig(BaseModel):
    config: Union[str, dict]  # Accept both path and direct config
    name: str = "Unnamed Pipeline"

class NodeUpdate(BaseModel):
    node_id: str
    params: dict

# --- Core Endpoints ---
@app.get("/health")
async def health_check():
    return {"status": "ok"}

@app.post("/pipelines")
def create_pipeline(config: PipelineConfig):
    pipeline_id = manager.create_pipeline(config.config)
    return {"pipeline_id": pipeline_id}

@app.post("/pipelines/{pipeline_id}/start")
def start_pipeline(pipeline_id: str):
    pipeline = manager.get_pipeline(pipeline_id)
    if not pipeline:
        raise HTTPException(status_code=404, detail="Pipeline not found")
    pipeline.run()
    return {"status": "started"}

@app.post("/pipelines/{pipeline_id}/stop")
def stop_pipeline(pipeline_id: str):
    pipeline = manager.get_pipeline(pipeline_id)
    if not pipeline:
        raise HTTPException(status_code=404, detail="Pipeline not found")
    
    try:
        pipeline.shutdown()
        return {"status": "stopped"}
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to stop pipeline: {str(e)}"
        )

@app.delete("/pipelines/{pipeline_id}")
def delete_pipeline(pipeline_id: str):
    if not manager.delete_pipeline(pipeline_id):
        raise HTTPException(status_code=404, detail="Pipeline not found")
    return {"status": "deleted"}

@app.put("/pipelines/{pipeline_id}/config")
def update_pipeline_config(pipeline_id: str, config: PipelineConfig):
    if not manager.update_pipeline_config(pipeline_id, config.config):
        raise HTTPException(status_code=404, detail="Pipeline not found or update failed")
    return {"status": "updated"}

@app.patch("/pipelines/{pipeline_id}/nodes/{node_id}")
def update_node_params(pipeline_id: str, node_id: str, update: NodeUpdate):
    pipeline = manager.get_pipeline(pipeline_id)
    if not pipeline:
        raise HTTPException(status_code=404, detail="Pipeline not found")
    if not pipeline.update_node_params(node_id, update.params):
        raise HTTPException(status_code=400, detail="Invalid parameters")
    return {"status": "updated"}

# --- Configuration Endpoints ---
@app.patch("/pipelines/{pipeline_id}/nodes")
async def update_node(
    pipeline_id: UUID,
    update: NodeUpdate,
    api_key: str = Security(security)
):
    """Update node parameters in real-time"""
    pipeline = _get_pipeline(pipeline_id)
    try:
        node = next(n for n in pipeline["instance"].nodes 
                   if n.node_id == update.node_id)
        node.update_params(update.params)
        return {"status": "updated"}
    except StopIteration:
        raise HTTPException(404, "Node not found")

@app.get("/pipelines/{pipeline_id}/nodes")
async def get_nodes(
    pipeline_id: UUID,
    api_key: str = Security(security)
):
    """Get current node configuration"""
    pipeline = _get_pipeline(pipeline_id)
    return [{
        "id": n.node_id,
        "type": n.node_type,
        "params": n.config,
        "inputs": n.inputs,
        "outputs": n.outputs
    } for n in pipeline["instance"].nodes]

# --- Helper Functions ---
def _get_pipeline(pipeline_id: UUID):
    pipeline = pipelines.get(pipeline_id)
    if not pipeline:
        raise HTTPException(404, "Pipeline not found")
    return pipeline

# api/main.py
@app.get("/node-types/{node_type}/params")
async def get_node_params_schema(
    node_type: str):
    """Get parameter schema for specific node type"""
    try:
        return NodeRegistry.get_params_schema(node_type)
    except KeyError:
        raise HTTPException(404, "Node type not found")

@app.get("/node-types")
async def get_available_nodes():
    """List available node types with metadata"""
    return {
        nt: {
            "params_schema": NodeRegistry.get_params_schema(nt),
            "category": NodeRegistry.get_category(nt)
        }
        for nt in NodeRegistry.list_available()
    }

@app.get("/data-spec")
async def get_data_specification():
    """Return full data type specification for UI/validation"""
    return {
        "data_types": {dt.name: dt.value for dt in DataType},
        "formats": {fmt.name: fmt.value for fmt in DataFormat},
        "categories": {cat.name: cat.value for cat in DataCategory},
        "lifecycle_states": {ls.name: ls.value for ls in LifecycleState},
        "sensitivity_levels": {sl.name: sl.value for sl in SensitivityLevel},
        "sources": {src.name: src.value for src in DataSource},
        
        # For surveillance critique - add semantic meanings
        "type_descriptions": {
            DataType.STREAM.value: "Real-time surveillance feeds",
            DataCategory.GEOSPATIAL.value: "Location tracking data",
            SensitivityLevel.RESTRICTED.value: "Classified surveillance material"
        }
    }

@app.websocket("/ws/telemetry")
async def websocket_telemetry(websocket: WebSocket):
    try:
        # Accept connection only once here
        await websocket.accept()
        
        # Send initial confirmation
        await websocket.send_json({
            "type": "connection_ack",
            "status": "connected",
            "server_time": time.time()
        })
        
        # Add to telemetry system
        await telemetry.add_connection(websocket)
        
        # Keep connection alive
        while True:
            await websocket.receive_text()
            
    except WebSocketDisconnect:
        pass  # Normal client disconnect
    except Exception as e:
        print(f"WebSocket error: {str(e)}")
    finally:
        await telemetry.remove_connection(websocket)
        try:
            await websocket.close()
        except RuntimeError:
            pass


