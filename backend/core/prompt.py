from langchain.prompts import PromptTemplate

MODERATION_TEMPLATE = """You are a strict and precise content moderation assistant.

You will be given a content moderation POLICY composed of specific RULES, and a piece of CONTENT to evaluate.

Your task is to evaluate the CONTENT against each RULE and determine whether the content violates it.

---

POLICY RULES:
{rules}

---

CONTENT TO EVALUATE:
{content}

---

INSTRUCTIONS:
- Evaluate the content against EACH rule independently.
- For each rule, assign a violation level:
    0 = No violation (the content clearly does not break this rule)
    1 = Possible violation (the content may or might break this rule, but it is ambiguous)
    2 = Clear violation (the content unmistakably breaks this rule)
- Additionally, provide a "details" key with 1-3 sentences explaining the overall reasoning behind your verdict.

RESPOND ONLY with a valid JSON object. Do NOT include any explanation, markdown, or code fences outside the JSON.
The JSON keys must be the exact rule IDs provided. Include a "details" key for overall reasoning.

Example format:
{{
  "rule_id_1": 0,
  "rule_id_2": 2,
  "rule_id_3": 1,
  "details": "The content contains an explicit threat targeting a specific group, which clearly violates Rule 2. Rule 3 may be relevant due to aggressive tone."
}}

Now evaluate the content and respond with the JSON verdict:"""


def build_moderation_prompt() -> PromptTemplate:
    return PromptTemplate(
        input_variables=["rules", "content"],
        template=MODERATION_TEMPLATE,
    )


def format_rules(rules: list[dict]) -> str:
    """Format a list of rule dicts into a numbered readable block."""
    lines = []
    for i, rule in enumerate(rules, start=1):
        lines.append(f"{i}. [ID: {rule['id']}] {rule['name']}: {rule['description']}")
    return "\n".join(lines)
