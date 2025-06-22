# framework/core/pipeline_manager.py
import uuid
import logging
from typing import Dict, Optional, Union
from pathlib import Path
from .pipeline import Pipeline
from threading import Lock
import json

class PipelineManager:
    _instance = None
    _lock = Lock()
    
    def __new__(cls):
        with cls._lock:
            if cls._instance is None:
                cls._instance = super().__new__(cls)
                cls._instance.pipelines = {}
                cls._instance.logger = logging.getLogger('pipeline_manager')
            return cls._instance
    
    def create_pipeline(self, config: dict) -> str:
        """Create a new pipeline and return its ID"""
        pipeline_id = str(uuid.uuid4())
        pipeline = Pipeline(config, pipeline_id)
        
        # Add this: Build the pipeline before storing
        pipeline.build()
        
        self.pipelines[pipeline_id] = pipeline
        self.logger.info(f"Created pipeline {pipeline_id}")
        return pipeline_id
    
    def get_pipeline(self, pipeline_id: str) -> Optional[Pipeline]:
        """Get pipeline by ID"""
        return self.pipelines.get(pipeline_id)
    
    def update_pipeline_config(self, pipeline_id: str, new_config: Union[str, dict]) -> bool:
        """Update pipeline configuration"""
        pipeline = self.get_pipeline(pipeline_id)
        if not pipeline:
            return False
        
        try:
            # Handle string config (file path)
            if isinstance(new_config, str):
                if not Path(new_config).exists():
                    self.logger.error(f"Config file not found: {new_config}")
                    return False
                # Load the config file
                with open(new_config) as f:
                    config_data = json.load(f)
            # Handle direct config
            else:
                config_data = new_config
            
            # Continue with update process
            was_running = pipeline._running.is_set()
            if was_running:
                pipeline.shutdown()
            
            pipeline.update_config(config_data)
            
            if was_running:
                pipeline.run()
            
            return True
        except Exception as e:
            self.logger.error(f"Update failed: {str(e)}", exc_info=True)
            return False

    
    def delete_pipeline(self, pipeline_id: str) -> bool:
        """Delete a pipeline"""
        pipeline = self.get_pipeline(pipeline_id)
        if not pipeline:
            return False
        
        pipeline.shutdown()
        del self.pipelines[pipeline_id]
        return True

# Singleton instance
pipeline_manager = PipelineManager()

