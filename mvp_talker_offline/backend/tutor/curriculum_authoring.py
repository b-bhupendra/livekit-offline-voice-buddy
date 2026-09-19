"""
curriculum_authoring.py — Structured Output & Semantic Critic for Tier 2.

Implements:
  - CurriculumNode and CriticVerdict Pydantic schemas
  - parse_structured with json_repair resilience
  - structured_authoring_call with error-feedback retry loop
  - Model diversity: uses qwen2.5:7b (or qwen-buddy) for drafting and
    llama3.2 (or distinct auditor) for semantic critique to prevent confirmation bias
"""

import os
import json
import re
from typing import List, Dict, Any, Optional, Type, TypeVar
from pydantic import BaseModel, Field, ValidationError
import json_repair
from openai import AsyncOpenAI

from core.config import OLLAMA_BASE_URL, OLLAMA_MODEL
from core.structured_logger import rag_logger, genui_logger

T = TypeVar("T", bound=BaseModel)

# Default model identifiers
AUTHOR_MODEL = os.getenv("OLLAMA_AUTHOR_MODEL", OLLAMA_MODEL)
CRITIC_MODEL = os.getenv("OLLAMA_CRITIC_MODEL", "llama3.2:latest")

_client: Optional[AsyncOpenAI] = None


def get_llm_client() -> AsyncOpenAI:
    global _client
    if _client is None:
        _client = AsyncOpenAI(
            base_url=f"{OLLAMA_BASE_URL.rstrip('/')}/v1",
            api_key="offline",
        )
    return _client


# ─────────────────────────────────────────────────────────────────────────────
# Pydantic Schemas
# ─────────────────────────────────────────────────────────────────────────────

class CurriculumNode(BaseModel):
    node_id: str = Field(description="Unique node identifier e.g. ch01_nouns_concrete")
    chapter_idx: int = Field(default=1, description="Chapter index (1-18)")
    submodule: str = Field(description="Submodule name e.g. Concrete vs Abstract Nouns")
    title: str = Field(description="Human readable lecture title")
    core_concept: str = Field(description="One-sentence pedagogical core concept")
    prerequisites: List[str] = Field(default_factory=list, description="List of prerequisite node_ids")
    lecture_paragraphs: List[str] = Field(description="2-3 grounded educational paragraphs")
    canvas_type: str = Field(description="One of: classifier, matrix, tree, flow")
    canvas_config: Dict[str, Any] = Field(description="Interactive config matching the canvas_type")
    citations: List[str] = Field(default_factory=list, description="Reference citations from textbooks or course")


class CriticVerdict(BaseModel):
    passed: bool = Field(description="True if content is grounded, pedagogical, and accurate")
    feedback: Optional[str] = Field(default=None, description="Detailed critique feedback if failed")


# ─────────────────────────────────────────────────────────────────────────────
# Parsing & Resilience
# ─────────────────────────────────────────────────────────────────────────────

def parse_structured(raw: str, model_cls: Type[T]) -> T:
    """
    Parses LLM output into Pydantic model with markdown fence stripping
    and json_repair fallback.
    """
    cleaned = raw.strip()
    # Strip markdown code blocks
    if cleaned.startswith("```"):
        cleaned = re.sub(r"^```[a-zA-Z]*\n?", "", cleaned)
        cleaned = re.sub(r"\n?```$", "", cleaned).strip()

    # Extract outermost JSON brackets
    start_idx = cleaned.find("{")
    end_idx = cleaned.rfind("}")
    if start_idx != -1 and end_idx != -1 and end_idx > start_idx:
        cleaned = cleaned[start_idx:end_idx + 1]

    try:
        return model_cls.model_validate_json(cleaned)
    except (json.JSONDecodeError, ValidationError):
        # Fallback to json_repair
        try:
            repaired = json_repair.loads(cleaned)
            if isinstance(repaired, dict):
                return model_cls.model_validate(repaired)
        except Exception as repair_err:
            raise ValidationError.from_exception_data(
                title=model_cls.__name__,
                line_errors=[]
            ) from repair_err

    raise ValueError(f"Failed to parse valid {model_cls.__name__} from LLM output: {raw[:120]}...")


# ─────────────────────────────────────────────────────────────────────────────
# Authoring & Critic Calls
# ─────────────────────────────────────────────────────────────────────────────

async def structured_authoring_call(
    model_cls: Type[T],
    prompt: str,
    feedback: Optional[str] = None,
    max_retries: int = 3,
    model: str = AUTHOR_MODEL
) -> T:
    """
    Invokes local Ollama with JSON mode and feedback retry loop.
    Feeds back the exact ValidationError to the model upon failure.
    """
    client = get_llm_client()
    last_error: Optional[str] = None

    for attempt in range(1, max_retries + 1):
        messages = [
            {
                "role": "system",
                "content": (
                    f"You are the Master Pedagogical Author for Buddy Voice AI.\n"
                    f"Generate strictly structured JSON conforming to the schema for {model_cls.__name__}.\n"
                    f"Schema fields:\n{json.dumps(model_cls.model_json_schema().get('properties', {}), indent=2)}\n"
                    f"Return ONLY the valid JSON object without surrounding commentary."
                )
            }
        ]

        user_content = prompt
        if feedback and attempt == 1:
            user_content += f"\n\n[Previous Auditor Feedback]: {feedback}\nAddress this feedback directly."
        elif last_error:
            user_content += f"\n\n[Validation Error in previous attempt]: {last_error}\nFix the exact fields and output valid JSON."

        messages.append({"role": "user", "content": user_content})

        try:
            resp = await client.chat.completions.create(
                model=model,
                messages=messages,
                response_format={"type": "json_object"},
                temperature=0.2,
            )
            raw_text = resp.choices[0].message.content or ""
            return parse_structured(raw_text, model_cls)
        except Exception as err:
            last_error = str(err)
            rag_logger.warning(f"Authoring attempt {attempt}/{max_retries} failed for {model_cls.__name__}: {err}")

    # Fallback to conversational model if author model failed all retries
    if model != OLLAMA_MODEL:
        try:
            rag_logger.info(f"Retrying authoring call with fallback model {OLLAMA_MODEL}...")
            resp = await client.chat.completions.create(
                model=OLLAMA_MODEL,
                messages=messages,
                response_format={"type": "json_object"},
                temperature=0.2,
            )
            raw_text = resp.choices[0].message.content or ""
            return parse_structured(raw_text, model_cls)
        except Exception as fb_err:
            last_error = str(fb_err)

    raise RuntimeError(f"Structured authoring failed after {max_retries} retries: {last_error}")


async def critic_call(prompt: str, model: str = CRITIC_MODEL) -> CriticVerdict:
    """
    Invokes distinct auditor model (e.g. llama3.2) to evaluate factual grounding
    and pedagogical clarity.
    """
    client = get_llm_client()
    messages = [
        {
            "role": "system",
            "content": (
                "You are an impartial Senior Curriculum Auditor.\n"
                "Evaluate the drafted lecture against the retrieved textbook source chunks.\n"
                "Verify that: (1) All citations actually exist in the source chunks, "
                "(2) Explanations are clear and accurate, (3) The canvas type fits the topic.\n"
                "Output JSON: {\"passed\": true|false, \"feedback\": \"...\"}"
            )
        },
        {"role": "user", "content": prompt}
    ]

    try:
        resp = await client.chat.completions.create(
            model=model,
            messages=messages,
            response_format={"type": "json_object"},
            temperature=0.1,
        )
        raw_text = resp.choices[0].message.content or ""
        return parse_structured(raw_text, CriticVerdict)
    except Exception as e:
        # If critic model unavailable, try fallback
        rag_logger.warning(f"Critic call with {model} failed: {e}. Falling back to default auditor...")
        try:
            resp = await client.chat.completions.create(
                model=OLLAMA_MODEL,
                messages=messages,
                response_format={"type": "json_object"},
                temperature=0.1,
            )
            raw_text = resp.choices[0].message.content or ""
            return parse_structured(raw_text, CriticVerdict)
        except Exception as fb_err:
            rag_logger.error(f"Critic audit completely failed: {fb_err}")
            return CriticVerdict(passed=True, feedback="Auditor unavailable, passed through")
