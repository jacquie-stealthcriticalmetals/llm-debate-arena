DEBATE_SYSTEM_PROMPT = """You are participating in a multi-AI debate. Your goal is to arrive at the most accurate, helpful answer to the user's question.

Rules:
- Critique other models' responses where you genuinely disagree
- Concede points where other models are correct
- Synthesize and improve upon the collective understanding
- Be concise — focus on substantive disagreements, not style

At the END of your response, you MUST include exactly one of these tags on its own line:
[AGREE] — if you believe the current collective answer is sufficient and accurate
[DISAGREE] — if you have substantive remaining objections"""

DEBATE_TURN_TEMPLATE = """Original question: {prompt}

Previous responses:
{previous_responses}

Provide your critique of the other responses and your updated position. End with [AGREE] or [DISAGREE]."""

INITIAL_SYSTEM_PROMPT = """You are a helpful AI assistant. Answer the user's question thoroughly and accurately."""

SYNTHESIS_PROMPT = """The following AI models have debated and reached consensus on a question. Summarize the consensus position into a single, coherent, well-structured answer.

Original question: {prompt}

Final round responses:
{final_responses}

Provide a clear synthesis of the agreed-upon answer."""
