from framework.core import Pipeline


pipeline = Pipeline("configs/math_pipeline.yaml")
pipeline.build()

# Test single iteration
pipeline.run()  # Would need to implement limited run