import concurrent.futures
import asyncio
import networkx as nx
from typing import List

#Not implemented yet
class Scheduler:
    """Orchestrates node execution strategies"""
    
    def __init__(self, max_workers: int = 4):
        self.max_workers = max_workers

    def execute_sequential(self, nodes: List):
        """Run nodes in linear order"""
        for node in nodes:
            node.process()

    def execute_parallel(self, nodes: List):
        """Thread-based parallel execution"""
        with concurrent.futures.ThreadPoolExecutor(max_workers=self.max_workers) as executor:
            futures = [executor.submit(node.process) for node in nodes]
            concurrent.futures.wait(futures)

    async def execute_async(self, nodes: List):
        """AsyncIO-based execution"""
        tasks = [asyncio.create_task(node.async_process()) for node in nodes]
        await asyncio.gather(*tasks)
