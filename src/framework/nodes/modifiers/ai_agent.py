import os
import json
import logging
from typing import Dict, Optional
from pydantic import BaseModel, Field
from groq import Groq
from framework.nodes.base_node import BaseNode
from framework.data.data_packet import DataPacket
from framework.data.data_types import *
from framework.core.decorators import node_telemetry

class AIAgentNode(BaseNode):
    node_type = "ai_agent"
    accepted_data_types = {DataType.DERIVED, DataType.STREAM, DataType.STATIC}
    accepted_formats = {DataFormat.TEXTUAL}
    accepted_categories = {DataCategory.USER_ACTIVITY, DataCategory.SOCIAL}
    
    class Params(BaseModel):
        api_key: str = Field(..., description="Groq API key from environment")
        model: str = Field(default="deepseek-r1-distill-llama-70b", 
                         description="Groq model name")
        max_tokens: int = Field(default=1024, ge=256, le=4096)
        temperature: float = Field(default=0.6, ge=0.0, le=1.0)
        analysis_task: str = Field(default="Analyze and extract insights from this data",
                                  description="Specific analysis objective")
        output_format: str = Field(default="json", 
                                  description="Requested output format from LLM")
        timeout: float = Field(default=10.0, description="API timeout in seconds")


    BASE_PROMPT = """Analyze this typing data for patterns:
    
    Identify which activity the user is performing.
    Return only JSON in this format without any additional text:
    {
        "activity": 
        "description": 
    }"""
    

    def __init__(self, config):
        super().__init__(config)
        self.params = self.Params(**config.get('params', {}))
        self.client = Groq(api_key=self.params.api_key)
        self.logger = logging.getLogger('llm_analyst')

    @node_telemetry("on_data")
    def on_data(self, packet: DataPacket, _input_channel: str = None):
        """Process incoming data packet with LLM analysis"""

        try:
            analysis = self._analyze_with_llm(packet)
            result_packet = self.create_packet(
                content=analysis,
                metadata={
                    "model": self.params.model,
                    "task": self.params.analysis_task,
                    "source_packet": packet.dict()
                }
            )
            self.data_bus.publish(self.outputs[0], result_packet)
        except Exception as e:
            self.logger.error(f"Analysis failed: {str(e)}", exc_info=True)

    def _analyze_with_llm(self, packet: DataPacket) -> Dict:
        """Execute LLM analysis through Groq API"""
        prompt = self._build_prompt(packet)
        
        try:
            response = self.client.chat.completions.create(
                messages=[{"role": "user", "content": prompt}],
                model=self.params.model,
                temperature=self.params.temperature,
                max_tokens=self.params.max_tokens,
                response_format={"type": "json_object"} if self.params.output_format == "json" else None,
                timeout=self.params.timeout  # Add timeout
            )
            return self._parse_response(response.choices[0].message.content)
        except Exception as e:
            self.logger.error(f"Groq API error: {str(e)}")
            return {"error": str(e)}  # Return error instead of raising

    def _build_prompt(self, packet: DataPacket) -> str:
        """Construct analysis prompt from template"""
        # return self.BASE_PROMPT.format(
            # task=self.params.analysis_task,
            # category=packet.category.value,
            # source=packet.source.value,
            # format=packet.format.value,
            # output_format=self.params.output_format.upper()
        #) + f"\n\nInput data:\n{packet.content}"
        return self.BASE_PROMPT+ f"\n\nInput data:\n{packet.content}"

    def _parse_response(self, raw_response: str) -> Dict:
        """Validate and parse LLM response"""
        try:
            if self.params.output_format == "json":
                return json.loads(raw_response)
            return {"raw_response": raw_response}
        except json.JSONDecodeError:
            self.logger.warning("Invalid JSON response, attempting repair")
            return self._repair_json(raw_response)

    def _repair_json(self, broken_json: str) -> Dict:
        """Attempt to fix common JSON formatting issues"""
        # Simple repair logic - extend as needed
        cleaned = broken_json.strip().replace("'", '"')
        if not cleaned.startswith("{"):
            cleaned = "{" + cleaned
        if not cleaned.endswith("}"):
            cleaned += "}"
        return json.loads(cleaned)

NODE_CLASSES = [AIAgentNode]