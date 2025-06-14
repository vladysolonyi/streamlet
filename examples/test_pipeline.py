import logging
from framework.core import Pipeline

# Configure logging - Add this at the start of your script
logging.basicConfig(
    level=logging.DEBUG,  # Set to DEBUG to see all messages
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),  # Output to terminal
    ]
)

# Now create and run your pipeline
pipeline = Pipeline("configs/keylogger_llm_analyze.json")
pipeline.build()

try:
    pipeline.run()  # Start the pipeline
    input("Press Enter to stop...")  # Keep running until user stops
except KeyboardInterrupt:
    pass
finally:
    pipeline.shutdown()  # Ensure clean shutdown