import asyncio
import time
import uuid
from dataclasses import dataclass, field

from backend.config import MAX_DEBATE_ROUNDS
from backend.consensus import check_consensus
from backend.llm_clients import get_client
from backend.prompts import (
    DEBATE_SYSTEM_PROMPT,
    DEBATE_TURN_TEMPLATE,
    INITIAL_SYSTEM_PROMPT,
    SYNTHESIS_PROMPT,
)


@dataclass
class ModelConfig:
    provider: str
    model: str

    @property
    def label(self) -> str:
        return self.model


@dataclass
class Response:
    model_label: str
    content: str


@dataclass
class DebateRound:
    round_number: int
    responses: list[Response] = field(default_factory=list)


@dataclass
class DebateSession:
    id: str
    prompt: str
    models: list[ModelConfig]
    timeout_seconds: int
    rounds: list[DebateRound] = field(default_factory=list)
    start_time: float = 0.0
    status: str = "pending"
    consensus_summary: str | None = None
    event_queue: asyncio.Queue = field(default_factory=asyncio.Queue)
    stop_requested: bool = False


sessions: dict[str, DebateSession] = {}


def create_session(prompt: str, models: list[dict], timeout_seconds: int) -> DebateSession:
    session = DebateSession(
        id=str(uuid.uuid4()),
        prompt=prompt,
        models=[ModelConfig(**m) for m in models],
        timeout_seconds=timeout_seconds,
    )
    sessions[session.id] = session
    return session


async def _call_model(mc: ModelConfig, messages: list[dict]) -> str:
    client = get_client(mc.provider)
    return await client.complete(messages, mc.model)


def _format_previous_responses(rounds: list[DebateRound]) -> str:
    parts = []
    for r in rounds:
        parts.append(f"--- Round {r.round_number} ---")
        for resp in r.responses:
            parts.append(f"[{resp.model_label}]:\n{resp.content}\n")
    return "\n".join(parts)


async def run_debate(session: DebateSession):
    session.status = "running"
    session.start_time = time.time()

    await session.event_queue.put({"type": "status", "message": "Starting initial responses..."})

    # Phase 1: Initial responses
    initial_round = DebateRound(round_number=1)
    session.rounds.append(initial_round)

    async def get_initial(mc: ModelConfig):
        messages = [
            {"role": "system", "content": INITIAL_SYSTEM_PROMPT},
            {"role": "user", "content": session.prompt},
        ]
        try:
            content = await _call_model(mc, messages)
            return Response(model_label=mc.label, content=content)
        except Exception as e:
            return Response(model_label=mc.label, content=f"[ERROR: {e}]")

    results = await asyncio.gather(*[get_initial(mc) for mc in session.models])

    active_models = []
    for i, resp in enumerate(results):
        initial_round.responses.append(resp)
        await session.event_queue.put({
            "type": "initial_response",
            "model": resp.model_label,
            "content": resp.content,
        })
        if not resp.content.startswith("[ERROR"):
            active_models.append(session.models[i])

    if len(active_models) < 2:
        session.status = "error"
        await session.event_queue.put({
            "type": "error",
            "message": "Fewer than 2 models responded successfully. Cannot debate.",
        })
        await session.event_queue.put({"type": "done"})
        return

    # Phase 2: Debate rounds
    for round_num in range(2, MAX_DEBATE_ROUNDS + 2):
        if session.stop_requested:
            session.status = "stopped"
            await session.event_queue.put({"type": "status", "message": "Debate stopped by user."})
            break

        elapsed = time.time() - session.start_time
        if elapsed >= session.timeout_seconds:
            session.status = "timeout"
            await session.event_queue.put({
                "type": "timeout",
                "message": f"Time limit reached ({session.timeout_seconds}s) after {round_num - 1} rounds.",
            })
            break

        await session.event_queue.put({"type": "status", "message": f"Round {round_num} starting..."})

        debate_round = DebateRound(round_number=round_num)
        session.rounds.append(debate_round)

        previous = _format_previous_responses(session.rounds[:-1])

        async def get_debate_response(mc: ModelConfig):
            user_content = DEBATE_TURN_TEMPLATE.format(
                prompt=session.prompt,
                previous_responses=previous,
            )
            messages = [
                {"role": "system", "content": DEBATE_SYSTEM_PROMPT},
                {"role": "user", "content": user_content},
            ]
            try:
                content = await _call_model(mc, messages)
                return Response(model_label=mc.label, content=content)
            except Exception as e:
                return Response(model_label=mc.label, content=f"[ERROR: {e}]")

        results = await asyncio.gather(*[get_debate_response(mc) for mc in active_models])

        still_active = []
        round_texts = []
        for i, resp in enumerate(results):
            debate_round.responses.append(resp)
            await session.event_queue.put({
                "type": "debate_turn",
                "round": round_num,
                "model": resp.model_label,
                "content": resp.content,
            })
            if not resp.content.startswith("[ERROR"):
                still_active.append(active_models[i])
                round_texts.append(resp.content)

        active_models = still_active

        if len(active_models) < 2:
            session.status = "error"
            await session.event_queue.put({
                "type": "error",
                "message": "Too few models remaining to continue debate.",
            })
            break

        if check_consensus(round_texts):
            session.status = "consensus"
            await session.event_queue.put({"type": "status", "message": "Consensus detected! Generating synthesis..."})

            # Generate synthesis using the cheapest available model
            synth_model = active_models[0]
            final_resp_text = "\n\n".join(
                f"[{r.model_label}]: {r.content}" for r in debate_round.responses
            )
            synth_messages = [
                {"role": "system", "content": "You are a helpful assistant."},
                {"role": "user", "content": SYNTHESIS_PROMPT.format(
                    prompt=session.prompt, final_responses=final_resp_text
                )},
            ]
            try:
                session.consensus_summary = await _call_model(synth_model, synth_messages)
            except Exception:
                session.consensus_summary = "Consensus reached but synthesis generation failed."

            await session.event_queue.put({
                "type": "consensus",
                "summary": session.consensus_summary,
            })
            break
    else:
        session.status = "max_rounds"
        await session.event_queue.put({
            "type": "timeout",
            "message": f"Maximum rounds ({MAX_DEBATE_ROUNDS}) reached without consensus.",
        })

    await session.event_queue.put({"type": "done"})
