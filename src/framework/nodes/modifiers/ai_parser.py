import logging
import json
import re
import ast
from typing import Any, Dict
from pydantic import BaseModel, Field
from groq import Groq
from framework.nodes.base_node import BaseNode
from framework.data.data_packet import DataPacket
from framework.data.data_types import DataType, DataFormat, DataCategory
from framework.core.decorators import node_telemetry

class AIParserNode(BaseNode):
    node_type = "ai_parser"
    tags = ["ai", "experimental"]
    accepted_data_types = {DataType.DERIVED, DataType.STREAM, DataType.EVENT}
    accepted_formats = {DataFormat.TEXTUAL, DataFormat.NUMERICAL}
    accepted_categories = set(DataCategory)
    IS_GENERATOR = False
    MIN_INPUTS = 1
    MAX_INPUTS = 1  # exactly one input

    class Params(BaseModel):
        api_key: str = Field(..., description="Groq API key")
        model: str = Field(default="deepseek-r1-distill-llama-70b")
        max_tokens: int = Field(default=1024, ge=128, le=100000)
        temperature: float = Field(default=0.3, ge=0.0, le=1.0)
        parse_task: str = Field(default="Extract the needed value from the input.")
        timeout: float = Field(default=10.0)
        minimize_json: bool = Field(default=True)

    BASE_PROMPT = (
        "You are a code generator.\n"
        "Generate only a Python function `parse(data)` that:\n"
        "1) Accepts a JSON string or Python data structure in `data`.\n"
        "2) Parses/validates it robustly (use json.loads and ast.literal_eval).\n"
        "3) Returns a single primitive value (number or string) as the final result.\n"
        "If parsing or extraction fails, return something like `None` or a default.\n"
        "Output only the code inside a ```python ... ``` block with no explanation."
    )

    CODE_RE = re.compile(r"```python\n([\s\S]*?)```", re.IGNORECASE)
    THINK_RE = re.compile(r"<think>[\s\S]*?</think>", re.IGNORECASE)

    def __init__(self, config):
        super().__init__(config)
        self.params = self.Params(**config.get('params', {}))
        self.client = Groq(api_key=self.params.api_key)
        self.logger = logging.getLogger(self.node_type)
        self._parse_fn = None

    @node_telemetry("on_data")
    def on_data(self, packet: DataPacket, _input_channel: str):
        data = packet.content

        # Generate & compile parser once
        if self._parse_fn is None:
            # Build prompt with a minimized preview
            preview = self._prepare_sample(data)
            prompt = (
                f"{self.BASE_PROMPT}\n"
                f"Task: {self.params.parse_task}\n"
                f"Sample for context:\n{repr(preview)}"
            )
            self.logger.debug(f"Prompt to LLM:\n{prompt}")

            try:
                resp = self.client.chat.completions.create(
                    messages=[{"role": "user", "content": prompt}],
                    model=self.params.model,
                    temperature=self.params.temperature,
                    max_tokens=self.params.max_tokens,
                    timeout=self.params.timeout,
                )
                raw = resp.choices[0].message.content
                self.logger.debug(f"Raw LLM output:\n{raw}")
            except Exception as e:
                self.logger.error(f"LLM generation error: {e}")
                return

            # Strip thought blocks and extract code
            code = self.THINK_RE.sub("", raw)
            m = self.CODE_RE.search(code)
            func_code = m.group(1).strip() if m else code.strip()

            # Ensure necessary imports
            imports = []
            if "json.loads" in func_code:
                imports.append("import json")
            if "ast.literal_eval" in func_code:
                imports.append("import ast")
            full_code = "\n".join(imports + [func_code])
            self.logger.debug(f"Final parser code:\n{full_code}")

            # Compile in a globals that include json and ast
            try:
                local_ns: Dict[str, Any] = {}
                exec_globals = {"json": json, "ast": ast}
                compiled = compile(full_code, '<ai_parser>', 'exec')
                exec(compiled, exec_globals, local_ns)
                self._parse_fn = local_ns.get('parse')
                if not callable(self._parse_fn):
                    raise ValueError("No parse() function found.")
                self.logger.info("Parser compiled successfully.")
            except Exception as e:
                self.logger.error(f"Parser compile error: {e}\nCode:\n{full_code}")
                return

        # Execute parser on raw input
        try:
            result = self._parse_fn(data)
            self.logger.debug(f"Parser result: {result}")
        except Exception as e:
            self.logger.error(f"Parser execution error: {e}")
            result = None

        # Determine format: numeric vs textual
        if isinstance(result, (int, float)):
            fmt = DataFormat.NUMERICAL
        else:
            fmt = DataFormat.TEXTUAL

        # Emit the primitive result directly
        out_pkt = self.create_packet(
            content=result,
            data_type=DataType.DERIVED,
            format=fmt,
            category=DataCategory.GENERIC
        )
        self.data_bus.publish(self.outputs[0], out_pkt)

    def _prepare_sample(self, data: Any) -> Any:
        # Minimize JSON structure or truncate repr
        if self.params.minimize_json and isinstance(data, dict):
            return {k: type(v).__name__ for k, v in data.items()}
        if self.params.minimize_json and isinstance(data, list) and data and isinstance(data[0], dict):
            return {k: type(v).__name__ for k, v in data[0].items()}
        text = repr(data)
        return text[:200] + ("..." if len(text) > 200 else "")

NODE_CLASSES = [AIParserNode]
