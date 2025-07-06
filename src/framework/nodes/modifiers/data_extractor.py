import logging
import json
import re
import ast
from typing import Any, Dict, List
from pydantic import BaseModel, Field
from groq import Groq
from framework.nodes.base_node import BaseNode
from framework.data.data_packet import DataPacket
from framework.data.data_types import DataType, DataFormat, DataCategory
from framework.core.decorators import node_telemetry

class DataExtractorNode(BaseNode):
    node_type = "data_extractor"
    accepted_data_types = {DataType.DERIVED, DataType.STREAM, DataType.EVENT}
    accepted_formats = {DataFormat.TEXTUAL, DataFormat.NUMERICAL}
    accepted_categories = set(DataCategory)
    IS_GENERATOR = False
    MIN_INPUTS = 1
    MAX_INPUTS = None

    class Params(BaseModel):
        api_key: str = Field(..., description="Groq API key")
        model: str = Field(default="deepseek-r1-distill-llama-70b")
        max_tokens: int = Field(default=1024, ge=128, le=100000)
        temperature: float = Field(default=0.3, ge=0.0, le=1.0)
        parse_task: str = Field(default="Analyze and extract fields from inputs.")
        timeout: float = Field(default=10.0)
        minimize_json: bool = Field(default=True)

    BASE_PROMPT = (
        "You are a code generator. Generate a single Python function `parse(inputs)` "
        "that accepts a dict `inputs` mapping channel names to data, "
        "parses JSON/text as needed, and returns a JSON-serializable dict according to the task. "
        "Use json.loads and ast.literal_eval for robust parsing. "
        "Output only the code block with ```python...``` and nothing else."
    )

    CODE_BLOCK_RE = re.compile(r"```python\n([\s\S]*?)```", re.IGNORECASE)
    CLEAN_RE = re.compile(r"<think>[\s\S]*?</think>", re.IGNORECASE)

    def __init__(self, config):
        super().__init__(config)
        self.params = self.Params(**config.get('params', {}))
        self.client = Groq(api_key=self.params.api_key)
        self.logger = logging.getLogger(self.node_type)
        self._parse_fn = None
        self._latest_inputs: Dict[str, Any] = {}

    @node_telemetry("on_data")
    def on_data(self, packet: DataPacket, input_channel: str):
        # Store latest data per channel
        self._latest_inputs[input_channel] = packet.content
        if len(self._latest_inputs) < self.MIN_INPUTS:
            return

        # Generate parser once
        if not self._parse_fn:
            # Prepare minimized sample
            sample_struct = {
                ch: self._prepare_sample(val)
                for ch, val in self._latest_inputs.items()
            }
            prompt = (
                f"{self.BASE_PROMPT}\nTask: {self.params.parse_task}\n"
                f"Sample input structure:\n{json.dumps(sample_struct, indent=2)}"
            )
            self.logger.debug(f"Prompt to LLM:\n{prompt}")
            try:
                resp = self.client.chat.completions.create(
                    messages=[{"role": "user", "content": prompt}],
                    model=self.params.model,
                    temperature=self.params.temperature,
                    max_tokens=self.params.max_tokens,
                    timeout=self.params.timeout
                )
                raw = resp.choices[0].message.content
                self.logger.debug(f"Raw LLM output:\n{raw}")
            except Exception as e:
                self.logger.error(f"LLM generation error: {e}")
                return

            # Clean and extract code
            code_text = self.CLEAN_RE.sub("", raw)
            m = self.CODE_BLOCK_RE.search(code_text)
            parser_code = m.group(1).strip() if m else code_text.strip()
            # Ensure imports at top
            lines = []
            if 'json.loads' in parser_code:
                lines.append('import json')
            if 'ast.literal_eval' in parser_code:
                lines.append('import ast')
            parser_code = "\n".join(lines + [parser_code])
            self.logger.debug(f"Parser code with imports:\n{parser_code}")

            # Compile and store
            try:
                local_ns: Dict[str, Any] = {}
                compiled = compile(parser_code, '<data_extractor>', 'exec')
                exec(compiled, {}, local_ns)
                self._parse_fn = local_ns.get('parse')
                if not callable(self._parse_fn):
                    raise ValueError("Generated code did not define parse()")
                self.logger.info("Parser compiled successfully")
            except Exception as e:
                self.logger.error(f"Parser compile error: {e}\nCode:\n{parser_code}")
                return

        # Execute parser
        try:
            result = self._parse_fn(self._latest_inputs)
            self.logger.debug(f"Parser result: {result}")
        except Exception as e:
            self.logger.error(f"Parser execution error: {e}")
            return

        # Emit result
        out_pkt = self.create_packet(
            content=result,
            data_type=DataType.DERIVED,
            format=DataFormat.TEXTUAL,
            category=DataCategory.GENERIC
        )
        self.data_bus.publish(self.outputs[0], out_pkt)

    def _prepare_sample(self, data: Any) -> Any:
        if self.params.minimize_json and isinstance(data, dict):
            return {k: type(v).__name__ for k, v in data.items()}
        if self.params.minimize_json and isinstance(data, list) and data and isinstance(data[0], dict):
            return {k: type(v).__name__ for k, v in data[0].items()}
        text = repr(data)
        return text[:200] + ('...' if len(text) > 200 else '')

NODE_CLASSES = [DataExtractorNode]
