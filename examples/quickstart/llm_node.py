import json
import logging
import os

try:
    from google import genai
    from google.genai import types
except ImportError:
    genai = None  # type: ignore

from clawgraph import ClawBag, ClawOutput, Signal, clawnode

logger = logging.getLogger(__name__)


def build_llm_node(node_id: str, system_prompt: str, bag: ClawBag) -> callable:
    """Builds a ClawNode backed by Gemini and registers it to the bag."""

    @clawnode(id=node_id, bag=bag.name, description=system_prompt)
    def wrapper(state: dict) -> ClawOutput:
        if not genai or not os.getenv("GEMINI_API_KEY"):
            return ClawOutput(
                signal=Signal.FAILED,
                node_id=node_id,
                orchestrator_summary="google-genai SDK or API key missing.",
                error_detail={
                    "failure_class": "SYSTEM_ERROR",
                    "message": "google-genai SDK or API key missing.",
                },
            )

        client = genai.Client(api_key=os.getenv("GEMINI_API_KEY"))

        sys_prompt = system_prompt + (
            "\n\nYou MUST respond in raw JSON matching this EXACT schema:\n"
            "{\n"
            '  "signal": "DONE" | "FAILED" | "NEED_INFO" | "PARTIAL",\n'
            '  "summary": "Short 1 sentence summary of what you did",\n'
            '  "result": "Detailed output or findings"\n'
            "}"
        )

        objective = state.get("objective", "")
        # The history or previous context from the orchestrator
        phase_history = state.get("phase_history", [])

        user_content = f"Objective: {objective}\n\nHistory of what has happened so far:\n"
        for h in phase_history:
            user_content += f"- {h}\n"

        if state.get("continuation_context"):
            user_content += f"\nContinuation Context:\n{state.get('continuation_context')}"

        try:
            logger.info(f"[{node_id}] Calling LLM...")

            # Simulated delay to make the UI look cool
            import time

            time.sleep(2)

            response = client.models.generate_content(
                model="gemini-2.5-flash",
                contents=user_content,
                config=types.GenerateContentConfig(
                    system_instruction=sys_prompt,
                    temperature=0.2,
                    response_mime_type="application/json",
                ),
            )

            text = response.text

            # Clean up markdown blocks if the LLM adds them
            if "```json" in text:
                text = text.split("```json")[1].split("```")[0].strip()
            elif "```" in text:
                text = text.split("```")[1].strip()

            data = json.loads(text)

            signal_str = data.get("signal", "DONE").upper()
            try:
                sig = Signal(signal_str)
            except ValueError:
                sig = Signal.DONE

            output_kwargs = {
                "signal": sig,
                "node_id": node_id,
                "orchestrator_summary": data.get("summary", "Task completed."),
                "continuation_context": {"text": data.get("result", "")},
            }
            if sig == Signal.FAILED:
                output_kwargs["error_detail"] = {
                    "failure_class": "LLM_FAILURE",
                    "message": data.get("result", "LLM explicitly opted to fail."),
                }
            elif sig == Signal.DONE:
                output_kwargs["result_uri"] = f"uri://live_demo/{node_id}_output.txt"

            return ClawOutput(**output_kwargs)

        except Exception as e:
            logger.error(f"LLM Exception in {node_id}: {e}")
            return ClawOutput(
                signal=Signal.FAILED,
                node_id=node_id,
                orchestrator_summary=f"LLM Call failed: {e!s}",
                error_detail={"failure_class": "SYSTEM_CRASH", "message": str(e)},
            )

    # Register the dynamically created node to the bag
    bag.manager.register_node(wrapper)
    return wrapper
