from framework.core import Pipeline


pipeline = Pipeline("configs/math_pipeline.json")
pipeline.build()

# Test single iteration
pipeline.run()  # Would need to implement limited run