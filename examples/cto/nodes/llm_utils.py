import json
import logging
import os
from typing import Any

try:
    from google import genai
    from google.genai import types
except ImportError:
    genai = None  # type: ignore

from clawgraph import ClawOutput, Signal
from clawgraph.core.models import HumanRequest

logger = logging.getLogger(__name__)


from examples.cto.tools.pdf_parser import PDFParser
from examples.cto.tools.excel_bridge import ExcelBridge
from examples.cto.tools.gmail_api import GmailAPI
from examples.cto.tools.google_search import GoogleSearch
from examples.cto.tools.notary_log import NotaryLog
from examples.cto.tools.stats_calc import StatsCalc

# Tool Registry
TOOL_REGISTRY = {
    "pdf_parser": PDFParser().extract_text,
    "excel_bridge": ExcelBridge().pull_sheet,
    "append_log": ExcelBridge().append_log,
    "gmail_api": GmailAPI().send_alert,
    "gmail_signature": GmailAPI().request_signature,
    "google_search": GoogleSearch().search,
    "notary_log": NotaryLog().log_integrity_check,
    "get_audit": NotaryLog().get_audit_trail,
    "stats_calc": StatsCalc().calculate_variance,
    "align_pk": StatsCalc().align_pk_metrics,
}

def run_cto_llm_node(
    node_id: str, 
    description: str, 
    state: dict[str, Any], 
    skills: list[str] | None = None,
    tools: list[str] | None = None
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
            result_uri=f"file://{abs_path}",
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
                with open(full_path) as f:
                    context_str_parts.append(f"\n--- SKILL: {skill_path} ---\n{f.read()}")
            except FileNotFoundError:
                logger.warning(f"Skill file not found: {full_path}")
    context_str = "\n".join(context_str_parts)

    # Assuming 'bag.name' is not available and using a generic placeholder or node_id
    # as the domain name for now, as it's not defined in the original context.
    domain_name = node_id  # Placeholder for bag.name

    sys_prompt = f"""
You are an expert agent executing the `{node_id}` node.
Your goal is to process the current state and return a structured JSON response.

# Core Objective
{description}

# Context
{context_str}

# Instructions
1. Analyze the context and perform your specialized task.
2. YOU HAVE ACCESS TO TOOLS. Use them if necessary to gather data, parse documents, or log events.
3. Do NOT hallucinate data. If a tool can provide the truth, use it.
4. If you need human input or approval before proceeding, set "signal" to "HOLD_FOR_HUMAN" and put your question in "human_request_message".
5. Otherwise, set "signal" to "DONE" when finished.
6. Once all information is gathered, return a FINAL valid JSON matching this schema:
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
        for k in archive:
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

        # Prepare tools for Gemini
        gemini_tools = []
        if tools:
            for t_name in tools:
                if t_name in TOOL_REGISTRY:
                    gemini_tools.append(TOOL_REGISTRY[t_name])

        # Initialize history
        history = [types.Content(role="user", parts=[types.Part(text=user_content)])]

        response = client.models.generate_content(
            model="gemini-3.1-flash-lite-preview",
            contents=history,
            config=types.GenerateContentConfig(
                system_instruction=sys_prompt,
                temperature=0.2,
                tools=gemini_tools if gemini_tools else None,
                # For tools we don't force JSON right away 
                # because tool calls are not always JSON primary
                response_mime_type="application/json" if not gemini_tools else None,
            ),
        )

        # Handle iterative tool calling
        # Flash-lite supports function calling but we need to check if it's a tool call or text
        while response.candidates[0].content.parts and any(p.function_call for p in response.candidates[0].content.parts):
            # Add the model's response (containing tool calls) to history
            history.append(response.candidates[0].content)
            
            tool_result_parts = []
            for part in response.candidates[0].content.parts:
                if part.function_call:
                    fn_name = part.function_call.name
                    fn_args = dict(part.function_call.args)
                    
                    # Resolve paths in arguments using the archive mapping
                    for arg_key, arg_val in fn_args.items():
                        if isinstance(arg_val, str):
                            # 1. Try resolving via specific archive key
                            resolved_val = arg_val
                            if arg_val in archive:
                                resolved_val = archive[arg_val]
                            
                            # 2. Heuristic for file paths or known reg files
                            if isinstance(resolved_val, str) and ("file://" in resolved_val or any(resolved_val.endswith(ext) for ext in [".pdf", ".csv", ".json", ".zip"])):
                                base = os.path.basename(resolved_val.replace("file:///seed/", "").replace("file://", ""))
                                possible_paths = [
                                    os.path.join("examples/cto/artifacts/reg_sources", base),
                                    os.path.join("examples/cto/artifacts", base),
                                    os.path.join("examples/cto/artifacts/generated", base),
                                    base
                                ]
                                for p in possible_paths:
                                    if os.path.exists(p):
                                        fn_args[arg_key] = os.path.abspath(p)
                                        break
                            elif arg_val == "protocol_v1" and "protocol_v1.pdf" in os.listdir("examples/cto/artifacts/reg_sources"):
                                # Specific fallback for key-to-filename if manifest is sparse
                                fn_args[arg_key] = os.path.abspath("examples/cto/artifacts/reg_sources/protocol_v1.pdf")

                    print(f"   🛠️  [TOOL_CALL] {fn_name}({fn_args})")
                    
                    # Direct dispatch - the function name in genai SDK corresponds 
                    # exactly to the __name__ of the function passed in tools.
                    # Since we are passing methods from TOOL_REGISTRY, we need a map.
                    
                    # Mapping of function names (as seen by Gemini) to our registry functions
                    # Note: GenAI SDK usually uses the __name__ of the function.
                    name_to_func = {f.__name__: f for f in TOOL_REGISTRY.values()}
                    
                    if fn_name in name_to_func:
                        try:
                            result = name_to_func[fn_name](**fn_args)
                            # SDK/Pydantic REQUIRE a dict for FunctionResponse.response
                            if not isinstance(result, dict):
                                result = {"data": result}
                            print(f"   ✅ [TOOL_SUCCESS] {fn_name}")
                        except Exception as e:
                            print(f"   ❌ [TOOL_ERROR] {fn_name}: {e}")
                            result = {"error": str(e)}
                    else:
                        result = {"error": f"Unknown tool: {fn_name}"}
                        print(f"   ⚠️ [TOOL_UNKNOWN] {fn_name}")
                    tool_result_parts.append(types.Part.from_function_response(
                        name=fn_name,
                        response=result
                    ))

            if tool_result_parts:
                # GenAI SDK expects "user" role for the function response parts
                history.append(types.Content(role="user", parts=tool_result_parts))
                
                # Send results back
                response = client.models.generate_content(
                    model="gemini-3.1-flash-lite-preview",
                    contents=history,
                    config=types.GenerateContentConfig(
                        system_instruction=sys_prompt,
                        temperature=0.1,
                        tools=gemini_tools if gemini_tools else None,
                    ),
                )
            else:
                break
    
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
            abs_path = os.path.abspath(
                os.path.join(os.path.dirname(__file__), "..", artifact_rel_path)
            )

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
