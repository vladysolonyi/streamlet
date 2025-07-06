import logging
from framework.core import Pipeline
from framework.core.pipeline_manager import PipelineManager
import time

# Configure logging
logging.basicConfig(
    level=logging.ERROR,  # Set to DEBUG for detailed output
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),  # Output to terminal
    ]
)

# Create manager instance
manager = PipelineManager()

# Create initial pipeline
config = "configs/global_flight_states.json"  # Or use a dict config
pipeline_id = manager.create_pipeline(config)
print(f"Created pipeline with ID: {pipeline_id}")

# Get the pipeline instance from manager
pipeline = manager.get_pipeline(pipeline_id)

# Start the pipeline
pipeline.run()
print("Pipeline started")

# New config to test
config_new = {
  "settings": {
    "fps_limit": 60
  },
    "nodes": [
        {
            "type": "number_generator",
            "name": "numbers",
            "params": {
                "start": 2,
                "step": 3
            }
        },
        {
            "type": "console_logger",
            "name": "Logger",
            "inputs": ["numbers"],
            "params": {
                "prefix": "[LOL]"
            }
        }
    ]
}

# Update pipeline configuration
# print("\n=== Updating pipeline configuration ===")
# success = manager.update_pipeline_config(pipeline_id, config_new)
# print(f"Update successful: {success}")

# # Let it run for a bit
# print("Pipeline running with new config...")
time.sleep(28)

# Stop and clean up
print("\nStopping pipeline...")
pipeline.shutdown()
manager.delete_pipeline(pipeline_id)
print("Cleanup complete")