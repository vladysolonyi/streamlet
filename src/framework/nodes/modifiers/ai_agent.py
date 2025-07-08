import os
import json
import logging
import re
from typing import Dict, Optional, Any
from pydantic import BaseModel, Field
from groq import Groq
from framework.nodes.base_node import BaseNode
from framework.data.data_packet import DataPacket
from framework.data.data_types import *
from framework.core.decorators import node_telemetry

class AIAgentNode(BaseNode):
    node_type = "ai_agent"
    tags = ["ai"]
    accepted_data_types = {DataType.DERIVED, DataType.STREAM, DataType.STATIC, DataType.EVENT}
    accepted_formats = {DataFormat.TEXTUAL}
    accepted_categories = set(DataCategory)
    IS_GENERATOR = False
    MIN_INPUTS = 1
    MAX_INPUTS = 1

    # regex to strip out <think>…</think> and any ```…``` code fences
    THINK_RE = re.compile(r"<think>[\s\S]*?</think>", re.IGNORECASE)
    FENCE_RE = re.compile(r"```[\s\S]*?```", re.IGNORECASE)

    class Params(BaseModel):
        api_key: str = Field(..., description="Groq API key")
        model: str = Field(default="deepseek-r1-distill-llama-70b", description="Groq model name")
        max_tokens: int = Field(default=1024, ge=256, le=100000)
        temperature: float = Field(default=0.6, ge=0.0, le=1.0)
        analysis_task: str = Field(
            default="Analyze and extract insights from this data",
            description="Specific analysis objective"
        )
        output_format: str = Field(default="json", description="Desired output format")
        timeout: float = Field(default=10.0, description="API timeout in seconds")

    BASE_PROMPT = (
        "You are a data analyst/processor/generator. Your task:\n"
        "{task}\n\n"
        "If input data is provided, analyze it; if not, just respond based on the task.\n"
        "Return valid JSON only.  Do not wrap your output in code fences or markdown.\n"
    )

    def __init__(self, config):
        super().__init__(config)
        self.params = self.Params(**config.get('params', {}))
        self.client = Groq(api_key=self.params.api_key)
        self.logger = logging.getLogger(self.node_type)

    @node_telemetry("on_data")
    def on_data(self, packet: DataPacket, _input_channel: str = None):
        try:
            if packet.data_type == DataType.EVENT:
                data_payload: Optional[Any] = None
            else:
                if not self.validate_input(packet):
                    return
                data_payload = packet.content

            analysis = self._analyze_with_llm(data_payload)
            result_pkt = self.create_packet(
                content=analysis,
                metadata={
                    "model": self.params.model,
                    "task": self.params.analysis_task,
                    "trigger": packet.data_type.value
                }
            )
            self.data_bus.publish(self.outputs[0], result_pkt)
        except Exception as e:
            self.logger.error(f"Analysis failed: {e}", exc_info=True)

    def _analyze_with_llm(self, data_payload: Optional[Any]) -> Any:
        prompt = self.BASE_PROMPT.format(task=self.params.analysis_task)
        if data_payload is not None:
            prompt += f"\n\nInput data:\n{data_payload}"

        try:
            resp = self.client.chat.completions.create(
                messages=[{"role": "user", "content": prompt}],
                model=self.params.model,
                temperature=self.params.temperature,
                max_tokens=self.params.max_tokens,
                response_format={"type": "json_object"} if self.params.output_format == "json" else None,
                timeout=self.params.timeout
            )
            raw = resp.choices[0].message.content
            # strip out any <think>…</think> or ```…``` fences
            raw = self.THINK_RE.sub("", raw)
            raw = self.FENCE_RE.sub("", raw).strip()
        except Exception as e:
            self.logger.error(f"Groq API error: {e}")
            return {"error": str(e)}

        if self.params.output_format == "json":
            try:
                return json.loads(raw)
            except json.JSONDecodeError:
                self.logger.warning("Invalid JSON, returning raw")
                return {"raw": raw}
        else:
            return raw

NODE_CLASSES = [AIAgentNode]
