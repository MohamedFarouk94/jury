import json
import re
from langchain.schema.output_parser import StrOutputParser

from .llm import get_llm
from .prompt import build_moderation_prompt, format_rules


def parse_json_response(raw: str) -> dict:
    """Safely extract and parse JSON from the LLM response."""
    # Strip any surrounding markdown code fences if present
    clean = re.sub(r"```(?:json)?", "", raw).strip()
    return json.loads(clean)


def run_moderation_chain(rules: list[dict], content: str) -> dict:
    """
    Runs the moderation chain against the given rules and content.

    Args:
        rules: List of dicts with keys 'id', 'name', 'description'
        content: The text content to evaluate

    Returns:
        A dict with rule IDs as keys (violation level 0/1/2) and a 'details' key.
    """
    prompt = build_moderation_prompt()
    llm = get_llm()
    parser = StrOutputParser()

    chain = prompt | llm | parser

    formatted_rules = format_rules(rules)

    raw_response = chain.invoke({
        "rules": formatted_rules,
        "content": content,
    })

    return parse_json_response(raw_response)
