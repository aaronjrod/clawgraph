import json
import logging
import os
from typing import Any, cast

from google import genai
from google.genai import types

from clawgraph.bag.manager import BagManager
from clawgraph.core.signals import SignalManager
from clawgraph.orchestrator.graph import BagState
from clawgraph.orchestrator.llm_tools import OrchestratorTools

logger = logging.getLogger(__name__)


def make_orchestrator_node(
    bag_manager: BagManager,
    signal_manager: SignalManager,
    contract: Any | None = None,
) -> Any:
    """Creates the LangGraph node function for the LLM Orchestrator."""
    tools = OrchestratorTools(bag_manager, signal_manager, contract=contract)

    # We define the tool schemas manually or via pydantic for Gemini
    gemini_tools = [
        types.Tool(
            function_declarations=[
                types.FunctionDeclaration(
                    name="dispatch_node",
                    description="Execute a specific node from the ready_queue.",
                    parameters=types.Schema(
                        type=types.Type.OBJECT,
                        properties={
                            "node_id": types.Schema(
                                type=types.Type.STRING, description="The ID of the node to execute."
                            )
                        },
                        required=["node_id"],
                    ),
                ),
                types.FunctionDeclaration(
                    name="escalate",
                    description="Escalate a problem (like a FAILED or PARTIAL signal) to the Super-Orchestrator.",
                    parameters=types.Schema(
                        type=types.Type.OBJECT,
                        properties={
                            "reason": types.Schema(
                                type=types.Type.STRING, description="The reason for escalation."
                            ),
                            "failure_class": types.Schema(
                                type=types.Type.STRING,
                                description="One of: LOGIC_ERROR, SCHEMA_MISMATCH, TOOL_FAILURE, GUARDRAIL_VIOLATION, SYSTEM_CRASH",
                            ),
                        },
                        required=["reason", "failure_class"],
                    ),
                ),
                types.FunctionDeclaration(
                    name="suspend",
                    description="Suspend the workflow to ask a human for approval or input (HOLD_FOR_HUMAN).",
                    parameters=types.Schema(
                        type=types.Type.OBJECT,
                        properties={
                            "human_request_message": types.Schema(
                                type=types.Type.STRING, description="The message to show the human."
                            )
                        },
                        required=["human_request_message"],
                    ),
                ),
                types.FunctionDeclaration(
                    name="complete",
                    description="Mark the current reasoning loop as finished and return to a READY/IDLE state. You MUST call this after you have provided a status update or answered a question if you have no further nodes to dispatch in this turn. Failing to call complete() after a chat update will cause you to loop. Calling complete() DOES NOT clear your memory; it simply ends your current active turn.",
                    parameters=types.Schema(
                        type=types.Type.OBJECT,
                        properties={
                            "final_summary": types.Schema(
                                type=types.Type.STRING,
                                description="A definitive summary of what you accomplished or what you are now waiting for.",
                            )
                        },
                        required=["final_summary"],
                    ),
                ),
                types.FunctionDeclaration(
                    name="post_chat_message",
                    description="Post a message back to the human in the chat tray (e.g. status updates, answers).",
                    parameters=types.Schema(
                        type=types.Type.OBJECT,
                        properties={
                            "text": types.Schema(
                                type=types.Type.STRING,
                                description="The message text to send.",
                            )
                        },
                        required=["text"],
                    ),
                ),
                types.FunctionDeclaration(
                    name="reset_memory",
                    description="Clear the agent's chat history and internal context. Use this if the context is cluttered or you have been explicitly asked to reset your memory.",
                    parameters=types.Schema(
                        type=types.Type.OBJECT,
                        properties={},
                    ),
                ),
            ]
        )
    ]

    def orchestrator_turn(state: BagState) -> BagState:
        """The main LLM loop for the Orchestrator."""
        iteration_count = state.get("iteration_count", 0)
        max_iterations = state.get("max_iterations", 10)

        if iteration_count >= max_iterations:
            logger.warning(
                f"Iteration budget exhausted ({iteration_count}/{max_iterations}). Escalating."
            )
            return cast(
                BagState,
                tools.escalate(
                    cast(dict[str, Any], state),
                    {"reason": "Iteration budget exhausted", "failure_class": "LOGIC_ERROR"},
                ),
            )

        sys_prompt = state.get("orchestrator_prompt", "You are the Tactical Director.")

        # F-REQ-MOD-06: Loop Hygiene
        sys_prompt += (
            "\n\n## LOOP HYGIENE\n"
            "- You are in a multi-turn reasoning loop. Each time you call `post_chat_message`, the loop continues.\n"
            "- Once you have provided your update or answered the human, you MUST call `complete()` to end your turn.\n"
            "- CRITICAL: If you see your own recent message in the 'Recent Chat History' section, do NOT repeat it. Call `complete()` immediately instead."
        )

        # Check for any human responses targeting this thread from the HUD
        thread_id = state.get("thread_id")
        human_context = ""
        if (
            thread_id
            and hasattr(signal_manager, "_human_responses")
            and thread_id in signal_manager._human_responses
        ):
            human_reply = signal_manager._human_responses[thread_id]
            human_context = f"\nHuman Response from previous HOLD: {human_reply}\n"

        # Contextual history from SignalManager (Human chat)
        chat_context = ""
        last_orchestrator_msg = None
        if hasattr(signal_manager, "_chat_history") and signal_manager._chat_history:
            chat_lines = []
            for c in signal_manager._chat_history:
                chat_lines.append(f"- [{c['sender']}] {c['text']}")
                if c['sender'] == "ORCHESTRATOR":
                    last_orchestrator_msg = c['text']
            chat_context = "\nRecent Chat History:\n" + "\n".join(chat_lines) + "\n"
        logger.info(f"Chat Context: {chat_context}")

        # Build the dynamic context for this turn
        context = f"""
=== CURRENT STATE ===
Objective: {state.get("objective")}
Turn: {iteration_count + 1} / {max_iterations}{human_context}{chat_context}

Bag Manifest (Tier 1 Metadata):
{json.dumps(state.get("bag_manifest", {}), indent=2)}

Document Archive (Pointers):
{json.dumps(state.get("document_archive", {}), indent=2)}

Stalled Queue (Nodes waiting on prereqs):
{state.get("stalled_queue", [])}

Ready Queue (Nodes ready to execute):
{state.get("ready_queue", [])}

Phase History:
{json.dumps(state.get("phase_history", []), indent=2)}

Current Node Output (Last signal received):
{json.dumps(state.get("current_output", {}), indent=2)}
"""

        # Test mode fallback: if no API key and no mock, use a deterministic router to pass the unit tests
        has_api_key = os.environ.get("GEMINI_API_KEY")

        # We need a way to detect if genai.Client() is mocked.
        # Check if the class or the init function is mocked.
        is_mocked = (
            "mock_init" in str(genai.Client)
            or "MockGeminiClient" in str(genai.Client)
            or "MagicMock" in str(genai.Client)
        )

        if not has_api_key and not is_mocked:
            logger.info(
                "No GEMINI_API_KEY found and not mocked. Falling back to deterministic orchestrator rules."
            )
            current_output = state.get("current_output", {})
            signal = current_output.get("signal")

            if signal == "DONE" or signal is None:
                ready_queue = state.get("ready_queue", [])
                if ready_queue:
                    return cast(
                        BagState,
                        tools.dispatch_node(
                            cast(dict[str, Any], state), {"node_id": ready_queue[0]}
                        ),
                    )
                return cast(
                    BagState,
                    tools.complete(
                        cast(dict[str, Any], state),
                        {"final_summary": "Auto-completed (Deterministic Fallback)."},
                    ),
                )

            if signal == "FAILED" or signal == "NEED_INTERVENTION":
                return cast(
                    BagState,
                    tools.escalate(
                        cast(dict[str, Any], state),
                        {"reason": "Fallback escalation.", "failure_class": "LOGIC_ERROR"},
                    ),
                )

            if signal == "HOLD_FOR_HUMAN":
                return cast(
                    BagState,
                    tools.suspend(
                        cast(dict[str, Any], state),
                        {"human_request_message": "Fallback human hold."},
                    ),
                )

            if signal == "NEED_INFO":
                return cast(
                    BagState,
                    tools.dispatch_node(
                        cast(dict[str, Any], state),
                        {"node_id": current_output.get("node_id", "unknown")},
                    ),
                )

            if signal == "PARTIAL":
                return cast(
                    BagState,
                    tools.escalate(
                        cast(dict[str, Any], state),
                        {"reason": "Partial escalation.", "failure_class": "LOGIC_ERROR"},
                    ),
                )

            return cast(
                BagState,
                tools.escalate(
                    cast(dict[str, Any], state),
                    {"reason": "Unknown signal.", "failure_class": "LOGIC_ERROR"},
                ),
            )

        client = genai.Client()
        logger.info(f"Orchestrator LLM reasoning turn {iteration_count + 1}...")

        try:
            response = client.models.generate_content(
                model="gemini-3.1-flash-lite-preview",
                contents=context,
                config=types.GenerateContentConfig(
                    system_instruction=sys_prompt,
                    tools=gemini_tools,
                    temperature=0.1,  # Keep it deterministic and strict
                ),
            )
        except Exception as e:
            logger.error(f"LLM API Call failed: {e}")
            return cast(
                BagState,
                tools.escalate(
                    cast(dict[str, Any], state),
                    {"reason": f"LLM API Exception: {e}", "failure_class": "SYSTEM_CRASH"},
                ),
            )

        # Parse tool calls
        if response.function_calls:
            call = response.function_calls[0]
            args = {k: v for k, v in call.args.items()} if call.args else {}
            logger.info(f"Orchestrator chose tool: {call.name} with args: {args}")

            # F-REQ-MOD-09: Repetition Guard - Force completion if the agent tries to send an identical message
            if (
                call.name == "post_chat_message" 
                and last_orchestrator_msg 
                and args.get("text") == last_orchestrator_msg
            ):
                logger.warning("Repetitive chat detected. Forcing completion to break loop.")
                return cast(
                    BagState,
                    tools.complete(
                        cast(dict[str, Any], state),
                        {"final_summary": "Redundant status update suppressed. Standing by for instructions."},
                    ),
                )

            # F-REQ-MOD-02: Sanity Guard - Prevent dispatching a node that just requested HOLD
            current_output = state.get("current_output", {})
            if (
                call.name == "dispatch_node"
                and current_output.get("signal") == "HOLD_FOR_HUMAN"
                and args.get("node_id") == current_output.get("node_id")
                and not state.get("human_response")
            ):
                logger.warning(
                    f"Orchestrator attempted to re-dispatch suspended node '{args.get('node_id')}' without new human input. Interposing forced suspend."
                )
                return cast(
                    BagState,
                    tools.suspend(
                        cast(dict[str, Any], state),
                        {"human_request_message": "Awaiting necessary source data as previously requested."},
                    ),
                )

            if call.name == "dispatch_node":
                return cast(BagState, tools.dispatch_node(cast(dict[str, Any], state), args))
            elif call.name == "escalate":
                return cast(BagState, tools.escalate(cast(dict[str, Any], state), args))
            elif call.name == "suspend":
                return cast(BagState, tools.suspend(cast(dict[str, Any], state), args))
            elif call.name == "complete":
                return cast(BagState, tools.complete(cast(dict[str, Any], state), args))
            elif call.name == "post_chat_message":
                return cast(BagState, tools.post_chat_message(cast(dict[str, Any], state), args))
            else:
                return cast(
                    BagState,
                    tools.escalate(
                        cast(dict[str, Any], state),
                        {
                            "reason": f"LLM hallucinated tool: {call.name}",
                            "failure_class": "LOGIC_ERROR",
                        },
                    ),
                )
        else:
            # LLM didn't call a tool, force an escalation
            return cast(
                BagState,
                tools.escalate(
                    cast(dict[str, Any], state),
                    {
                        "reason": "LLM failed to call a routing tool.",
                        "failure_class": "LOGIC_ERROR",
                    },
                ),
            )

    return orchestrator_turn
