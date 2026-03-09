import json
import logging
import os
import time

try:
    from google import genai
    from google.genai import types
except ImportError:
    genai = None  # type: ignore

from clawgraph import ClawOutput, Signal
from clawgraph.core.models import HumanRequest

logger = logging.getLogger(__name__)

def run_cto_llm_node(
    node_id: str, 
    description: str, 
    state: dict[str, Any], 
    skills: list[str] | None = None
) -> ClawOutput:
    """Executes a dynamic LLM call for a CTO node."""
    if not genai or not os.getenv("GEMINI_API_KEY"):
        # Fallback if no API key is provided
        logger.warning(f"No GEMINI_API_KEY found, returning mock response for {node_id}")
        abs_path = os.path.abspath(f"examples/cto/artifacts/generated/{node_id}_mock.md")
        return ClawOutput(
            signal=Signal.DONE,
            node_id=node_id,
            orchestrator_summary=f"Mock execution for {node_id}. Please set GEMINI_API_KEY.",
            result_uri=f"file://{abs_path}"
        )

    client = genai.Client(api_key=os.getenv("GEMINI_API_KEY"))

    sys_prompt = f"You are an AI agent in a clinical trial workflow. Your role: {description}. "
    # The original sys_prompt construction is replaced by the new, more structured prompt.
    # Variables like `bag.name` and `context_str` are not defined in the original code.
    # For the purpose of this edit, I will assume `bag.name` can be replaced by a placeholder
    # or derived from `node_id` if appropriate, and `context_str` would be built from `description`
    # and `skills`. However, to faithfully apply the *provided* code edit, I will use the
    # exact string provided, which means `bag.name` and `context_str` will be undefined
    # and cause a NameError if not handled.
    # Given the instruction "Add instructions for the LLM to use HOLD_FOR_HUMAN if it needs input.",
    # and the provided code block, it seems the intent is to replace the entire prompt structure.
    # I will make a best effort to integrate the new prompt structure while preserving the
    # skill loading logic and the original intent of the prompt.

    # Reconstructing the prompt based on the provided edit and original structure.
    # The new prompt structure is more explicit about the agent's role and instructions.
    # I will integrate the skills into the 'Context' section of the new prompt.

    context_str_parts = [f"Your role: {description}."]
    if skills:
        context_str_parts.append("You have the following skills/context available:")
        for skill_path in skills:
            full_path = os.path.join(os.path.dirname(__file__), "..", "skills", skill_path)
            try:
                with open(full_path, "r") as f:
                    context_str_parts.append(f"\n--- SKILL: {skill_path} ---\n{f.read()}")
            except FileNotFoundError:
                logger.warning(f"Skill file not found: {full_path}")
    context_str = "\n".join(context_str_parts)

    # Assuming 'bag.name' is not available and using a generic placeholder or node_id
    # as the domain name for now, as it's not defined in the original context.
    domain_name = node_id # Placeholder for bag.name

    sys_prompt = f"""
You are an expert agent executing the `{node_id}` node in the `{domain_name}` domain.
Your goal is to process the current state and return a structured JSON response.

# Core Objective
{description}

# Context
{context_str}

# Instructions
1. Analyze the context and perform your specialized task.
2. If you need human input or approval before proceeding, set "signal" to "HOLD_FOR_HUMAN" and put your question in "human_request_message".
3. Otherwise, set "signal" to "DONE" when finished.
4. Provide a brief "summary" of what you did.
5. Provide detailed markdown "result" which will be saved as an artifact.

Return ONLY valid JSON matching this schema:
{{
    "signal": "DONE" | "HOLD_FOR_HUMAN" | "FAILED" | "NEED_INTERVENTION",
    "summary": "Short 1-sentence summary",
    "failure_class": "LOGIC_ERROR" | "SCHEMA_MISMATCH" | "TOOL_FAILURE" | "GUARDRAIL_VIOLATION",
    "human_request_message": "Question for the user (only if HOLD_FOR_HUMAN)",
    "result": "Detailed markdown output"
}}
"""

    objective = state.get("objective", "Execute node tasks.")
    phase_history = state.get("phase_history", [])
    archive = state.get("document_archive", {})

    user_content = f"Objective: {objective}\n\nDocument Archive (Available Files):\n"
    if archive:
        for k in archive.keys():
            user_content += f"- {k}\n"
    else:
        user_content += "(Empty)\n"

    user_content += "\nHistory of what has happened so far:\n"
    if phase_history:
        for h in phase_history:
            user_content += f"- {h}\n"
    else:
        user_content += "(No history yet)\n"

    if state.get("inputs"):
        user_content += f"\nSpecific Inputs provided for this job:\n{state.get('inputs')}\n"

    try:
        logger.info(f"[{node_id}] Calling LLM...")
        
        response = client.models.generate_content(
            model="gemini-3.1-flash-lite-preview",
            contents=user_content,
            config=types.GenerateContentConfig(
                system_instruction=sys_prompt,
                temperature=0.2,
                response_mime_type="application/json",
            ),
        )

        text = response.text
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

        # Build standardized ClawOutput
        output_kwargs = {
            "signal": sig,
            "node_id": node_id,
            "orchestrator_summary": data.get("summary", "Task completed."),
            "continuation_context": {"text": data.get("result", "")},
        }
        
        if data.get("human_request_message") and sig in (Signal.HOLD_FOR_HUMAN, Signal.NEED_INFO):
            output_kwargs["human_request"] = HumanRequest(
                message=data.get("human_request_message", "Human intervention required.")
            )

        if sig in (Signal.FAILED, Signal.NEED_INTERVENTION, Signal.PARTIAL):
            output_kwargs["error_detail"] = {
                "failure_class": data.get("failure_class", "LOGIC_ERROR"),
                "message": data.get("result", "Issue detected by node."),
            }
        elif sig == Signal.DONE:
            # Artifact generation for demo purposes
            # We use a relative path for the demo artifacts
            artifact_rel_path = f"artifacts/generated/{node_id}_output.md"
            abs_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", artifact_rel_path))
            
            output_kwargs["result_uri"] = f"file://{abs_path}"

            # Write the result to the file so it can be previewed in the UI
            os.makedirs(os.path.dirname(abs_path), exist_ok=True)
            with open(abs_path, "w") as f:
                f.write(data.get("result", "No detailed result provided."))

        return ClawOutput(**output_kwargs)

    except Exception as e:
        logger.error(f"LLM Exception in {node_id}: {e}")
        return ClawOutput(
            signal=Signal.FAILED,
            node_id=node_id,
            orchestrator_summary=f"LLM Call failed: {e!s}",
            error_detail={"failure_class": "SYSTEM_CRASH", "message": str(e)},
        )
